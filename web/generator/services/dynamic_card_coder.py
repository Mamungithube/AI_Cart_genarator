import io
import re
import math
import random
import logging
import urllib.request
import urllib.error
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from card_project.notifications import send_openai_error_notification, is_openai_error

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).resolve().parent.parent / 'fonts'


# -------------------------------------------------------------
# 1. Bulletproof Font Manager for the Sandbox
# -------------------------------------------------------------
class FontManager:
    """Provides reliable font loading for sandbox execution across Linux & Windows."""

    def __init__(self):
        self._cache = {}
        self._font_candidates = [
            # Bundled
            (FONTS_DIR / 'bold.ttf', FONTS_DIR / 'regular.ttf'),
            # Linux container
            (Path('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
             Path('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf')),
            (Path('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'),
             Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')),
            (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
             Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')),
            # Windows host
            (Path('C:/Windows/Fonts/arialbd.ttf'), Path('C:/Windows/Fonts/arial.ttf')),
            (Path('C:/Windows/Fonts/segoeuib.ttf'), Path('C:/Windows/Fonts/segoeui.ttf')),
        ]

    def get_font(self, size: int, bold: bool = False):
        cache_key = (int(size), bool(bold))
        if cache_key in self._cache:
            return self._cache[cache_key]

        size = max(10, min(140, int(size)))
        for bold_path, reg_path in self._font_candidates:
            target = bold_path if bold else reg_path
            if target.exists():
                try:
                    f = ImageFont.truetype(str(target), size)
                    self._cache[cache_key] = f
                    return f
                except Exception:
                    continue

        try:
            f = ImageFont.load_default(size=size)
        except Exception:
            f = ImageFont.load_default()
        self._cache[cache_key] = f
        return f


GLOBAL_FONTS = FontManager()


# -------------------------------------------------------------
# 2. Injected Vector Helper Utilities (Available to AI Code)
# -------------------------------------------------------------
def draw_linear_gradient(img: Image.Image, color_start: tuple, color_end: tuple, direction: str = 'diagonal'):
    """Fills img with a smooth linear gradient."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    if direction == 'vertical':
        for y in range(h):
            ratio = y / max(1, h - 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
    elif direction == 'horizontal':
        for x in range(w):
            ratio = x / max(1, w - 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))
    else:  # diagonal
        diag_len = math.hypot(w, h)
        for i in range(int(diag_len) + 1):
            ratio = min(1.0, i / diag_len)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            x0 = int(i * (w / diag_len))
            y0 = int(i * (h / diag_len))
            draw.line([(x0 - h, y0 + w), (x0 + h, y0 - w)], fill=(r, g, b), width=2)


def draw_monogram_badge(draw, fonts, initials: str, cx: int, cy: int, radius: int = 55,
                        bg_color: tuple = (30, 40, 60), border_color: tuple = (212, 175, 55),
                        text_color: tuple = (255, 255, 255), shape: str = 'circle', border_width: int = 3):
    """Draws a world-class stylized monogram badge with initials centered."""
    if not initials:
        initials = "VC"
    initials = str(initials)[:3].upper()
    font_size = max(18, int(radius * 0.72))
    font = fonts.get_font(font_size, bold=True)

    if shape == 'hexagon':
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            pts.append((cx + int(radius * math.cos(angle)), cy + int(radius * math.sin(angle))))
        draw.polygon(pts, fill=bg_color, outline=border_color, width=border_width)
    elif shape == 'square':
        draw.rounded_rectangle([cx - radius, cy - radius, cx + radius, cy + radius], radius=max(4, radius // 4),
                               fill=bg_color, outline=border_color, width=border_width)
        inner_r = max(4, radius - 6)
        draw.rounded_rectangle([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], radius=max(2, inner_r // 4),
                               outline=border_color, width=1)
    elif shape == 'diamond':
        pts = [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)]
        draw.polygon(pts, fill=bg_color, outline=border_color, width=border_width)
    else:  # circle
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=bg_color, outline=border_color, width=border_width)
        inner_r = max(4, radius - 6)
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], outline=border_color, width=1)

    draw.text((cx, cy), initials, font=font, fill=text_color, anchor='mm')


def draw_icon(draw, icon_name: str, x: int, y: int, size: int, color: tuple):
    """Draws vector icons: phone, email, website, address, schedule."""
    r = size // 2
    icon_name = str(icon_name).lower()
    if icon_name in ('phone', 'mobile', 'tel'):
        h = int(size * 1.4)
        draw.rounded_rectangle([x, y, x + size, y + h], radius=max(2, size // 6), outline=color, width=max(2, size // 8))
        draw.line([x + max(2, size // 5), y + max(2, size // 6), x + size - max(2, size // 5), y + max(2, size // 6)], fill=color, width=max(1, size // 12))
        draw.ellipse([x + r - 2, y + h - max(5, size // 3), x + r + 2, y + h - max(2, size // 6)], fill=color)
    elif icon_name in ('email', 'mail'):
        h = int(size * 0.75)
        draw.rounded_rectangle([x, y, x + size, y + h], radius=max(2, size // 6), outline=color, width=max(2, size // 8))
        draw.line([x, y, x + size // 2, y + h // 2], fill=color, width=max(2, size // 8))
        draw.line([x + size, y, x + size // 2, y + h // 2], fill=color, width=max(2, size // 8))
    elif icon_name in ('website', 'web', 'globe', 'url'):
        cx, cy = x + r, y + r
        draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, size // 8))
        draw.line([x, cy, x + size, cy], fill=color, width=max(1, size // 10))
        draw.ellipse([cx - r // 2, y, cx + r // 2, y + size], outline=color, width=max(1, size // 10))
    elif icon_name in ('address', 'location', 'loc', 'map'):
        cx = x + r
        draw.ellipse([x + 2, y, x + size - 2, y + size - 4], outline=color, width=max(2, size // 8))
        draw.polygon([(x + 3, y + r), (x + size - 3, y + r), (cx, y + size + 2)], fill=color)
    elif icon_name in ('schedule', 'clock', 'time'):
        cx, cy = x + r, y + r
        draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, size // 8))
        draw.line([cx, cy, cx, y + 4], fill=color, width=max(2, size // 8))
        draw.line([cx, cy, x + size - 4, cy], fill=color, width=max(2, size // 8))
    else:  # default pin
        cx = x + r
        draw.ellipse([x + 2, y, x + size - 2, y + size - 4], outline=color, width=max(2, size // 8))


# -------------------------------------------------------------
# 3. OpenAI Code Generation Prompts
# -------------------------------------------------------------
CODER_SYSTEM_PROMPT = """You are an elite Graphic Design Director and Expert Python Canvas Programmer (like ChatGPT Canvas / Code Interpreter).
Your mission is to generate clean, high-performance Python Pillow (PIL) code that programmatically renders a bespoke, award-winning visiting card.

CRITICAL EXECUTION RULES:
1. Output ONLY valid Python code wrapped in ```python ... ``` block. No conversational filler or explanations outside the block.
2. The code MUST define a function with signature:
   def draw_visiting_card(fonts) -> Image.Image:
   CRITICAL: Do NOT declare extra required positional arguments (e.g. DO NOT do `def draw_visiting_card(fonts, phone, email)`). Put all card text values directly as local variables inside the function body!
3. Canvas Dimensions: Exactly 1200 width by 700 height:
   w, h = 1200, 700
   img = Image.new('RGB', (w, h), bg_color)
   draw = ImageDraw.Draw(img)
4. Use `fonts.get_font(size, bold=False)` to obtain ImageFont objects. NEVER hardcode OS font filepaths or call `ImageFont.truetype` with local filepaths.
5. Injected helpers available in scope:
   - `draw_linear_gradient(img, color_start, color_end, direction='diagonal'|'vertical'|'horizontal')`
   - `draw_monogram_badge(draw, fonts, initials, cx, cy, radius=55, bg_color=..., border_color=..., text_color=..., shape='circle'|'hexagon'|'square'|'diamond', border_width=3)`
   - `draw_icon(draw, icon_name, x, y, size, color)` where icon_name in ['phone', 'email', 'website', 'address', 'schedule']
   - Standard modules: `math`, `random`, `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFilter`
6. LOGO & MONOGRAM BADGE MANDATE:
   - NEVER draw a generic briefcase icon as the card logo!
   - ALWAYS create a stylized Monogram Badge using `draw_monogram_badge()` with the person's initials (e.g. 'MM', 'TI', 'SA') or custom geometric badge.
7. COMPOSITION & LAYOUT DIVERSITY:
   - You MUST strictly implement the layout according to the requested COMPOSITION VARIANT and LAYOUT STYLE directives in the prompt.
   - Every card must feel uniquely tailored to the profession — NEVER use a generic single-column layout!
   - Draw rich background geometry (borders, diagonal cuts, circuit lines, wave arcs, or color panels) that utilize the entire 1200x700 canvas.
8. Centering Helper: To center text at (cx, cy), use `draw.text((cx, cy), text, font=font, fill=color, anchor='mm')`.
9. RETURN: The function MUST return the PIL `img` object.
"""

REFINER_SYSTEM_PROMPT = """You are an expert Python Canvas Programmer maintaining visual design continuity (like ChatGPT Canvas).
You are given an existing Python visiting card script and a user instruction to update it.

CRITICAL RULES:
1. PRESERVE THE VISUAL DESIGN: Keep the visual layout, background art, colors, shapes, and badges from the existing code UNLESS the user explicitly asks to change them (e.g. "change color to blue", "redesign").
2. For text or contact updates (e.g. "change name", "add phone", "update designation"):
   - Modify ONLY the target text variables/constants in the script.
   - Retain all other coordinates, styling, and graphics unchanged.
3. Output ONLY the updated Python code wrapped in ```python ... ``` block. No filler explanations.
4. Must maintain `def draw_visiting_card(fonts) -> Image.Image:`.
"""

HEALER_SYSTEM_PROMPT = """You are an expert Python debugger fixing a broken PIL visiting card script.
You are given the failed Python code and the exact error traceback.
Fix the error and return ONLY the corrected, fully working Python code inside ```python ... ``` block.
Do not change the design intent, just fix the bug/syntax error.
"""


# -------------------------------------------------------------
# 4. LLM API Call Utility
# -------------------------------------------------------------
def call_llm(messages: list, api_key: str, temperature: float = 0.4) -> str:
    """Calls OpenAI chat completions API via urllib."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2500,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            return body['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"OpenAI API error {e.code}: {err_body}")
        raise RuntimeError(f"OpenAI API error {e.code}: {err_body}")
    except Exception as e:
        logger.error(f"OpenAI connection error: {e}")
        raise RuntimeError(f"OpenAI connection error: {e}")


def extract_python_code(raw_response: str) -> str:
    """Extracts Python code block from markdown response."""
    match = re.search(r'```(?:python)?\s*\n(.*?)\n```', raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_response.strip()


# -------------------------------------------------------------
# 5. Dynamic Code Generation & Refinement
# -------------------------------------------------------------
def generate_card_code(card_data: dict, user_prompt: str, api_key: str) -> str:
    """Generates a bespoke Python Pillow visiting card rendering script from scratch."""
    name = card_data.get('name', '')
    desig = card_data.get('designation', '')
    comp = card_data.get('company_name', '')
    tagline = card_data.get('tagline', '')
    phone = card_data.get('phone') or card_data.get('phones', [])
    if isinstance(phone, list):
        phone = phone[0] if phone else ''
    email = card_data.get('email') or card_data.get('emails', [])
    if isinstance(email, list):
        email = email[0] if email else ''
    website = card_data.get('website') or card_data.get('websites', [])
    if isinstance(website, list):
        website = website[0] if website else ''
    address = card_data.get('address', '')
    schedule = card_data.get('schedule', '')
    monogram = card_data.get('monogram') or (name[:2].upper() if name else 'VC')

    layout_style = card_data.get('layout_style', 'minimal_clean')
    comp_variant = card_data.get('composition_variant', 'left_monogram_stack')
    theme = card_data.get('theme') or {}

    bg_card = tuple(theme.get('bg_card', [18, 24, 38]))
    accent = tuple(theme.get('accent', [212, 175, 55]))
    accent_sec = tuple(theme.get('accent_secondary', [245, 215, 127]))
    text_primary = tuple(theme.get('text_primary', [255, 255, 255]))
    text_secondary = tuple(theme.get('text_secondary', accent))
    text_muted = tuple(theme.get('text_muted', [180, 190, 205]))

    comp_guides = {
        'centered_hero': (
            "COMPOSITION: Centered Hero Layout\n"
            "- Draw a prominent monogram badge centered at (cx=600, cy=180).\n"
            "- Name in large bold font centered at (600, 310) using anchor='mm'.\n"
            "- Designation in uppercase tracked accent color centered at (600, 370) using anchor='mm'.\n"
            "- Company name centered at (600, 420) using anchor='mm'.\n"
            "- Draw an elegant horizontal divider line (e.g. from x=450 to x=750 at y=460) with accent color.\n"
            "- Arrange contact items (phone, email, website, address) at the bottom in a balanced, centered horizontal row or 2 neat centered columns."
        ),
        'split_diagonal': (
            "COMPOSITION: Split Diagonal / Two-Tone Geometric Layout\n"
            "- Draw a dramatic angular division across the 1200x700 canvas using `draw.polygon([(0, 0), (750, 0), (450, 700), (0, 700)], fill=...)` or similar.\n"
            "- Zone 1 (Left/Angle): Background with Monogram badge and Company branding.\n"
            "- Zone 2 (Right): High-contrast area with Name, Designation, and cleanly aligned Contact rows.\n"
            "- Draw an accent separation line along the diagonal split."
        ),
        'top_banner': (
            "COMPOSITION: Top Banner / Architectural Header Layout\n"
            "- Draw a distinct, contrasting banner band across the top (y=0 to y=190) with subtle gradient or solid accent.\n"
            "- In top banner: place the Monogram badge at (140, 95) and Company Name with tagline at (240, 95).\n"
            "- In lower canvas (y=230 to 670): place the Person's Name in huge bold typography (x=140, y=280), Designation in accent color (x=140, y=350), and aligned contact rows with icons (x=140, y=430 to 600)."
        ),
        'right_aligned_monogram': (
            "COMPOSITION: Right-Aligned Badge & Asymmetric Framing\n"
            "- Place a large, elegant monogram crest/badge on the right side of the canvas (cx=960, cy=350, radius=85).\n"
            "- Left/Center area (x=120 to x=800): Name in large bold (x=120, y=180), Designation (x=120, y=250), Company (x=120, y=300), followed by clean contact rows with icons.\n"
            "- Draw a vertical accent framing line or gradient band at x=850."
        ),
        'asymmetric_offset': (
            "COMPOSITION: Modern Asymmetric Offset Layout\n"
            "- Offset layout with modern negative space.\n"
            "- Draw geometric color slabs or vertical accent stripe on one side.\n"
            "- Monogram badge positioned in an offset corner (e.g. cx=180, cy=520 or cx=1020, cy=180).\n"
            "- Crisp typography with generous margins."
        ),
        'left_monogram_stack': (
            "COMPOSITION: Left Monogram Stack with Vertical Division\n"
            "- Place the Monogram Badge with initials at (cx=180, cy=250, radius=70).\n"
            "- Draw a sleek vertical accent divider line (x=300 from y=120 to y=580) or vertical color column.\n"
            "- Right of divider (starting at x=360):\n"
            "  * Name: Large bold font (size 52-58) at y=180\n"
            "  * Designation: Uppercase tracked accent color at y=250\n"
            "  * Company: Distinct contrast at y=300\n"
            "  * Contact rows with icons: Spaced neatly starting from y=380 to y=560."
        ),
    }

    style_guides = {
        'luxury_gold': (
            "STYLE: Luxury Gold & Obsidian\n"
            "- Background: Deep obsidian/onyx or rich dark charcoal.\n"
            "- Draw a delicate double-line gold metallic border inset 35px from edges with corner diamond accents.\n"
            "- Use gold/amber accent colors for titles, badge borders, and icons.\n"
            "- Badge shape: 'circle' with gold double-ring."
        ),
        'cyber_tech': (
            "STYLE: Cyber Tech / Developer\n"
            "- Background: Deep navy/midnight cyber dark.\n"
            "- Draw electric cyan circuit trace lines, subtle grid dots, angled tech brackets at corners, or glowing digital divider bars.\n"
            "- Badge shape: 'hexagon' with electric cyan/neon border."
        ),
        'organic_waves': (
            "STYLE: Organic Waves / Creative Artistic\n"
            "- Background: Artistic gradient or vibrant pastel/warm tone.\n"
            "- Draw 2-3 overlapping sweeping curved arcs or wave shapes across one corner or along the bottom/side.\n"
            "- Badge shape: 'circle' or 'diamond' with fluid styling."
        ),
        'minimal_clean': (
            "STYLE: Minimal Clean / Scandinavian Modern\n"
            "- Background: Crisp high-contrast layout.\n"
            "- Razor-sharp typography, ample negative space, single bold accent divider line.\n"
            "- Badge shape: 'square' with rounded corners."
        ),
        'corporate_blue': (
            "STYLE: Corporate Blue / Institutional\n"
            "- Deep navy and royal sapphire color palette with crisp white typography.\n"
            "- Structured geometric header/footer or vertical sidebar band.\n"
            "- Badge shape: 'circle' or 'square'."
        ),
        'bold_editorial': (
            "STYLE: Bold Editorial / High-Impact\n"
            "- High-contrast typographic blocks, bold saturated color fields, heavy headlines.\n"
            "- Badge shape: 'square' or 'diamond'."
        ),
    }

    comp_directive = comp_guides.get(comp_variant, comp_guides['left_monogram_stack'])
    style_directive = style_guides.get(layout_style, style_guides['minimal_clean'])

    spec_summary = {
        "name": name,
        "designation": desig,
        "company_name": comp,
        "tagline": tagline,
        "phone": phone,
        "email": email,
        "website": website,
        "address": address,
        "schedule": schedule,
        "monogram": monogram,
        "layout_style": layout_style,
        "composition_variant": comp_variant,
        "theme_colors": {
            "bg_card": bg_card,
            "accent": accent,
            "accent_secondary": accent_sec,
            "text_primary": text_primary,
            "text_secondary": text_secondary,
            "text_muted": text_muted,
        }
    }

    user_msg = (
        f"USER REQUEST: {user_prompt}\n\n"
        f"CARD DATA & THEME SPECIFICATION:\n{json.dumps(spec_summary, indent=2)}\n\n"
        f"MANDATORY DESIGN DIRECTIVES:\n"
        f"1. {comp_directive}\n\n"
        f"2. {style_directive}\n\n"
        f"3. MONOGRAM BADGE:\n"
        f"   Call `draw_monogram_badge(draw, fonts, initials='{monogram}', cx=..., cy=..., radius=..., "
        f"bg_color={bg_card}, border_color={accent}, text_color={text_primary}, shape='circle'|'hexagon'|'square'|'diamond')`.\n"
        f"   NEVER draw a briefcase icon!\n\n"
        f"4. PALETTE:\n"
        f"   bg_card={bg_card}, accent={accent}, accent_secondary={accent_sec}, "
        f"text_primary={text_primary}, text_secondary={text_secondary}, text_muted={text_muted}.\n\n"
        "Generate a complete, self-contained Python function `draw_visiting_card(fonts) -> Image.Image` "
        "that executes this exact blueprint at 1200x700 pixels."
    )

    messages = [
        {"role": "system", "content": CODER_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = call_llm(messages, api_key, temperature=0.5)
        code = extract_python_code(raw)
        return code
    except Exception as e:
        logger.warning(f"Dynamic code generation LLM call failed, using default fallback script: {e}")
        return build_default_fallback_code(card_data)


def refine_card_code(previous_code: str, card_data: dict, user_instruction: str, api_key: str) -> str:
    """Refines existing Python visiting card script while maintaining visual style continuity."""
    user_msg = (
        f"USER INSTRUCTION: {user_instruction}\n\n"
        f"UPDATED CARD DATA:\n{json.dumps(card_data, indent=2)}\n\n"
        f"PREVIOUS WORKING PYTHON CODE:\n```python\n{previous_code}\n```\n\n"
        "Update the code according to the instruction while strictly preserving the visual aesthetic, layout geometry, and colors."
    )

    messages = [
        {"role": "system", "content": REFINER_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = call_llm(messages, api_key, temperature=0.2)
        code = extract_python_code(raw)
        return code
    except Exception as e:
        logger.warning(f"Dynamic code refinement LLM call failed, keeping previous working code: {e}")
        return previous_code


def heal_card_code(failed_code: str, error_trace: str, api_key: str) -> str:
    """Self-healing loop: asks LLM to fix syntax or runtime errors."""
    user_msg = (
        f"The following visiting card Python script failed with this error:\n"
        f"ERROR: {error_trace}\n\n"
        f"FAILED CODE:\n```python\n{failed_code}\n```\n\n"
        "Fix the code and output ONLY the corrected Python script inside ```python ... ```."
    )

    messages = [
        {"role": "system", "content": HEALER_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    raw = call_llm(messages, api_key, temperature=0.1)
    return extract_python_code(raw)


# -------------------------------------------------------------
# 6. Secure Execution Sandbox with Auto-Healing
# -------------------------------------------------------------
def execute_card_code(
    code_str: str,
    card_data: dict | None = None,
    api_key: str | None = None,
    fonts: FontManager = GLOBAL_FONTS,
    max_retries: int = 2
) -> tuple[bytes, str]:
    """
    Executes Python Pillow drawing script in a safe sandbox.
    If execution fails, initiates automatic self-healing retry loop via LLM.
    Returns: (png_bytes, final_working_code)
    """
    current_code = code_str

    for attempt in range(max_retries + 1):
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            top = name.split('.')[0]
            if top in ('math', 'random', 'PIL', 'io'):
                return __import__(name, globals, locals, fromlist, level)
            raise ImportError(f"Importing module '{name}' is not permitted in sandbox.")

        # Prepare safe sandbox environment
        sandbox = {
            '__builtins__': {
                '__import__': safe_import,
                'range': range,
                'len': len,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'tuple': tuple,
                'list': list,
                'dict': dict,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'enumerate': enumerate,
                'zip': zip,
                'print': print,
            },
            'Image': Image,
            'ImageDraw': ImageDraw,
            'ImageFont': ImageFont,
            'ImageFilter': ImageFilter,
            'math': math,
            'random': random,
            'draw_linear_gradient': draw_linear_gradient,
            'draw_monogram_badge': draw_monogram_badge,
            'draw_icon': draw_icon,
            'fonts': fonts,
        }

        try:
            # 1. Execute script definition in sandbox
            exec(current_code, sandbox)

            # 2. Call draw_visiting_card function
            draw_fn = (
                sandbox.get('draw_visiting_card')
                or sandbox.get('draw_card')
                or sandbox.get('render_card')
                or sandbox.get('draw')
            )
            if draw_fn and callable(draw_fn):
                import inspect
                sig = inspect.signature(draw_fn)
                kwargs = {}
                for p_name in sig.parameters.keys():
                    if p_name in ('fonts', 'font', 'font_manager'):
                        kwargs[p_name] = fonts
                    elif p_name == 'card_data':
                        kwargs['card_data'] = card_data or {}
                    elif card_data and p_name in card_data:
                        val = card_data[p_name]
                        if isinstance(val, list):
                            val = val[0] if val else ''
                        kwargs[p_name] = str(val or '')
                    elif p_name in ('name', 'phone', 'email', 'website', 'address', 'company', 'designation', 'company_name'):
                        val = card_data.get(p_name, '') if card_data else ''
                        if isinstance(val, list):
                            val = val[0] if val else ''
                        kwargs[p_name] = str(val or '')
                    else:
                        kwargs[p_name] = ''

                if len(sig.parameters) == 0:
                    img = draw_fn()
                elif len(sig.parameters) == 1 and any(k in sig.parameters for k in ('fonts', 'font', 'font_manager')):
                    img = draw_fn(fonts)
                else:
                    img = draw_fn(**kwargs)
            elif 'img' in sandbox and isinstance(sandbox['img'], Image.Image):
                img = sandbox['img']
            else:
                raise ValueError("Script must define a callable `draw_visiting_card(fonts)` function.")

            if not isinstance(img, Image.Image):
                raise TypeError(f"draw_visiting_card returned {type(img)}, expected PIL.Image.Image")

            # 3. Ensure exact standard 1200x700 dimensions
            if img.size != (1200, 700):
                img = img.resize((1200, 700), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format='PNG', dpi=(300, 300))
            buf.seek(0)
            return buf.getvalue(), current_code

        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            logger.warning(f"Sandbox execution failed on attempt {attempt + 1}: {err_msg}")

            if attempt < max_retries and api_key:
                logger.info(f"Self-healing trigger: asking AI to fix script error...")
                try:
                    current_code = heal_card_code(current_code, err_msg, api_key)
                    continue
                except Exception as heal_err:
                    logger.error(f"Self-healing LLM call failed: {heal_err}")
                    break
            else:
                break

    # If all self-healing attempts fail:
    if card_data is not None:
        logger.warning(f"All dynamic execution attempts failed ({err_msg}). Falling back to robust default script.")
        fb_code = build_default_fallback_code(card_data)
        return execute_card_code(fb_code, card_data=None, max_retries=0)

    raise RuntimeError(f"Dynamic card execution failed after retries: {err_msg}")


# -------------------------------------------------------------
# 7. Reliable Default Script Fallback
# -------------------------------------------------------------
def build_default_fallback_code(card_data: dict) -> str:
    """Generates a clean fallback Python script if LLM is unavailable."""
    name = card_data.get('name', 'John Doe')
    desig = card_data.get('designation', 'Professional')
    comp = card_data.get('company_name', '')
    phone = card_data.get('phone', '')
    if isinstance(phone, list):
        phone = phone[0] if phone else ''
    email = card_data.get('email', '')
    if isinstance(email, list):
        email = email[0] if email else ''
    mono = card_data.get('monogram') or (name[:2].upper() if name else 'JD')

    return f"""def draw_visiting_card(fonts) -> Image.Image:
    w, h = 1200, 700
    img = Image.new('RGB', (w, h), (18, 24, 38))
    draw_linear_gradient(img, (28, 38, 58), (14, 18, 28), direction='diagonal')
    draw = ImageDraw.Draw(img)

    # Accent hairline frame
    draw.rectangle([25, 25, w - 25, h - 25], outline=(212, 175, 55), width=2)
    draw.rectangle([35, 35, w - 35, h - 35], outline=(245, 215, 127), width=1)

    # Monogram Crest
    cx, cy, r = 240, h // 2, 110
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(212, 175, 55), width=3)
    draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=(245, 215, 127), width=1)
    f_mono = fonts.get_font(68, bold=True)
    mb = draw.textbbox((0, 0), "{mono}", font=f_mono)
    draw.text((cx - (mb[2]-mb[0])//2, cy - (mb[3]-mb[1])//2 - 4), "{mono}", font=f_mono, fill=(212, 175, 55))

    # Content on right
    tx, curr_y = 440, 180
    f_name = fonts.get_font(56, bold=True)
    draw.text((tx, curr_y), "{name}", font=f_name, fill=(255, 255, 255))
    curr_y += 70

    if "{desig}":
        f_des = fonts.get_font(24, bold=True)
        draw.text((tx, curr_y), "{desig}".upper(), font=f_des, fill=(212, 175, 55))
        curr_y += 40

    if "{comp}":
        f_comp = fonts.get_font(26, bold=False)
        draw.text((tx, curr_y), "{comp}", font=f_comp, fill=(200, 210, 220))
        curr_y += 45

    draw.line([(tx, curr_y), (tx + 450, curr_y)], fill=(212, 175, 55), width=2)
    curr_y += 30

    if "{phone}":
        draw_icon(draw, 'phone', tx, curr_y + 2, 18, (212, 175, 55))
        draw.text((tx + 32, curr_y), "{phone}", font=fonts.get_font(22), fill=(185, 195, 205))
        curr_y += 38

    if "{email}":
        draw_icon(draw, 'email', tx, curr_y + 2, 18, (212, 175, 55))
        draw.text((tx + 32, curr_y), "{email}", font=fonts.get_font(22), fill=(185, 195, 205))

    return img
"""
