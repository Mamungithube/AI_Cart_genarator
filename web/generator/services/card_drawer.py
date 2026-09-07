import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Base directory for fonts
FONTS_DIR = Path(__file__).resolve().parent.parent / 'fonts'

THEMES = {
    'midnight_gold': {
        'bg_start': (11, 15, 23),       # Deep obsidian navy
        'bg_end': (22, 27, 46),         # Rich midnight blue
        'accent': (212, 175, 55),       # Metallic Gold
        'accent_glow': (245, 215, 127), # Warm pale gold
        'text_primary': (255, 255, 255),# Pure white
        'text_secondary': (212, 175, 55),# Gold designation
        'text_muted': (148, 163, 184),  # Slate light gray
        'card_border': (45, 55, 72),
        'icon_bg': (26, 32, 44),
        'icon_stroke': (212, 175, 55),
        'ribbon': (212, 175, 55),
    },
    'ocean_modern': {
        'bg_start': (6, 18, 38),        # Deep sapphire
        'bg_end': (15, 38, 75),         # Electric navy
        'accent': (6, 182, 212),        # Cyan / Aqua
        'accent_glow': (56, 189, 248),  # Sky blue
        'text_primary': (255, 255, 255),
        'text_secondary': (56, 189, 248),
        'text_muted': (186, 230, 253),
        'card_border': (30, 58, 138),
        'icon_bg': (12, 74, 110),
        'icon_stroke': (56, 189, 248),
        'ribbon': (6, 182, 212),
    },
    'minimal_clean': {
        'bg_start': (252, 252, 253),    # Off white
        'bg_end': (241, 245, 249),      # Cool slate 100
        'accent': (15, 23, 42),         # Deep graphite
        'accent_glow': (239, 68, 68),   # Crimson Swiss accent
        'text_primary': (15, 23, 42),   # Pitch black
        'text_secondary': (239, 68, 68),# Red accent for role
        'text_muted': (71, 85, 105),    # Slate gray
        'card_border': (226, 232, 240),
        'icon_bg': (226, 232, 240),
        'icon_stroke': (15, 23, 42),
        'ribbon': (239, 68, 68),
    },
    'slate_neon': {
        'bg_start': (15, 23, 42),       # Dark Slate 900
        'bg_end': (30, 41, 59),         # Slate 800
        'accent': (168, 85, 247),       # Neon Purple
        'accent_glow': (236, 72, 153),  # Cyber Pink
        'text_primary': (255, 255, 255),
        'text_secondary': (216, 180, 254),
        'text_muted': (148, 163, 184),
        'card_border': (71, 85, 105),
        'icon_bg': (51, 65, 85),
        'icon_stroke': (236, 72, 153),
        'ribbon': (168, 85, 247),
    },
}

def load_font(name: str, size: int):
    """
    Attempts to load bundled TTF fonts first, then OS fallbacks, then Pillow default.
    """
    font_files = [
        FONTS_DIR / f"{name}.ttf",
        FONTS_DIR / "bold.ttf" if name == "bold" else FONTS_DIR / "regular.ttf",
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if name == "bold" else "DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/freefont") / ("FreeSansBold.ttf" if name == "bold" else "FreeSans.ttf"),
        Path("C:/Windows/Fonts") / ("arialbd.ttf" if name == "bold" else "arial.ttf"),
    ]

    for candidate in font_files:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except Exception:
                continue

    # Fallback if no true-type font found
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def draw_gradient(draw: ImageDraw.ImageDraw, width: int, height: int, start_color: tuple, end_color: tuple):
    """Renders a smooth vertical linear gradient."""
    for y in range(height):
        ratio = y / float(height)
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_phone_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    """Draws a clean phone icon centered at (cx, cy)."""
    r = size // 2
    draw.rounded_rectangle([cx - r + 3, cy - r, cx + r - 3, cy + r], radius=4, outline=color, width=2)
    # Screen notch / speaker
    draw.line([cx - 3, cy - r + 4, cx + 3, cy - r + 4], fill=color, width=1)
    # Home button / chin dot
    draw.ellipse([cx - 2, cy + r - 6, cx + 2, cy + r - 2], fill=color)

def draw_mail_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    """Draws an envelope icon centered at (cx, cy)."""
    w = size
    h = int(size * 0.7)
    left = cx - w // 2
    top = cy - h // 2
    right = cx + w // 2
    bottom = cy + h // 2
    draw.rounded_rectangle([left, top, right, bottom], radius=2, outline=color, width=2)
    # Flap
    draw.line([left, top, cx, cy + 2], fill=color, width=2)
    draw.line([right, top, cx, cy + 2], fill=color, width=2)

def draw_globe_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple):
    """Draws a modern globe / web icon centered at (cx, cy)."""
    r = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)
    # Latitude line
    draw.line([cx - r, cy, cx + r, cy], fill=color, width=1)
    # Longitude ellipse
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy + r], outline=color, width=1)

def draw_monogram_emblem(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, initials: str, theme: dict, font):
    """Draws a modern geometric company badge."""
    # Outer hexagon or rotated diamond
    accent = theme['accent']
    pts = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        x = cx + int(radius * math.cos(angle_rad))
        y = cy + int(radius * math.sin(angle_rad))
        pts.append((x, y))

    draw.polygon(pts, fill=theme['icon_bg'], outline=accent)
    # Inner ring
    inner_pts = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        x = cx + int((radius - 6) * math.cos(angle_rad))
        y = cy + int((radius - 6) * math.sin(angle_rad))
        inner_pts.append((x, y))
    draw.polygon(inner_pts, outline=theme['accent_glow'])

    # Initials
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), initials, font=font, fill=theme['text_primary'])

def generate_business_card(data: dict) -> bytes:
    """
    Renders a standard 1050x600 px (3.5" x 2" at 300 DPI) business card in-memory
    using Pillow and returns PNG bytes.
    """
    width = 1050
    height = 600

    name = data.get('name', 'Alex Morgan').strip()
    designation = data.get('designation', 'Senior Software Architect').strip().upper()
    phone = data.get('phone', '+1 (555) 019-2834').strip()
    email = data.get('email', 'alex.morgan@company.com').strip()
    website = data.get('website', 'www.company.com').strip()
    company_name = data.get('company_name', 'NEXUS INNOVATIONS').strip().upper()
    theme_key = data.get('theme', 'midnight_gold')

    theme = THEMES.get(theme_key, THEMES['midnight_gold'])

    # Initialize canvas
    img = Image.new('RGB', (width, height), color=theme['bg_start'])
    draw = ImageDraw.Draw(img)

    # 1. Background Gradient
    draw_gradient(draw, width, height, theme['bg_start'], theme['bg_end'])

    # 2. Modern Decorative Geometric Accents (subtle grid / polygon lines)
    for i in range(5):
        offset = i * 28
        alpha_color = theme['card_border']
        draw.line([width - 320 + offset, 0, width, 320 - offset], fill=alpha_color, width=1)
        draw.line([width - 320 + offset, height, width, height - (320 - offset)], fill=alpha_color, width=1)

    # Left Ribbon / Accent Bar
    ribbon_w = 14
    draw.rectangle([0, 0, ribbon_w, height], fill=theme['ribbon'])
    draw.rectangle([ribbon_w, 0, ribbon_w + 3, height], fill=theme['accent_glow'])

    # Outer border for card definition
    draw.rectangle([0, 0, width - 1, height - 1], outline=theme['card_border'], width=2)

    # 3. Fonts
    font_company = load_font('bold', 20)
    font_name = load_font('bold', 46)
    font_role = load_font('bold', 20)
    font_contact = load_font('regular', 21)
    font_badge = load_font('bold', 26)

    # 4. Header: Company Monogram & Name
    initials = "".join([part[0] for part in company_name.split()[:2]]) if company_name else "NX"
    if not initials:
        initials = "NX"

    draw_monogram_emblem(draw, cx=80, cy=75, radius=32, initials=initials, theme=theme, font=font_badge)

    # Company name text
    draw.text((125, 65), company_name, font=font_company, fill=theme['text_primary'])
    # Decorative line under company
    draw.line([125, 93, 340, 93], fill=theme['accent'], width=2)

    # 5. Main Hero: Name and Designation
    hero_y = 190
    draw.text((70, hero_y), name, font=font_name, fill=theme['text_primary'])

    role_y = hero_y + 58
    draw.text((70, role_y), designation, font=font_role, fill=theme['text_secondary'])

    # Horizontal stylized divider line
    div_y = role_y + 42
    draw.line([70, div_y, 480, div_y], fill=theme['accent'], width=3)
    draw.line([480, div_y, 560, div_y], fill=theme['accent_glow'], width=1)

    # 6. Contact Information Section
    contact_items = [
        ('phone', phone, draw_phone_icon),
        ('email', email, draw_mail_icon),
        ('website', website, draw_globe_icon),
    ]

    start_contact_y = 350
    spacing = 58

    for idx, (label, val, icon_func) in enumerate(contact_items):
        item_y = start_contact_y + idx * spacing

        # Icon circular container
        icon_cx = 95
        icon_cy = item_y + 12
        r = 20
        draw.ellipse(
            [icon_cx - r, icon_cy - r, icon_cx + r, icon_cy + r],
            fill=theme['icon_bg'],
            outline=theme['icon_stroke'],
            width=2
        )

        # Draw vector icon
        icon_func(draw, icon_cx, icon_cy, size=18, color=theme['accent_glow'])

        # Draw contact label text
        draw.text((icon_cx + 34, item_y), val, font=font_contact, fill=theme['text_muted'])

    # 7. Modern Corner Accent / Tech Badge on Right
    badge_cx = width - 130
    badge_cy = height - 130
    # Stylized watermarked logo in background on right
    draw.ellipse([badge_cx - 80, badge_cy - 80, badge_cx + 80, badge_cy + 80], outline=theme['card_border'], width=2)
    draw.ellipse([badge_cx - 50, badge_cy - 50, badge_cx + 50, badge_cy + 50], outline=theme['accent'], width=1)
    draw.ellipse([badge_cx - 20, badge_cy - 20, badge_cx + 20, badge_cy + 20], fill=theme['accent'])

    # Save to in-memory bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', dpi=(300, 300), optimize=True)
    buffer.seek(0)
    return buffer.getvalue()
