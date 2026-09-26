import io
import base64
from PIL import Image, ImageDraw, ImageFont

def render_business_card_image(card_data):
    """
    Renders an executive print-ready business card PNG image (1050x600 px)
    from card_data and returns (png_bytes, base64_data_uri).
    """
    width = 1050
    height = 600

    name = str(card_data.get('name') or "Executive Name")
    title = str(card_data.get('title') or "Professional Title")
    company = str(card_data.get('company') or "Company Name")
    tagline = str(card_data.get('tagline') or "ARCHITECTING EXCELLENCE")
    phone = str(card_data.get('phone') or "")
    email = str(card_data.get('email') or "")
    website = str(card_data.get('website') or "")
    address = str(card_data.get('address') or "")

    primary_color = card_data.get('primary_color') or "#090d16"
    accent_color = card_data.get('accent_color') or "#d4af37"

    # Normalize hex colors
    def hex_to_rgb(hex_code, fallback=(9, 13, 22)):
        try:
            h = hex_code.lstrip('#')
            if len(h) == 3:
                h = ''.join([c*2 for c in h])
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            return fallback

    bg_rgb = hex_to_rgb(primary_color, (9, 13, 22))
    accent_rgb = hex_to_rgb(accent_color, (212, 175, 55))
    is_dark = (bg_rgb[0] * 0.299 + bg_rgb[1] * 0.587 + bg_rgb[2] * 0.114) < 128
    text_rgb = (255, 255, 255) if is_dark else (15, 23, 42)
    muted_rgb = (148, 163, 184) if is_dark else (100, 116, 139)

    # 1. Base image
    img = Image.new('RGB', (width, height), color=bg_rgb)
    draw = ImageDraw.Draw(img)

    # 2. Subtle radial glow in top right
    glow_color = (
        int(accent_rgb[0] * 0.15 + bg_rgb[0] * 0.85),
        int(accent_rgb[1] * 0.15 + bg_rgb[1] * 0.85),
        int(accent_rgb[2] * 0.15 + bg_rgb[2] * 0.85),
    )
    for r in range(300, 0, -15):
        draw.ellipse([width - 150 - r, -50 - r, width - 150 + r, -50 + r], fill=glow_color)

    # 3. Inner border hairline
    border_color = (255, 255, 255, 25) if is_dark else (0, 0, 0, 25)
    draw.rounded_rectangle([12, 12, width - 12, height - 12], radius=16, outline=border_color[:3], width=1)

    # 4. Fonts
    font_name = ImageFont.load_default(size=40)
    font_title = ImageFont.load_default(size=18)
    font_company = ImageFont.load_default(size=24)
    font_tagline = ImageFont.load_default(size=14)
    font_contact = ImageFont.load_default(size=16)
    font_emblem = ImageFont.load_default(size=26)
    font_qr_label = ImageFont.load_default(size=12)

    # 5. Top Header (Company & Logo)
    initial = (company[:1] if company else "C").upper()
    emblem_box = [60, 50, 116, 106]
    draw.rounded_rectangle(emblem_box, radius=12, fill=accent_rgb)
    draw.text((76, 62), initial, fill=bg_rgb, font=font_emblem)

    draw.text((130, 56), company.upper(), fill=text_rgb, font=font_company)
    draw.text((130, 86), tagline.upper(), fill=muted_rgb, font=font_tagline)

    # 6. Main Info (Name & Title)
    draw.text((60, 200), name, fill=text_rgb, font=font_name)
    draw.text((62, 254), title.upper(), fill=accent_rgb, font=font_title)

    # Accent bar
    draw.rounded_rectangle([62, 286, 120, 290], radius=2, fill=accent_rgb)

    # 7. Contact Details Stack
    contact_items = []
    if phone: contact_items.append(('M', phone))
    if email: contact_items.append(('E', email))
    if website: contact_items.append(('W', website))
    if address: contact_items.append(('A', address))

    # Fallback default items if none extracted
    if not contact_items:
        contact_items = [('M', '+880 1xxx'), ('E', 'contact@company.com')]

    y_pos = 330
    for prefix, val in contact_items[:4]:
        # Chip
        draw.rounded_rectangle([62, y_pos, 96, y_pos + 30], radius=6, outline=accent_rgb, width=1)
        draw.text((74, y_pos + 6), prefix, fill=accent_rgb, font=font_title)
        draw.text((110, y_pos + 7), val, fill=text_rgb, font=font_contact)
        y_pos += 46

    # 8. Modern QR Code Box on the right side
    qr_x = width - 240
    qr_y = 180
    qr_size = 170

    # QR background container
    draw.rounded_rectangle([qr_x, qr_y, qr_x + qr_size, qr_y + qr_size], radius=14, fill=(255, 255, 255), outline=accent_rgb, width=2)

    # Draw geometric QR pattern blocks inside
    px = qr_x + 18
    py = qr_y + 18
    block_color = (15, 23, 42)

    # Top-left corner
    draw.rectangle([px, py, px + 36, py + 36], fill=block_color)
    draw.rectangle([px + 8, py + 8, px + 28, py + 28], fill=(255, 255, 255))
    draw.rectangle([px + 14, py + 14, px + 22, py + 22], fill=block_color)

    # Top-right corner
    draw.rectangle([px + 96, py, px + 132, py + 36], fill=block_color)
    draw.rectangle([px + 104, py + 8, px + 124, py + 28], fill=(255, 255, 255))
    draw.rectangle([px + 110, py + 14, px + 118, py + 22], fill=block_color)

    # Bottom-left corner
    draw.rectangle([px, py + 96, px + 36, py + 132], fill=block_color)
    draw.rectangle([px + 8, py + 104, px + 28, py + 124], fill=(255, 255, 255))
    draw.rectangle([px + 14, py + 110, px + 22, py + 118], fill=block_color)

    # Center matrix data dots
    draw.rectangle([px + 48, py + 10, px + 62, py + 24], fill=block_color)
    draw.rectangle([px + 72, py + 16, px + 84, py + 28], fill=block_color)
    draw.rectangle([px + 44, py + 48, px + 88, py + 88], fill=block_color)
    draw.rectangle([px + 98, py + 60, px + 118, py + 80], fill=block_color)
    draw.rectangle([px + 60, py + 104, px + 90, py + 124], fill=block_color)
    draw.rectangle([px + 104, py + 104, px + 128, py + 128], fill=block_color)

    # QR Label underneath
    draw.text((qr_x + 18, qr_y + qr_size + 14), "SCAN TO CONNECT", fill=accent_rgb, font=font_qr_label)

    # Bottom decorative accent bar
    draw.rectangle([0, height - 6, width, height], fill=accent_rgb)

    # 9. Output PNG bytes and base64
    buf = io.BytesIO()
    img.save(buf, format='PNG', quality=95)
    png_bytes = buf.getvalue()
    b64_str = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"

    return png_bytes, b64_str
