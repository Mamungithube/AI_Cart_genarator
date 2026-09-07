import os
import io
import json
import math
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path('/app/generator/fonts')

def get_font(size: int, bold: bool = False):
    font_candidates = [
        FONTS_DIR / ('bold.ttf' if bold else 'regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/freefont') / ('FreeSansBold.ttf' if bold else 'FreeSans.ttf'),
        Path('C:/Windows/Fonts') / ('arialbd.ttf' if bold else 'arial.ttf'),
    ]
    for c in font_candidates:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def draw_clock_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    r = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)
    draw.line([cx, cy, cx, cy - r + 3], fill=color, width=2)
    draw.line([cx, cy, cx + r - 4, cy], fill=color, width=2)
    draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=color)

def draw_phone_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    r = size // 2
    draw.rounded_rectangle([cx - r + 4, cy - r, cx + r - 4, cy + r], radius=3, outline=color, width=2)
    draw.line([cx - 3, cy - r + 3, cx + 3, cy - r + 3], fill=color, width=1)
    draw.ellipse([cx - 1, cy + r - 4, cx + 1, cy + r - 2], fill=color)

def draw_serial_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    w = size - 2
    h = int(size * 0.8)
    draw.rounded_rectangle([cx - w//2, cy - h//2, cx + w//2, cy + h//2], radius=2, outline=color, width=2)
    draw.line([cx - w//2 + 3, cy - 2, cx + w//2 - 3, cy - 2], fill=color, width=1)
    draw.line([cx - w//2 + 3, cy + 2, cx + w//2 - 3, cy + 2], fill=color, width=1)

def draw_mail_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    w = size
    h = int(size * 0.7)
    left, top, right, bottom = cx - w//2, cy - h//2, cx + w//2, cy + h//2
    draw.rounded_rectangle([left, top, right, bottom], radius=2, outline=color, width=2)
    draw.line([left, top, cx, cy + 2], fill=color, width=2)
    draw.line([right, top, cx, cy + 2], fill=color, width=2)

def draw_globe_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    r = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)
    draw.line([cx - r, cy, cx + r, cy], fill=color, width=1)
    draw.ellipse([cx - r//2, cy - r, cx + r//2, cy + r], outline=color, width=1)

def draw_github_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    r = size // 2
    draw.line([cx - 2, cy - r + 3, cx - r + 2, cy], fill=color, width=2)
    draw.line([cx - r + 2, cy, cx - 2, cy + r - 3], fill=color, width=2)
    draw.line([cx + 2, cy - r + 3, cx + r - 2, cy], fill=color, width=2)
    draw.line([cx + r - 2, cy, cx + 2, cy + r - 3], fill=color, width=2)

def draw_location_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    r = size // 2 - 1
    pin_y = cy - 2
    draw.ellipse([cx - r, pin_y - r, cx + r, pin_y + r], outline=color, width=2)
    draw.ellipse([cx - 2, pin_y - 2, cx + 2, pin_y + 2], fill=color)
    draw.polygon([(cx - r + 2, pin_y + 3), (cx + r - 2, pin_y + 3), (cx, cy + r)], fill=color)

ICON_DISPATCH = {
    'phone': draw_phone_icon,
    'serial': draw_serial_icon,
    'email': draw_mail_icon,
    'website': draw_globe_icon,
    'github': draw_github_icon,
    'schedule': draw_clock_icon,
    'location': draw_location_icon,
}

def parse_card_info_with_llm(user_prompt: str, api_key: str) -> dict:
    """Extracts all visiting card fields and determines the dynamic theme."""
    system_msg = (
        "You are an Elite Visiting Card Designer & Information Architect.\n"
        "Your task is to thoroughly analyze the user's prompt and extract EVERY single detail provided.\n\n"
        "CRITICAL EXTRACTION RULES:\n"
        "1. Extract ALL information:\n"
        "   - Name\n"
        "   - Designation / Role\n"
        "   - Degrees / Qualifications / Subtitle (e.g. 'MBBS, FCPS (Medicine)' or 'Lead AI Engineer')\n"
        "   - Company / Clinic / Hospital / Institution\n"
        "   - Every contact item: Phone, Serial / Appointment number, Email, Website, GitHub, Schedule / Visiting hours, Chamber / Location / Address.\n"
        "2. NEVER HALLUCINATE OR PREDICT FAKE DATA:\n"
        "   - If no phone is provided, DO NOT add a phone item!\n"
        "   - If no email is provided, DO NOT add an email item!\n"
        "   - ONLY include what the user explicitly stated!\n"
        "3. THEME & COLOR PALETTE:\n"
        "   - Detect if theme should be dark or light:\n"
        "     * Tech / Cyber / Dark Slate: is_dark=true, bg_card=[15, 23, 42], panel_bg=[10, 16, 30], accent=[0, 229, 255], accent_secondary=[56, 189, 248], text_primary=[255, 255, 255], text_secondary=[0, 229, 255], text_muted=[203, 213, 225], badge_bg=[15, 23, 42].\n"
        "     * Medical / Doctor / Clean White: is_dark=false, bg_card=[255, 255, 255], panel_bg=[13, 148, 136], accent=[16, 185, 129], accent_secondary=[204, 251, 241], text_primary=[15, 23, 42], text_secondary=[13, 148, 136], text_muted=[51, 65, 85], badge_bg=[255, 255, 255].\n"
        "     * Executive / Luxury Gold: is_dark=true, bg_card=[11, 15, 25], panel_bg=[18, 24, 38], accent=[212, 175, 55], accent_secondary=[245, 215, 127], text_primary=[255, 255, 255], text_secondary=[212, 175, 55], text_muted=[203, 213, 225], badge_bg=[11, 15, 25].\n\n"
        "Return ONLY JSON:\n"
        "{\n"
        "  \"name\": \"...\",\n"
        "  \"designation\": \"...\",\n"
        "  \"degrees\": \"...\",\n"
        "  \"company_name\": \"...\",\n"
        "  \"monogram\": \"2-3 letter initials for logo (e.g. 'AR' or 'NL' or 'RI')\",\n"
        "  \"theme\": {\n"
        "     \"is_dark\": true/false,\n"
        "     \"bg_card\": [r, g, b],\n"
        "     \"panel_bg\": [r, g, b],\n"
        "     \"accent\": [r, g, b],\n"
        "     \"accent_secondary\": [r, g, b],\n"
        "     \"text_primary\": [r, g, b],\n"
        "     \"text_secondary\": [r, g, b],\n"
        "     \"text_muted\": [r, g, b],\n"
        "     \"badge_bg\": [r, g, b]\n"
        "  },\n"
        "  \"info_items\": [\n"
        "     {\"type\": \"phone|serial|email|website|github|schedule|location\", \"label\": \"...\", \"value\": \"...\"}\n"
        "  ]\n"
        "}"
    )

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }).encode()

    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        data = json.loads(res.read())
        return json.loads(data['choices'][0]['message']['content'])


def render_precision_visiting_card(spec: dict) -> bytes:
    """Renders a 1200x700 ultra-premium visiting card with 100% full card coverage."""
    width = 1200
    height = 700

    theme = spec.get('theme', {})
    is_dark = theme.get('is_dark', True)
    bg_card = tuple(theme.get('bg_card', [15, 23, 42] if is_dark else [255, 255, 255]))
    panel_bg = tuple(theme.get('panel_bg', [10, 16, 30] if is_dark else [13, 148, 136]))
    accent = tuple(theme.get('accent', [0, 229, 255] if is_dark else [16, 185, 129]))
    accent_sec = tuple(theme.get('accent_secondary', [56, 189, 248] if is_dark else [204, 251, 241]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255] if is_dark else [15, 23, 42]))
    text_secondary = tuple(theme.get('text_secondary', [0, 229, 255] if is_dark else [13, 148, 136]))
    text_muted = tuple(theme.get('text_muted', [203, 213, 225] if is_dark else [51, 65, 85]))
    badge_bg = tuple(theme.get('badge_bg', [15, 23, 42] if is_dark else [255, 255, 255]))

    # Initialize canvas
    img = Image.new('RGB', (width, height), color=bg_card)
    draw = ImageDraw.Draw(img)

    # Subtle background pattern for tech cards
    if is_dark:
        for x_offset in range(0, 750, 75):
            line_c = (bg_card[0] + 8, bg_card[1] + 10, bg_card[2] + 16)
            draw.line([(x_offset, 0), (x_offset + 250, height)], fill=line_c, width=1)
    else:
        # Subtle light medical texture
        for x_offset in range(0, 750, 60):
            line_c = (241, 245, 249)
            draw.line([(x_offset, 0), (x_offset + 200, height)], fill=line_c, width=1)

    # 2. Dynamic Right-side Geometric Brand Panel
    panel_x_top = 750
    panel_x_bottom = 660

    # Layer 1: Outer glowing ribbon / accent cut
    draw.polygon([
        (panel_x_top - 20, 0),
        (width, 0),
        (width, height),
        (panel_x_bottom - 20, height)
    ], fill=accent_sec)

    # Layer 2: Main Brand Panel
    draw.polygon([
        (panel_x_top, 0),
        (width, 0),
        (width, height),
        (panel_x_bottom, height)
    ], fill=panel_bg)

    # Layer 3: Sharp Accent Trim Line
    draw.line([(panel_x_top - 6, 0), (panel_x_bottom - 6, height)], fill=accent, width=4)

    # 3. Monogram Emblem Badge inside Brand Panel
    badge_cx = 940
    badge_cy = 280
    badge_radius = 80

    # Halo glow around emblem
    glow_steps = 15
    for s in range(glow_steps):
        r_step = badge_radius + (glow_steps - s) * 2
        alpha = (s + 1) / (glow_steps * 4.0)
        c_glow = (
            int(panel_bg[0] + (accent[0] - panel_bg[0]) * alpha),
            int(panel_bg[1] + (accent[1] - panel_bg[1]) * alpha),
            int(panel_bg[2] + (accent[2] - panel_bg[2]) * alpha),
        )
        draw.ellipse([badge_cx - r_step, badge_cy - r_step, badge_cx + r_step, badge_cy + r_step], fill=c_glow)

    # Hexagonal Emblem
    hex_pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        hx = badge_cx + int(badge_radius * math.cos(angle))
        hy = badge_cy + int(badge_radius * math.sin(angle))
        hex_pts.append((hx, hy))
    draw.polygon(hex_pts, fill=badge_bg, outline=accent, width=4)

    # Inner hexagon trim
    inner_hex = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        hx = badge_cx + int((badge_radius - 12) * math.cos(angle))
        hy = badge_cy + int((badge_radius - 12) * math.sin(angle))
        inner_hex.append((hx, hy))
    draw.polygon(inner_hex, outline=accent_sec, width=2)

    # Monogram Initials
    monogram = spec.get('monogram', 'NL')[:3].upper()
    font_mono = get_font(52, bold=True)
    m_bbox = draw.textbbox((0, 0), monogram, font=font_mono)
    m_w = m_bbox[2] - m_bbox[0]
    m_h = m_bbox[3] - m_bbox[1]
    mono_color = accent if is_dark else panel_bg
    draw.text((badge_cx - m_w // 2, badge_cy - m_h // 2 - 4), monogram, font=font_mono, fill=mono_color)

    # Company / Hospital / Clinic Name below Emblem
    company_name = spec.get('company_name', '').strip().upper()
    if company_name:
        font_comp = get_font(24, bold=True)
        comp_bbox = draw.textbbox((0, 0), company_name, font=font_comp)
        comp_w = comp_bbox[2] - comp_bbox[0]
        if comp_w > 400:
            font_comp = get_font(19, bold=True)
            comp_bbox = draw.textbbox((0, 0), company_name, font=font_comp)
            comp_w = comp_bbox[2] - comp_bbox[0]
        
        comp_text_color = (255, 255, 255) if is_dark or (sum(panel_bg)/3 < 150) else (15, 23, 42)
        draw.text((badge_cx - comp_w // 2, badge_cy + badge_radius + 35), company_name, font=font_comp, fill=comp_text_color)
        draw.line([badge_cx - 50, badge_cy + badge_radius + 70, badge_cx + 50, badge_cy + badge_radius + 70], fill=accent, width=2)

    # 4. Content Zone (Left Side)
    margin_x = 75
    curr_y = 65

    # Name
    name = spec.get('name', '').strip()
    font_name = get_font(52, bold=True)
    draw.text((margin_x, curr_y), name, font=font_name, fill=text_primary)
    name_bbox = draw.textbbox((margin_x, curr_y), name, font=font_name)
    curr_y = name_bbox[3] + 12

    # Designation
    designation = spec.get('designation', '').strip().upper()
    if designation:
        font_desig = get_font(24, bold=True)
        draw.text((margin_x, curr_y), designation, font=font_desig, fill=text_secondary)
        des_bbox = draw.textbbox((margin_x, curr_y), designation, font=font_desig)
        curr_y = des_bbox[3] + 8

    # Degrees / Qualifications
    degrees = spec.get('degrees', '').strip()
    if degrees:
        font_deg = get_font(21, bold=False)
        draw.text((margin_x, curr_y), degrees, font=font_deg, fill=text_muted)
        deg_bbox = draw.textbbox((margin_x, curr_y), degrees, font=font_deg)
        curr_y = deg_bbox[3] + 8

    # Sleek Horizontal Accent Divider
    curr_y += 10
    draw.line([margin_x, curr_y, margin_x + 360, curr_y], fill=accent, width=3)
    draw.line([margin_x + 360, curr_y, margin_x + 480, curr_y], fill=accent_sec, width=1)
    curr_y += 35

    # 5. Dynamic Information Items
    info_items = spec.get('info_items', [])
    valid_items = [item for item in info_items if item.get('value', '').strip()]

    item_count = len(valid_items)
    row_gap = 48 if item_count <= 4 else (42 if item_count <= 5 else 36)
    icon_r = 18 if item_count <= 5 else 16
    font_item = get_font(21 if item_count <= 4 else (19 if item_count <= 5 else 17), bold=False)

    for item in valid_items:
        itype = item.get('type', 'phone').lower()
        val = item.get('value', '').strip()
        label = item.get('label', '').strip()

        # Display text with appropriate label prefix if not already present
        if itype in ['schedule', 'serial', 'location'] and label and not val.lower().startswith(label.lower()):
            display_text = f"{label}: {val}"
        else:
            display_text = val

        icx = margin_x + icon_r + 2
        icy = curr_y + icon_r

        # Icon circular container
        icon_circle_bg = (24, 34, 58) if is_dark else (241, 245, 249)
        draw.ellipse([icx - icon_r, icy - icon_r, icx + icon_r, icy + icon_r], fill=icon_circle_bg, outline=accent, width=2)

        # Draw icon
        draw_func = ICON_DISPATCH.get(itype, draw_phone_icon)
        draw_func(draw, icx, icy, size=int(icon_r * 1.2), color=accent)

        # Draw text
        text_x = icx + icon_r + 16
        text_y = curr_y + (icon_r * 2 - 20) // 2
        item_text_color = text_primary if itype in ['schedule', 'serial'] else text_muted
        draw.text((text_x, text_y), display_text, font=font_item, fill=item_text_color)

        curr_y += row_gap

    # Clean border around visiting card
    draw.rectangle([0, 0, width - 1, height - 1], outline=accent, width=2)

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(300, 300), optimize=True)
    buf.seek(0)
    return buf.getvalue()

print("Refined script ready")
