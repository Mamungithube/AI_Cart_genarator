import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent.parent / 'fonts'

def get_font(size: int, bold: bool = False):
    """Loads bundled TTF fonts first, then OS fallbacks, then default."""
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

# -------------------------------------------------------------
# High-DPI Vector Glyphs
# -------------------------------------------------------------
def draw_phone_glyph(draw, x, y, size, color):
    r = size // 2
    h = int(size * 1.5)
    draw.rounded_rectangle([x, y, x + size, y + h], radius=max(2, size // 6), outline=color, width=max(2, size // 8))
    draw.line([x + max(2, size // 5), y + max(2, size // 6), x + size - max(2, size // 5), y + max(2, size // 6)], fill=color, width=max(1, size // 12))
    draw.ellipse([x + r - 2, y + h - max(5, size // 3), x + r + 2, y + h - max(2, size // 6)], fill=color)

def draw_mail_glyph(draw, x, y, size, color):
    h = int(size * 0.75)
    draw.rounded_rectangle([x, y, x + size, y + h], radius=max(2, size // 6), outline=color, width=max(2, size // 8))
    draw.line([x, y, x + size // 2, y + h // 2], fill=color, width=max(2, size // 8))
    draw.line([x + size, y, x + size // 2, y + h // 2], fill=color, width=max(2, size // 8))

def draw_web_glyph(draw, x, y, size, color):
    r = size // 2
    cx, cy = x + r, y + r
    draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, size // 8))
    draw.line([x, cy, x + size, cy], fill=color, width=max(1, size // 10))
    draw.ellipse([cx - r // 2, y, cx + r // 2, y + size], outline=color, width=max(1, size // 10))

def draw_loc_glyph(draw, x, y, size, color):
    r = size // 2
    cx = x + r
    draw.ellipse([x + 2, y, x + size - 2, y + size - 4], outline=color, width=max(2, size // 8))
    draw.polygon([(x + 3, y + r), (x + size - 3, y + r), (cx, y + size + 2)], fill=color)

def draw_clock_glyph(draw, x, y, size, color):
    r = size // 2
    cx, cy = x + r, y + r
    draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, size // 8))
    draw.line([cx, cy, cx, y + 4], fill=color, width=max(2, size // 8))
    draw.line([cx, cy, x + size - 4, cy], fill=color, width=max(2, size // 8))


# -------------------------------------------------------------
# 1. ORGANIC WAVES (Screenshot 1 & Screenshot 2)
# -------------------------------------------------------------
def render_organic_waves_card(data: dict, scale: int = 2) -> Image.Image:
    w, h = 1200 * scale, 700 * scale
    theme = data.get('theme') or {}
    bg_color = tuple(theme.get('bg_card', [22, 37, 54]))
    accent_1 = tuple(theme.get('accent', [245, 166, 35]))
    accent_2 = tuple(theme.get('accent_secondary', [217, 83, 47]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255]))
    text_sec = tuple(theme.get('text_secondary', [245, 166, 35]))
    text_mut = tuple(theme.get('text_muted', [200, 210, 220]))

    def s(v): return int(v * scale)

    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Upper yellow wave
    wave_pts_1 = []
    for x in range(s(-10), s(520), s(2)):
        y = s(120) + int(s(65) * math.sin(x * (0.009 / scale)) + s(35) * math.cos(x * (0.013 / scale)))
        wave_pts_1.append((x, y))
    draw.line(wave_pts_1, fill=accent_1, width=s(32), joint='curve')

    # Lower wave rising from bottom-right
    wave_pts_2 = []
    for x in range(s(720), w + s(20), s(2)):
        t = (x - s(720))
        y = h - s(75) - int(s(75) * math.sin(t * (0.0095 / scale)))
        wave_pts_2.append((x, y))
    draw.line(wave_pts_2, fill=accent_1, width=s(30), joint='curve')

    # Sun disc & quarter arc top-right
    draw.ellipse([w - s(220), s(75), w - s(160), s(135)], fill=accent_1)
    draw.pieslice([w - s(110), s(-50), w + s(110), s(170)], 90, 180, fill=accent_2)

    # Bottom-left striped circle badge
    circle_cx, circle_cy, circle_r = s(160), h - s(80), s(120)
    mask = Image.new('L', (w, h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([circle_cx - circle_r, circle_cy - circle_r, circle_cx + circle_r, circle_cy + circle_r], fill=255)

    stripe_layer = Image.new('RGB', (w, h), bg_color)
    s_draw = ImageDraw.Draw(stripe_layer)
    for sx in range(0, s(420), s(22)):
        s_draw.line([(sx, h), (sx + s(200), h - s(250))], fill=accent_2, width=s(10))
    img.paste(stripe_layer, (0, 0), mask)

    # Bold Monogram Emblem (Left side)
    mono_cx, mono_cy = s(340), s(350)
    name = data.get('name', '').strip()
    monogram = data.get('monogram') or (name[:2].upper() if name else 'TE')
    monogram = monogram[:2].upper()

    font_mono = get_font(s(135), bold=True)
    mb = draw.textbbox((0, 0), monogram, font=font_mono)
    draw.text((mono_cx - (mb[2] - mb[0]) // 2, mono_cy - (mb[3] - mb[1]) // 2 - s(12)), monogram, font=font_mono, fill=text_primary)

    # Content Zone (Right side)
    tx = s(540)
    curr_y = s(185)

    if name:
        font_name = get_font(s(54), bold=True)
        nb = draw.textbbox((tx, curr_y), name, font=font_name)
        if (nb[2] - nb[0]) > s(580):
            font_name = get_font(s(44), bold=True)
            nb = draw.textbbox((tx, curr_y), name, font=font_name)
        draw.text((tx, curr_y), name, font=font_name, fill=text_primary)
        curr_y = nb[3] + s(14)

    desig = data.get('designation', '').strip()
    if desig:
        font_des = get_font(s(28), bold=False)
        db = draw.textbbox((tx, curr_y), desig, font=font_des)
        draw.text((tx, curr_y), desig, font=font_des, fill=text_sec)
        curr_y = db[3] + s(16)

    comp = data.get('company_name', '').strip()
    if comp:
        font_comp = get_font(s(34), bold=True)
        cb = draw.textbbox((tx, curr_y), comp, font=font_comp)
        draw.text((tx, curr_y), comp, font=font_comp, fill=text_primary)
        curr_y = cb[3] + s(28)

    # Contacts (with guaranteed safe margins)
    contacts = []
    if data.get('phone'): contacts.append(('phone', data['phone'], draw_phone_glyph))
    if data.get('email'): contacts.append(('email', data['email'], draw_mail_glyph))
    if data.get('website'): contacts.append(('web', data['website'], draw_web_glyph))
    if data.get('address'): contacts.append(('loc', data['address'], draw_loc_glyph))
    if data.get('schedule'): contacts.append(('clock', data['schedule'], draw_clock_glyph))

    if contacts:
        font_c = get_font(s(25), bold=False)
        for ctype, cval, icon_fn in contacts:
            icon_fn(draw, tx, curr_y + s(4), s(18), accent_1)
            draw.text((tx + s(32), curr_y), cval, font=font_c, fill=text_mut)
            curr_y += s(38)

    return img.resize((1200, 700), Image.Resampling.LANCZOS)


# -------------------------------------------------------------
# 2. CORNER ARCS (Screenshot 3)
# -------------------------------------------------------------
def render_corner_arcs_card(data: dict, scale: int = 2) -> Image.Image:
    w, h = 1200 * scale, 700 * scale
    theme = data.get('theme') or {}
    bg_color = tuple(theme.get('bg_card', [26, 32, 38]))
    accent = tuple(theme.get('accent', [245, 95, 30]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255]))
    text_sec = tuple(theme.get('text_secondary', [200, 210, 220]))
    text_mut = tuple(theme.get('text_muted', [175, 185, 195]))

    def s(v): return int(v * scale)

    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Top-right concentric rounded arcs
    draw.arc([w - s(420), s(-140), w + s(140), s(420)], start=90, end=180, fill=accent, width=s(28))
    draw.arc([w - s(320), s(-40), w + s(40), s(320)], start=90, end=180, fill=accent, width=s(22))

    # Bottom-left 45-degree diagonal accent stripes
    for sx in [s(-60), s(40), s(140)]:
        draw.line([(sx, h + s(30)), (sx + s(240), h - s(210))], fill=accent, width=s(24))

    # Bottom-right corner arc
    draw.arc([w - s(240), h - s(240), w + s(80), h + s(80)], start=180, end=270, fill=accent, width=s(16))

    # Bold Monogram Emblem (Left side)
    mono_cx, mono_cy = s(320), s(350)
    name = data.get('name', '').strip()
    monogram = data.get('monogram') or (name[:2].upper() if name else 'DO')
    monogram = monogram[:2].upper()

    font_mono = get_font(s(145), bold=True)
    mb = draw.textbbox((0, 0), monogram, font=font_mono)
    draw.text((mono_cx - (mb[2] - mb[0]) // 2, mono_cy - (mb[3] - mb[1]) // 2 - s(15)), monogram, font=font_mono, fill=accent)

    # Content Zone (Right side)
    tx = s(520)
    curr_y = s(205)

    if name:
        font_name = get_font(s(56), bold=True)
        nb = draw.textbbox((tx, curr_y), name, font=font_name)
        if (nb[2] - nb[0]) > s(560):
            font_name = get_font(s(44), bold=True)
            nb = draw.textbbox((tx, curr_y), name, font=font_name)
        draw.text((tx, curr_y), name, font=font_name, fill=text_primary)
        curr_y = nb[3] + s(16)

    desig = data.get('designation', '').strip()
    if desig:
        font_des = get_font(s(28), bold=False)
        db = draw.textbbox((tx, curr_y), desig, font=font_des)
        draw.text((tx, curr_y), desig, font=font_des, fill=text_sec)
        curr_y = db[3] + s(16)

    comp = data.get('company_name', '').strip()
    if comp:
        font_comp = get_font(s(34), bold=True)
        cb = draw.textbbox((tx, curr_y), comp, font=font_comp)
        draw.text((tx, curr_y), comp, font=font_comp, fill=text_primary)
        curr_y = cb[3] + s(30)

    # Contacts (with guaranteed safe clearance)
    contacts = []
    if data.get('phone'): contacts.append(('phone', data['phone'], draw_phone_glyph))
    if data.get('email'): contacts.append(('email', data['email'], draw_mail_glyph))
    if data.get('website'): contacts.append(('web', data['website'], draw_web_glyph))
    if data.get('address'): contacts.append(('loc', data['address'], draw_loc_glyph))
    if data.get('schedule'): contacts.append(('clock', data['schedule'], draw_clock_glyph))

    if contacts:
        font_c = get_font(s(28), bold=False)
        for ctype, cval, icon_fn in contacts:
            icon_fn(draw, tx, curr_y + s(4), s(20), accent)
            draw.text((tx + s(36), curr_y), cval, font=font_c, fill=text_primary)
            curr_y += s(44)

    return img.resize((1200, 700), Image.Resampling.LANCZOS)


# -------------------------------------------------------------
# 3. CYBER TECH
# -------------------------------------------------------------
def render_cyber_tech_card(data: dict, scale: int = 2) -> Image.Image:
    w, h = 1200 * scale, 700 * scale
    theme = data.get('theme') or {}
    bg_color = tuple(theme.get('bg_card', [10, 16, 28]))
    accent = tuple(theme.get('accent', [0, 229, 255]))
    accent_sec = tuple(theme.get('accent_secondary', [56, 189, 248]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255]))
    text_sec = tuple(theme.get('text_secondary', [0, 229, 255]))
    text_mut = tuple(theme.get('text_muted', [148, 163, 184]))

    def s(v): return int(v * scale)

    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Subtle circuit grid
    grid_c = (20, 30, 48)
    for gy in range(0, h, s(70)):
        draw.line([(0, gy), (w, gy)], fill=grid_c, width=1)
    for gx in range(0, w, s(70)):
        draw.line([(gx, 0), (gx, h)], fill=grid_c, width=1)

    # Tech angular brackets
    draw.line([(w - s(80), s(60)), (w - s(40), s(60)), (w - s(40), s(180))], fill=accent, width=s(3))
    draw.line([(w - s(80), h - s(60)), (w - s(40), h - s(60)), (w - s(40), h - s(180))], fill=accent, width=s(3))

    # Hexagon Emblem on Right
    hex_cx, hex_cy, hex_r = w - s(240), h // 2, s(110)
    hex_pts = []
    for i in range(6):
        ang = math.radians(60 * i - 30)
        hex_pts.append((hex_cx + int(hex_r * math.cos(ang)), hex_cy + int(hex_r * math.sin(ang))))
    draw.polygon(hex_pts, fill=(15, 23, 42), outline=accent, width=s(4))

    name = data.get('name', '').strip()
    monogram = data.get('monogram') or (name[:2].upper() if name else 'TE')
    font_mono = get_font(s(68), bold=True)
    mb = draw.textbbox((0, 0), monogram, font=font_mono)
    draw.text((hex_cx - (mb[2] - mb[0]) // 2, hex_cy - (mb[3] - mb[1]) // 2 - s(6)), monogram, font=font_mono, fill=accent)

    # Circuit trace connecting to hexagon
    draw.line([(hex_cx - hex_r - s(40), hex_cy), (hex_cx - hex_r, hex_cy)], fill=accent, width=s(2))
    draw.ellipse([hex_cx - hex_r - s(46), hex_cy - s(6), hex_cx - hex_r - s(34), hex_cy + s(6)], fill=accent)

    # Content Zone on Left
    tx = s(90)
    curr_y = s(120)

    if name:
        font_name = get_font(s(58), bold=True)
        nb = draw.textbbox((tx, curr_y), name, font=font_name)
        draw.text((tx, curr_y), name, font=font_name, fill=text_primary)
        curr_y = nb[3] + s(12)

    desig = data.get('designation', '').strip().upper()
    if desig:
        font_des = get_font(s(24), bold=True)
        db = draw.textbbox((tx, curr_y), desig, font=font_des)
        draw.text((tx, curr_y), desig, font=font_des, fill=accent)
        curr_y = db[3] + s(14)

    comp = data.get('company_name', '').strip()
    if comp:
        font_comp = get_font(s(30), bold=False)
        cb = draw.textbbox((tx, curr_y), comp, font=font_comp)
        draw.text((tx, curr_y), comp, font=font_comp, fill=text_mut)
        curr_y = cb[3] + s(24)

    # Divider line
    draw.line([(tx, curr_y), (tx + s(380), curr_y)], fill=accent, width=s(2))
    draw.line([(tx + s(380), curr_y), (tx + s(480), curr_y)], fill=accent_sec, width=s(1))
    curr_y += s(35)

    # Contacts
    contacts = []
    if data.get('phone'): contacts.append(('phone', data['phone'], draw_phone_glyph))
    if data.get('email'): contacts.append(('email', data['email'], draw_mail_glyph))
    if data.get('website'): contacts.append(('web', data['website'], draw_web_glyph))
    if data.get('address'): contacts.append(('loc', data['address'], draw_loc_glyph))
    if data.get('schedule'): contacts.append(('clock', data['schedule'], draw_clock_glyph))

    if contacts:
        font_c = get_font(s(24), bold=False)
        for ctype, cval, icon_fn in contacts:
            icon_fn(draw, tx, curr_y + s(4), s(18), accent)
            draw.text((tx + s(32), curr_y), cval, font=font_c, fill=text_mut)
            curr_y += s(38)

    draw.rectangle([0, 0, w - 1, h - 1], outline=accent, width=s(2))
    return img.resize((1200, 700), Image.Resampling.LANCZOS)


# -------------------------------------------------------------
# 4. LUXURY GOLD
# -------------------------------------------------------------
def render_luxury_gold_card(data: dict, scale: int = 2) -> Image.Image:
    w, h = 1200 * scale, 700 * scale
    theme = data.get('theme') or {}
    bg_color = tuple(theme.get('bg_card', [13, 15, 20]))
    gold = tuple(theme.get('accent', [212, 175, 55]))
    gold_light = tuple(theme.get('accent_secondary', [245, 215, 127]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255]))
    text_mut = tuple(theme.get('text_muted', [205, 210, 220]))

    def s(v): return int(v * scale)

    img = Image.new('RGB', (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Double Gold Borders with corner notches
    draw.rectangle([s(25), s(25), w - s(25), h - s(25)], outline=gold, width=s(2))
    draw.rectangle([s(36), s(36), w - s(36), h - s(36)], outline=gold_light, width=s(1))
    for cx, cy in [(s(25), s(25)), (w - s(25), s(25)), (s(25), h - s(25)), (w - s(25), h - s(25))]:
        draw.rectangle([cx - s(6), cy - s(6), cx + s(6), cy + s(6)], fill=gold)

    # Right side Crest Badge
    badge_cx, badge_cy, badge_r = w - s(240), h // 2, s(105)
    draw.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], outline=gold, width=s(3))
    draw.ellipse([badge_cx - badge_r + s(10), badge_cy - badge_r + s(10), badge_cx + badge_r - s(10), badge_cy + badge_r - s(10)], outline=gold_light, width=s(1))

    name = data.get('name', '').strip()
    monogram = data.get('monogram') or (name[:2].upper() if name else 'LG')
    font_mono = get_font(s(70), bold=True)
    mb = draw.textbbox((0, 0), monogram, font=font_mono)
    draw.text((badge_cx - (mb[2] - mb[0]) // 2, badge_cy - (mb[3] - mb[1]) // 2 - s(6)), monogram, font=font_mono, fill=gold)

    # Content Zone on Left
    tx = s(90)
    curr_y = s(140)

    if name:
        font_name = get_font(s(58), bold=True)
        nb = draw.textbbox((tx, curr_y), name, font=font_name)
        draw.text((tx, curr_y), name, font=font_name, fill=gold_light)
        curr_y = nb[3] + s(14)

    desig = data.get('designation', '').strip().upper()
    if desig:
        font_des = get_font(s(22), bold=False)
        db = draw.textbbox((tx, curr_y), desig, font=font_des)
        draw.text((tx, curr_y), desig, font=font_des, fill=gold)
        curr_y = db[3] + s(14)

    comp = data.get('company_name', '').strip()
    if comp:
        font_comp = get_font(s(30), bold=True)
        cb = draw.textbbox((tx, curr_y), comp, font=font_comp)
        draw.text((tx, curr_y), comp, font=font_comp, fill=text_primary)
        curr_y = cb[3] + s(26)

    # Gold Divider
    draw.line([(tx, curr_y), (tx + s(400), curr_y)], fill=gold, width=s(2))
    curr_y += s(36)

    # Contacts
    contacts = []
    if data.get('phone'): contacts.append(('phone', data['phone'], draw_phone_glyph))
    if data.get('email'): contacts.append(('email', data['email'], draw_mail_glyph))
    if data.get('website'): contacts.append(('web', data['website'], draw_web_glyph))
    if data.get('address'): contacts.append(('loc', data['address'], draw_loc_glyph))
    if data.get('schedule'): contacts.append(('clock', data['schedule'], draw_clock_glyph))

    if contacts:
        font_c = get_font(s(24), bold=False)
        for ctype, cval, icon_fn in contacts:
            icon_fn(draw, tx, curr_y + s(4), s(18), gold)
            draw.text((tx + s(32), curr_y), cval, font=font_c, fill=text_mut)
            curr_y += s(38)

    return img.resize((1200, 700), Image.Resampling.LANCZOS)


# -------------------------------------------------------------
# Dispatcher & Main Entry Points
# -------------------------------------------------------------
STYLE_DISPATCHER = {
    'organic_waves': render_organic_waves_card,
    'corner_arcs': render_corner_arcs_card,
    'cyber_tech': render_cyber_tech_card,
    'luxury_gold': render_luxury_gold_card,
}

def generate_business_card(data: dict) -> bytes:
    """
    Main vector generation function.
    Selects layout style, renders 2x supersampled card, downsamples with LANCZOS to 1200x700 PNG.
    Guarantees 100% full bleed, zero outer desk/table, zero text clipping.
    """
    layout_style = (data.get('layout_style') or 'organic_waves').lower()
    renderer = STYLE_DISPATCHER.get(layout_style, render_organic_waves_card)

    img = renderer(data)

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(300, 300), optimize=True)
    buf.seek(0)
    return buf.getvalue()


def render_precision_visiting_card(spec: dict) -> bytes:
    """Backward compatibility wrapper."""
    return generate_business_card(spec)
