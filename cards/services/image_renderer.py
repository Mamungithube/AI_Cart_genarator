import os
import io
import re
import cv2
import base64
import logging
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _hex_to_rgb(hex_code, fallback=(9, 13, 22)):
    if not hex_code:
        return fallback
    try:
        h = str(hex_code).strip().lstrip('#')
        if len(h) == 3:
            h = ''.join([c * 2 for c in h])
        if len(h) == 6:
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return fallback


def render_html_to_image(front_html, css):
    """
    Renders front_html + css to PNG bytes (1050x600 px) using headless Chromium or wkhtmltoimage.
    """
    if not front_html:
        return None

    # Check for chromium / chrome / wkhtmltoimage binaries
    browser_bin = None
    for candidate in ("chromium", "chromium-browser", "google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        found = shutil.which(candidate) or (candidate if os.path.exists(candidate) else None)
        if found:
            browser_bin = found
            break

    wk = shutil.which("wkhtmltoimage")
    if not wk:
        for p in ("/usr/bin/wkhtmltoimage", "/usr/local/bin/wkhtmltoimage"):
            if os.path.exists(p):
                wk = p
                break

    if not browser_bin and not wk:
        return None

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1050, height=600, initial-scale=1">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{
    width: 1050px;
    height: 600px;
    overflow: hidden;
    background: transparent;
    font-family: 'Roboto', 'Liberation Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
{css or ''}
</style>
</head>
<body>
{front_html}
</body>
</html>"""

    h_path = None
    p_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as h_file:
            h_file.write(full_html)
            h_path = h_file.name

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as p_file:
            p_path = p_file.name

        # 1. High-fidelity rendering via headless Chromium
        if browser_bin:
            cmd = [
                browser_bin,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--window-size=1050,600",
                f"--screenshot={p_path}",
                f"file://{h_path}"
            ]
            ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
            if ret.returncode == 0 and os.path.exists(p_path) and os.path.getsize(p_path) > 1000:
                with open(p_path, "rb") as f:
                    return f.read()

        # 2. Secondary fallback via wkhtmltoimage
        if wk:
            cmd = [
                wk,
                "--width", "1050",
                "--height", "600",
                "--enable-local-file-access",
                "--quality", "95",
                h_path,
                p_path
            ]
            ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
            if ret.returncode == 0 and os.path.exists(p_path) and os.path.getsize(p_path) > 1000:
                with open(p_path, "rb") as f:
                    return f.read()
    except Exception as e:
        logger.warning(f"HTML rendering error: {e}")
    finally:
        for path in (h_path, p_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    return None


def render_reference_card_composite(reference_image, card_data):
    """
    Composites user card credentials onto the reference image artwork.
    1. Crops/resizes reference image to 1050x600.
    2. Identifies background color from multiple patches and cleans old dummy text.
    3. Overlays user's actual name, designation, company, and contact details
       using matching contrast and fonts.
    """
    if not reference_image:
        return None

    try:
        ref_pil = None
        if isinstance(reference_image, Image.Image):
            ref_pil = reference_image
        elif hasattr(reference_image, 'read'):
            try:
                reference_image.seek(0)
            except Exception:
                pass
            ref_pil = Image.open(reference_image)
        elif isinstance(reference_image, str):
            s = reference_image.strip()
            if s.startswith('data:image') or len(s) > 100:
                b64_part = s.split(',', 1)[1] if ',' in s else s
                img_bytes = base64.b64decode(b64_part)
                ref_pil = Image.open(io.BytesIO(img_bytes))
            elif os.path.exists(s):
                ref_pil = Image.open(s)

        if not ref_pil:
            return None

        # Resize to standard 1050x600
        w, h = 1050, 600
        ref_resized = ref_pil.resize((w, h), Image.Resampling.LANCZOS)
        if ref_resized.mode != 'RGB':
            ref_resized = ref_resized.convert('RGB')

        bgr = cv2.cvtColor(np.array(ref_resized), cv2.COLOR_RGB2BGR)

        # Multi-patch background sampling (corners and margins)
        patches = [
            bgr[20:70, 30:80],
            bgr[h-80:h-30, 30:80],
            bgr[20:70, 150:200],
            bgr[h-80:h-30, 150:200],
        ]
        medians = [np.median(p.reshape(-1, 3), axis=0) for p in patches]
        bg_bgr = np.median(medians, axis=0).astype(int)
        bg_gray = int(0.299 * bg_bgr[2] + 0.587 * bg_bgr[1] + 0.114 * bg_bgr[0])
        is_dark = bg_gray < 128

        # Inpaint text zone safely (left 60% of card, keeping right-side artwork intact)
        clean_bgr = None
        try:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray, np.full_like(gray, bg_gray))

            text_zone_mask = np.zeros_like(gray)
            cv2.rectangle(text_zone_mask, (30, 30), (int(w * 0.62), h - 30), 255, -1)

            _, text_mask = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
            text_mask = cv2.bitwise_and(text_mask, text_zone_mask)

            # Safety check: if mask is reasonable, perform inpaint
            if cv2.countNonZero(text_mask) < (w * h * 0.40):
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                text_mask = cv2.dilate(text_mask, kernel, iterations=2)
                clean_bgr = cv2.inpaint(bgr, text_mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
        except Exception:
            clean_bgr = None

        if clean_bgr is None:
            # High-fidelity fallback: blend background color over text zone, preserving curves on right
            clean_bgr = bgr.copy()
            overlay = bgr.copy()
            cv2.rectangle(overlay, (30, 30), (int(w * 0.60), h - 30), (int(bg_bgr[0]), int(bg_bgr[1]), int(bg_bgr[2])), -1)
            cv2.addWeighted(overlay, 0.95, clean_bgr, 0.05, 0, clean_bgr)

        clean_img = Image.fromarray(cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(clean_img)

        # Extract user credentials
        name = str(card_data.get('name') or "Executive Name").strip()
        title = str(card_data.get('designation') or card_data.get('title') or "").strip()
        company = str(card_data.get('company_name') or card_data.get('company') or "").strip()
        phone = str(card_data.get('phone') or "").strip()
        email = str(card_data.get('email') or "").strip()
        website = str(card_data.get('website') or "").strip()
        address = str(card_data.get('address') or "").strip()

        # High-contrast readable typography
        text_rgb = (255, 255, 255) if is_dark else (15, 23, 42)
        muted_rgb = (160, 175, 195) if is_dark else (71, 85, 105)
        accent_rgb = (0, 200, 255) if is_dark else (0, 102, 204)

        font_name = ImageFont.load_default(size=44)
        font_title = ImageFont.load_default(size=20)
        font_company = ImageFont.load_default(size=22)
        font_contact = ImageFont.load_default(size=18)

        # Render text block
        y = 75
        if company:
            draw.text((60, y), company.upper(), fill=muted_rgb, font=font_company)
            y += 34

        if name:
            draw.text((60, y), name, fill=text_rgb, font=font_name)
            y += 54

        if title:
            draw.text((62, y), title.upper(), fill=accent_rgb, font=font_title)
            y += 30

        # Sleek accent underline
        draw.rounded_rectangle([62, y, 140, y + 4], radius=2, fill=accent_rgb)
        y += 40

        # Contact items
        items = []
        if phone: items.append(('M', phone))
        if email: items.append(('E', email))
        if website: items.append(('W', website))
        if address: items.append(('A', address))

        for tag, val in items[:4]:
            draw.rounded_rectangle([62, y, 92, y + 26], radius=5, fill=accent_rgb)
            draw.text((72, y + 4), tag, fill=(255, 255, 255), font=font_contact)
            draw.text((106, y + 4), val, fill=text_rgb, font=font_contact)
            y += 42

        buf = io.BytesIO()
        clean_img.save(buf, format='PNG', quality=95)
        return buf.getvalue()

    except Exception as e:
        logger.warning(f"Error rendering reference card composite: {e}")
        return None


def render_dynamic_canvas_image(card_data):
    """
    Renders an executive, modern visiting card when no reference image or HTML tool is available.
    Dynamically respects dark/light themes without rigid hardcoded placeholder labels.
    """
    width = 1050
    height = 600

    name = str(card_data.get('name') or "Executive Name")
    title = str(card_data.get('designation') or card_data.get('title') or "")
    company = str(card_data.get('company_name') or card_data.get('company') or "")
    tagline = str(card_data.get('tagline') or "")
    phone = str(card_data.get('phone') or "")
    email = str(card_data.get('email') or "")
    website = str(card_data.get('website') or "")
    address = str(card_data.get('address') or "")

    primary_hex = card_data.get('primary_color') or "#0d1117"
    accent_hex = card_data.get('accent_color') or "#00f2fe"

    bg_rgb = _hex_to_rgb(primary_hex, (13, 17, 23))
    accent_rgb = _hex_to_rgb(accent_hex, (0, 242, 254))

    is_dark = (bg_rgb[0] * 0.299 + bg_rgb[1] * 0.587 + bg_rgb[2] * 0.114) < 128
    text_rgb = (255, 255, 255) if is_dark else (15, 23, 42)
    muted_rgb = (148, 163, 184) if is_dark else (100, 116, 139)

    img = Image.new('RGB', (width, height), color=bg_rgb)
    draw = ImageDraw.Draw(img)

    # Hairline frame
    frame_color = (255, 255, 255, 25) if is_dark else (0, 0, 0, 25)
    draw.rounded_rectangle([16, 16, width - 16, height - 16], radius=16, outline=frame_color[:3], width=1)

    font_name = ImageFont.load_default(size=44)
    font_title = ImageFont.load_default(size=20)
    font_company = ImageFont.load_default(size=24)
    font_tagline = ImageFont.load_default(size=14)
    font_contact = ImageFont.load_default(size=18)

    # Company Header
    if company:
        draw.text((60, 60), company.upper(), fill=text_rgb, font=font_company)
        if tagline:
            draw.text((60, 92), tagline.upper(), fill=muted_rgb, font=font_tagline)

    # Name & Title
    name_y = 170 if company else 120
    draw.text((60, name_y), name, fill=text_rgb, font=font_name)

    if title:
        draw.text((62, name_y + 54), title.upper(), fill=accent_rgb, font=font_title)
        draw.rounded_rectangle([62, name_y + 86, 140, name_y + 90], radius=2, fill=accent_rgb)

    # Contact Info
    contact_items = []
    if phone: contact_items.append(('M', phone))
    if email: contact_items.append(('E', email))
    if website: contact_items.append(('W', website))
    if address: contact_items.append(('A', address))

    y_pos = name_y + 120
    for prefix, val in contact_items[:4]:
        draw.rounded_rectangle([62, y_pos, 96, y_pos + 28], radius=6, outline=accent_rgb, width=1)
        draw.text((74, y_pos + 5), prefix, fill=accent_rgb, font=font_contact)
        draw.text((110, y_pos + 5), val, fill=text_rgb, font=font_contact)
        y_pos += 44
    buf = io.BytesIO()
    img.save(buf, format='PNG', quality=95)
    return buf.getvalue()


def render_business_card_image(card_data, reference_image=None, front_html=None, css=None):
    """
    Master business card image generator:
    1. Highest fidelity: Uses wkhtmltoimage if available to render Gemini's custom HTML+CSS
    2. Reference fidelity: If reference_image provided, composites user data on reference artwork
    3. Dynamic canvas: Fallback modern responsive canvas matching user colors and data
    """
    png_bytes = None

    # 1. Try HTML to Image if wkhtmltoimage is installed
    if front_html:
        png_bytes = render_html_to_image(front_html, css)

    # 2. If reference_image is present and wkhtmltoimage did not render, use reference composite
    if not png_bytes and reference_image:
        png_bytes = render_reference_card_composite(reference_image, card_data)

    # 3. Dynamic canvas fallback
    if not png_bytes:
        png_bytes = render_dynamic_canvas_image(card_data)

    b64_str = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"
    return png_bytes, b64_str
