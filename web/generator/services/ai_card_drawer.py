import io
import os
import json
import base64
import logging
import urllib.request
from PIL import Image

logger = logging.getLogger(__name__)

SYSTEM_MSG = """You are an elite Graphic Design Director specializing in clean, modern, ultra-professional visiting cards.

Analyze the user's prompt with precision and extract ONLY the information explicitly provided.

CRITICAL DATA INTEGRITY RULES (ZERO TOLERANCE FOR FAKE OR PLACEHOLDER DATA):
1. NEVER INVENT OR PREDICT MISSING DATA:
   - Name: Extract full name.
   - Designation: ONLY if explicitly stated by user. If not provided, MUST be empty "". DO NOT invent titles like 'Developer', 'Executive', 'Doctor', 'Specialist', etc.
   - Company Name: ONLY if explicitly stated by user. Otherwise empty "".
   - Phone Number: ONLY if explicitly stated by user. Otherwise empty "".
   - Email Address: ONLY if explicitly stated by user. Otherwise empty "".
   - Address / Chamber Location: FULL address string ONLY if explicitly stated by user. Otherwise empty "".
   - Working Hours / Visiting Schedule: ONLY if explicitly stated by user. Otherwise empty "".
   - Website URL: ONLY if explicitly stated by user. Otherwise empty "".
   - Social Media / Links: ONLY if explicitly stated by user. Otherwise empty "".

2. DESIGN STYLE & COLOR THEME:
   - Select an appropriate modern color theme based on profession or request (e.g. tech: deep obsidian slate with cyan/teal accents; executive: dark navy with gold; medical: clean crisp white with emerald/mint wave).
   - Determine monogram initials (2-3 letters) derived from the name or company.

Return ONLY a JSON object:
{
  "name": string,
  "designation": string,
  "company_name": string,
  "address": string,
  "schedule": string,
  "phone": string,
  "email": string,
  "website": string,
  "monogram": string,
  "style_description": string
}"""


def analyze_and_design_card(user_prompt: str, api_key: str) -> dict:
    """Uses GPT-4o-mini as a Creative Director to extract exact facts without hallucination."""
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }).encode()

    try:
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=payload,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            result = json.loads(res.read())
            content = result['choices'][0]['message']['content']
            data = json.loads(content)
            logger.info(f"AI Creative Director Design Spec: {data}")
            return data
    except Exception as e:
        logger.error(f"Creative director reasoning failed: {e}")
        return {
            'name': user_prompt[:40],
            'designation': '',
            'company_name': '',
            'address': '',
            'schedule': '',
            'phone': '',
            'email': '',
            'website': '',
            'monogram': user_prompt[:2].upper(),
            'style_description': 'Modern minimalist visiting card design with clean typography and abstract geometric wave'
        }


def build_precision_dalle_prompt(card_spec: dict) -> str:
    """
    Constructs an airtight DALL-E prompt with:
    1. A strict whitelist of ONLY provided text.
    2. A strict blacklist banning fake/dummy phone numbers, emails, addresses, or icons.
    3. An unequivocal mandate for a flat 2D graphic file with 90-degree square corners (no 3D mockup, no desk/table).
    """
    name = card_spec.get('name', '').strip()
    designation = card_spec.get('designation', '').strip()
    company = card_spec.get('company_name', '').strip()
    phone = card_spec.get('phone', '').strip()
    email = card_spec.get('email', '').strip()
    address = card_spec.get('address', '').strip()
    schedule = card_spec.get('schedule', '').strip()
    website = card_spec.get('website', '').strip()
    monogram = card_spec.get('monogram', '').strip() or (name[:2].upper() if name else 'ID')
    style = card_spec.get('style_description', 'Sleek modern business card with bold typography and abstract vector accents')

    # 1. Text Whitelist
    whitelist = [f"Name: '{name}'"]
    if designation:
        whitelist.append(f"Title: '{designation}'")
    if company:
        whitelist.append(f"Company: '{company}'")
    if phone:
        whitelist.append(f"Phone: '{phone}' (with phone icon)")
    if email:
        whitelist.append(f"Email: '{email}' (with mail icon)")
    if address:
        whitelist.append(f"Address: '{address}' (with location pin icon)")
    if schedule:
        whitelist.append(f"Schedule: '{schedule}' (with clock icon)")
    if website:
        whitelist.append(f"Website: '{website}' (with globe icon)")

    whitelist_text = ", ".join(whitelist)

    # 2. Strict Blacklist for any absent fields
    blacklist = []
    if not phone:
        blacklist.append("DO NOT render any phone number or phone icon (ABSOLUTELY NO +00, NO +123, NO dummy numbers)")
    if not email:
        blacklist.append("DO NOT render any email address or mail icon (ABSOLUTELY NO dummy@email.com)")
    if not address:
        blacklist.append("DO NOT render any address or location pin icon (ABSOLUTELY NO 123 Anywhere St, NO fake cities)")
    if not designation:
        blacklist.append("DO NOT render any job title or designation below the name")
    if not schedule:
        blacklist.append("DO NOT render any visiting hours or clock icon")
    if not website:
        blacklist.append("DO NOT render any website URL or globe icon")

    blacklist_text = "; ".join(blacklist)

    prompt = (
        f"A full-bleed flat digital graphic layout, exact 1536x1024 rectangular wallpaper canvas. "
        f"Sharp 90-degree square corners filling 100% of the entire rectangle from corner (0,0) to (1536,1024) edge-to-edge. "
        f"{style}. "
        f"Prominent stylish monogram emblem with initials '{monogram}'. "
        f"EXACT TEXT TO RENDER (AND NOTHING ELSE): {whitelist_text}. "
        f"STRICT PROHIBITIONS: {blacklist_text}. ABSOLUTELY ZERO placeholder text, dummy numbers, or fake contact info! "
        f"CANVAS MANDATE: Edge-to-edge flat 2D digital print file filling 100% of the 1536x1024 frame with zero outer margins. "
        f"ABSOLUTELY NO 3D mockup, NO perspective angle, NO table, NO desk, NO floor, NO shadows outside, NO rounded corners, NO background surface. The entire 1536x1024 image file IS the card surface."
    )
    return prompt


def generate_dalle_card(dalle_prompt: str, api_key: str) -> bytes | None:
    """Calls OpenAI image generation model with the tailor-made creative prompt."""
    logger.info(f"Generating DALL-E image with prompt: {dalle_prompt}")

    model_configs = [
        ('gpt-image-1', '1536x1024'),
        ('chatgpt-image-latest', '1536x1024'),
        ('dall-e-3', '1792x1024'),
    ]

    for model, size in model_configs:
        try:
            payload = json.dumps({
                'model': model,
                'prompt': dalle_prompt,
                'n': 1,
                'size': size
            }).encode()

            req = urllib.request.Request(
                'https://api.openai.com/v1/images/generations',
                data=payload,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                }
            )

            with urllib.request.urlopen(req, timeout=120) as res:
                result = json.loads(res.read())
                item = result.get('data', [{}])[0]
                if 'b64_json' in item:
                    return base64.b64decode(item['b64_json'])
                elif 'url' in item:
                    with urllib.request.urlopen(item['url'], timeout=30) as img_res:
                        return img_res.read()

        except urllib.error.HTTPError as e:
            logger.error(f"OpenAI image generation error model={model}: {e.code} {e.read().decode(errors='ignore')}")
            continue
        except Exception as e:
            logger.error(f"OpenAI image generation exception model={model}: {e}")
            continue
    return None


def auto_crop_card_surface(image_bytes: bytes) -> bytes:
    """
    Outside-in boundary detection:
    Scans from the extreme outer borders inward.
    As soon as it crosses the outer background and detects the first edge peak
    (the card's physical boundary line), it records the coordinate and immediately stops.
    It NEVER scans into the interior of the card, guaranteeing 100% safety
    for monograms, logos, and typography.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        gray = img.convert("L")

        y_mid_start = int(h * 0.25)
        y_mid_end = int(h * 0.75)
        y_samples = list(range(y_mid_start, y_mid_end, 3))
        n_y = max(len(y_samples), 1)

        x_mid_start = int(w * 0.25)
        x_mid_end = int(w * 0.75)
        x_samples = list(range(x_mid_start, x_mid_end, 3))
        n_x = max(len(x_samples), 1)

        def scan_edge(get_grad_func, start, end, step, lookahead=45, min_start=2.8):
            hit_idx = None
            for i in range(start, end, step):
                if get_grad_func(i) >= min_start:
                    hit_idx = i
                    break
            if hit_idx is None:
                return None
            limit = min(max(start, end), max(min(start, end), hit_idx + step * lookahead))
            search_range = range(hit_idx, limit, step)
            best_idx = hit_idx
            best_val = get_grad_func(hit_idx)
            for j in search_range:
                val = get_grad_func(j)
                if val > best_val:
                    best_val = val
                    best_idx = j
            return best_idx if best_val >= 3.8 else None

        left_edge = scan_edge(
            lambda x: sum(abs(gray.getpixel((x, y)) - gray.getpixel((x - 1, y))) for y in y_samples) / n_y,
            int(w * 0.02), int(w * 0.20), 1, lookahead=45
        )
        right_edge = scan_edge(
            lambda x: sum(abs(gray.getpixel((x, y)) - gray.getpixel((x - 1, y))) for y in y_samples) / n_y,
            w - 2, int(w * 0.70), -1, lookahead=80
        )
        top_edge = scan_edge(
            lambda y: sum(abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 1))) for x in x_samples) / n_x,
            int(h * 0.02), int(h * 0.20), 1, lookahead=45
        )
        bot_edge = scan_edge(
            lambda y: sum(abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 1))) for x in x_samples) / n_x,
            h - 2, int(h * 0.70), -1, lookahead=160
        )

        c_left = (left_edge + 2) if left_edge is not None else 0
        c_right = (right_edge - 2) if right_edge is not None else w
        c_top = (top_edge + 2) if top_edge is not None else 0
        c_bottom = (bot_edge - 2) if bot_edge is not None else h

        # Verify validity: must retain at least 60% of original dimensions
        if (c_right - c_left) >= int(w * 0.60) and (c_bottom - c_top) >= int(h * 0.60):
            if (c_left > 0) or (c_top > 0) or (c_right < w) or (c_bottom < h):
                logger.info(f"Auto-crop removing outer borders: left={c_left}, top={c_top}, right={c_right}, bottom={c_bottom}")
                cropped = img.crop((c_left, c_top, c_right, c_bottom))
                buf = io.BytesIO()
                cropped.save(buf, format="PNG", optimize=True)
                return buf.getvalue()

        return image_bytes
    except Exception as e:
        logger.error(f"Auto-crop error: {e}")
        return image_bytes


def generate_hybrid_business_card(prompt: str) -> tuple[bytes, dict]:
    """
    Main entry point for visiting card generation:
    1. GPT-4o-mini extracts exact facts, enforces zero hallucination of missing contacts.
    2. Constructs a bespoke prompt with whitelisted text and strict prohibitions.
    3. OpenAI Image Model generates the flat 2D edge-to-edge card.
    4. Auto-crop cleanly strips any outer border / backdrop while preserving logos.
    """
    api_key = (
        os.environ.get('OPENAI_API_KEY') or
        os.environ.get('Open_AI_Key') or
        ''
    ).strip()

    if not api_key:
        logger.warning("OPENAI_API_KEY missing. Using fallback card.")
        from .card_drawer import generate_business_card
        card_data = {'name': prompt[:40], 'designation': '', 'company_name': '',
                     'phone': '', 'email': '', 'website': '', 'linkedin': ''}
        return generate_business_card(card_data), card_data

    logger.info("Step 0: Creative Director deep reasoning & strict fact extraction...")
    card_spec = analyze_and_design_card(prompt, api_key)

    card_data = {
        'name':         card_spec.get('name', '').strip(),
        'designation':  card_spec.get('designation', '').strip(),
        'company_name': card_spec.get('company_name', '').strip() or card_spec.get('address', '').strip(),
        'phone':        card_spec.get('phone', '').strip(),
        'email':        card_spec.get('email', '').strip(),
        'website':      card_spec.get('website', '').strip(),
        'linkedin':     card_spec.get('linkedin', '').strip(),
    }

    dalle_prompt = card_spec.get('dalle_prompt') or build_precision_dalle_prompt(card_spec)

    logger.info("Step 1: Generating bespoke visiting card via OpenAI image model...")
    raw_bytes = generate_dalle_card(dalle_prompt, api_key)

    if raw_bytes:
        card_bytes = auto_crop_card_surface(raw_bytes)
        logger.info("Step 2: Successfully produced pure visiting card!")
        return card_bytes, card_data
    else:
        logger.warning("OpenAI image generation failed. Falling back to precision card drawer.")
        from .card_drawer import generate_business_card
        return generate_business_card(card_spec), card_data


