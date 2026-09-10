import io
import os
import re
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
   - name: Full name string.
   - designation: Professional title / position string. If not provided, empty "".
   - department: Department or division string. If not provided, empty "".
   - qualifications: Array of academic or professional degrees/certifications [string] (e.g. ["MBBS (DMC)", "FCPS", "PhD in AI"]). If none, [].
   - company_name: Organization, company, or clinic name string. If not provided, empty "".
   - tagline: Company slogan, motto, or business subtitle string. If not provided, empty "".
   - phone: Array of phone/mobile/hotline numbers [string] (e.g. ["+880 1837..."]). If none, [].
   - email: Array of email addresses [string] (e.g. ["user@example.com"]). If none, [].
   - website: Array of website URLs [string] (e.g. ["https://example.com"]). If none, [].
   - address: Full street or chamber address string. If not provided, empty "".
   - branch: Branch, chamber, or office location string. If not provided, empty "".
   - city: City or district string. If not provided, empty "".
   - postal_code: Postal/ZIP code string. If not provided, empty "".
   - country: Country string. If not provided, empty "".
   - schedule: Working hours, clinic schedule, or visiting hours string. If not provided, empty "".
   - services: Array of key services or medical specialties [string]. If none, [].
   - social_links: Object with {"linkedin": "", "github": "", "twitter": "", "facebook": "", "instagram": "", "youtube": ""}.
   - monogram: 2-3 letter monogram initials derived from the name or company.
   - style_description: Brief description of the visual design style.

2. ZERO HALLUCINATION:
   - Never invent dummy phone numbers, fake emails, or fake addresses.
   - Every field not mentioned by the user must remain empty string "" or empty array [].

Return ONLY a JSON object:
{
  "name": string,
  "designation": string,
  "department": string,
  "qualifications": [string],
  "company_name": string,
  "tagline": string,
  "address": string,
  "branch": string,
  "city": string,
  "postal_code": string,
  "country": string,
  "schedule": string,
  "phone": [string],
  "email": [string],
  "website": [string],
  "services": [string],
  "social_links": {
    "linkedin": string,
    "github": string,
    "twitter": string,
    "facebook": string,
    "instagram": string,
    "youtube": string
  },
  "monogram": string,
  "style_description": string
}"""


def normalize_card_data(raw_data: dict) -> dict:
    """
    Standardizes all visiting card fields into a comprehensive, predictable JSON structure:
    - String fields: name, designation, department, company_name, tagline,
      address, branch, city, postal_code, country, schedule, monogram
    - Multi-value contact arrays: phone, phones, email, emails, websites,
      qualifications, services, fax
    - Social links: social_links dict (linkedin, github, twitter, facebook, instagram, youtube)
      plus convenient top-level string aliases
    """
    data = dict(raw_data) if isinstance(raw_data, dict) else {}

    def _clean_str(val):
        return str(val or '').strip()

    def _normalize_list(val):
        if isinstance(val, str):
            if not val.strip():
                return []
            return [x.strip() for x in re.split(r'[,;/|\n]+', val) if x.strip()]
        elif isinstance(val, (list, tuple)):
            return [str(x).strip() for x in val if str(x).strip()]
        return []

    # 1. Clean String Fields
    string_keys = [
        'name', 'designation', 'department', 'company_name', 'tagline',
        'address', 'branch', 'city', 'postal_code', 'country',
        'schedule', 'monogram'
    ]
    for k in string_keys:
        data[k] = _clean_str(data.get(k))

    # 2. Multi-value Array Fields
    phones = _normalize_list(data.get('phone') or data.get('phones'))
    data['phone'] = phones
    data['phones'] = phones

    emails = _normalize_list(data.get('email') or data.get('emails'))
    data['email'] = emails
    data['emails'] = emails

    websites = _normalize_list(data.get('websites') or data.get('website'))
    data['websites'] = websites
    data['website'] = websites[0] if websites else _clean_str(data.get('website'))

    data['qualifications'] = _normalize_list(data.get('qualifications'))
    data['services'] = _normalize_list(data.get('services'))
    data['fax'] = _normalize_list(data.get('fax'))

    # 3. Social Profiles
    raw_social = data.get('social_links')
    if not isinstance(raw_social, dict):
        raw_social = {}
    social_dict = {}
    for platform in ['linkedin', 'github', 'twitter', 'facebook', 'instagram', 'youtube']:
        val = _clean_str(raw_social.get(platform) or data.get(platform))
        social_dict[platform] = val
        data[platform] = val
    data['social_links'] = social_dict

    # 4. Monogram computation if missing
    if not data['monogram'] and data['name']:
        parts = data['name'].split()
        if len(parts) >= 2:
            data['monogram'] = (parts[0][0] + parts[1][0]).upper()
        else:
            data['monogram'] = data['name'][:2].upper()

    return data


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
            normalized = normalize_card_data(data)
            logger.info(f"AI Creative Director Design Spec: {normalized}")
            return normalized
    except Exception as e:
        logger.error(f"Creative director reasoning failed: {e}")
        return normalize_card_data({
            'name': user_prompt[:40],
            'monogram': user_prompt[:2].upper(),
            'style_description': 'Modern minimalist visiting card design with clean typography and abstract geometric wave'
        })


LAYOUT_STYLE_DESCRIPTIONS = {
    'organic_waves': (
        "Fluid organic wave ribbons flowing across the card, "
        "sun disc motif, striped circle accent, dark navy background with "
        "warm gold/terracotta accents"
    ),
    'corner_arcs': (
        "Bold concentric rounded arcs hugging the top-right "
        "corner, 45-degree diagonal accent stripes in the bottom-left "
        "corner, dark slate background with vibrant orange accents"
    ),
    'cyber_tech': (
        "Circuit trace grid pattern, glowing neon cyan bracket "
        "outlines, glowing hexagon badge for the monogram, thin tech "
        "divider line, midnight obsidian background with cyan glow"
    ),
    'luxury_gold': (
        "Double hairline gold borders with corner notches, "
        "delicate circular crest emblem, high-fashion serif typography, "
        "matte obsidian black background with champagne gold accents"
    ),
}


def build_precision_dalle_prompt(card_spec: dict) -> str:
    """
    Constructs an airtight DALL-E prompt with:
    1. A strict whitelist of ONLY provided text.
    2. A strict blacklist banning fake/dummy phone numbers, emails, addresses, or icons.
    3. An unequivocal mandate for a flat 2D graphic file with 90-degree square corners (no 3D mockup, no desk/table).
    """
    spec = normalize_card_data(card_spec)

    name = spec['name']
    designation = spec['designation']
    department = spec['department']
    qualifications = spec['qualifications']
    company = spec['company_name']
    tagline = spec['tagline']
    address = spec['address']
    branch = spec['branch']
    city = spec['city']
    postal_code = spec['postal_code']
    country = spec['country']
    schedule = spec['schedule']
    phones = spec['phone']
    emails = spec['email']
    websites = spec['websites']
    services = spec['services']
    social_links = spec['social_links']
    monogram = spec['monogram'] or (name[:2].upper() if name else 'ID')

    layout_style = spec.get('layout_style')
    fallback_style = spec.get('style_description') or 'Sleek modern business card with bold typography and abstract vector accents'
    style = LAYOUT_STYLE_DESCRIPTIONS.get(layout_style, fallback_style)

    # Mandatory Color instruction with early emphasis
    theme = spec.get('theme') or {}
    color_instruction = ""
    if isinstance(theme, dict):
        bg = theme.get('bg_card')
        acc = theme.get('accent')
        acc_sec = theme.get('accent_secondary')
        color_parts = []
        if bg and isinstance(bg, (list, tuple)) and len(bg) >= 3:
            color_parts.append(f"card background MUST be a solid color approximately RGB({bg[0]}, {bg[1]}, {bg[2]})")
        if acc and isinstance(acc, (list, tuple)) and len(acc) >= 3:
            color_parts.append(f"primary accent color RGB({acc[0]}, {acc[1]}, {acc[2]})")
        if acc_sec and isinstance(acc_sec, (list, tuple)) and len(acc_sec) >= 3:
            color_parts.append(f"secondary accent color RGB({acc_sec[0]}, {acc_sec[1]}, {acc_sec[2]})")
        if color_parts:
            color_instruction = (
                f"MANDATORY COLOR PALETTE: {'; '.join(color_parts)} — "
                f"this is strictly required, non-negotiable, and overrides any conflicting color suggestion in the style description. "
            )

    # Critical Phone Number Mandate
    phone_mandate = ""
    if phones:
        if len(phones) == 1:
            phone_mandate = (
                f"CRITICAL PHONE NUMBER MANDATE: render the phone number EXACTLY as '{phones[0]}' "
                f"— character by character, digit by digit, with ZERO changes, additions, or omissions. "
                f"Double-check every single digit matches '{phones[0]}' exactly before finalizing. "
            )
        else:
            joined = ", ".join(f"'{p}'" for p in phones)
            phone_mandate = (
                f"CRITICAL PHONE NUMBER MANDATE: render all phone numbers EXACTLY as {joined} "
                f"— character by character, digit by digit, with ZERO changes, additions, or omissions. "
                f"Double-check every single digit matches exactly before finalizing. "
            )

    # 1. Text Whitelist
    whitelist = [f"Name: '{name}'"]
    if designation:
        whitelist.append(f"Title: '{designation}'")
    if qualifications:
        whitelist.append(f"Qualifications: '{', '.join(qualifications)}'")
    if department:
        whitelist.append(f"Department: '{department}'")
    if company:
        whitelist.append(f"Company: '{company}'")
    if tagline:
        whitelist.append(f"Tagline: '{tagline}'")
    if phones:
        whitelist.append(f"Phone: '{' / '.join(phones)}' (with phone icon)")
    if emails:
        whitelist.append(f"Email: '{' / '.join(emails)}' (with mail icon)")
    if websites:
        whitelist.append(f"Website: '{' / '.join(websites)}' (with globe icon)")

    addr_parts = [p for p in [branch, address, city, postal_code, country] if p]
    full_address = ", ".join(addr_parts) if addr_parts else address
    if full_address:
        whitelist.append(f"Address: '{full_address}' (with location pin icon)")

    if schedule:
        whitelist.append(f"Schedule: '{schedule}' (with clock icon)")
    if services:
        whitelist.append(f"Specialties/Services: '{', '.join(services)}'")

    active_socials = [f"{k.capitalize()}: {v}" for k, v in social_links.items() if v]
    if active_socials:
        whitelist.append(f"Social: '{', '.join(active_socials)}'")

    whitelist_text = ", ".join(whitelist)

    # 2. Strict Blacklist for any absent fields
    blacklist = []
    if not phones:
        blacklist.append("DO NOT render any phone number or phone icon (ABSOLUTELY NO +00, NO +123, NO dummy numbers)")
    if not emails:
        blacklist.append("DO NOT render any email address or mail icon (ABSOLUTELY NO dummy@email.com)")
    if not full_address:
        blacklist.append("DO NOT render any address or location pin icon (ABSOLUTELY NO 123 Anywhere St, NO fake cities)")
    if not designation:
        blacklist.append("DO NOT render any job title or designation below the name")
    if not schedule:
        blacklist.append("DO NOT render any visiting hours or clock icon")
    if not websites:
        blacklist.append("DO NOT render any website URL or globe icon")
    if not qualifications:
        blacklist.append("DO NOT render any unmentioned academic degrees")
    if not tagline:
        blacklist.append("DO NOT render any fake company slogan or tagline")

    blacklist_text = "; ".join(blacklist)

    prompt = (
        f"A full-bleed flat digital graphic layout, exact 1536x1024 rectangular wallpaper canvas. "
        f"{color_instruction}"
        f"{phone_mandate}"
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
    logger.info(f"Generating DALL-E image with final prompt:\n{dalle_prompt}")

    model_configs = [
        ('dall-e-3', '1792x1024'),
        ('dall-e-2', '1024x1024'),
    ]

    for model, size in model_configs:
        try:
            payload = json.dumps({
                'model': model,
                'prompt': dalle_prompt,
                'n': 1,
                'size': size,
                'response_format': 'b64_json'
            }).encode()

            req = urllib.request.Request(
                'https://api.openai.com/v1/images/generations',
                data=payload,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                }
            )

            with urllib.request.urlopen(req, timeout=90) as res:
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
                cropped.save(buf, format="PNG")
                return buf.getvalue()

        return image_bytes
    except Exception as e:
        logger.error(f"Auto-crop error: {e}")
        return image_bytes


DEFAULT_THEMES = {
    'organic_waves': {
        'bg_card': [22, 37, 54],
        'accent': [245, 166, 35],
        'accent_secondary': [217, 83, 47],
        'text_primary': [255, 255, 255],
        'text_secondary': [245, 166, 35],
        'text_muted': [200, 210, 220]
    },
    'corner_arcs': {
        'bg_card': [26, 32, 38],
        'accent': [245, 95, 30],
        'accent_secondary': [210, 70, 20],
        'text_primary': [255, 255, 255],
        'text_secondary': [200, 210, 220],
        'text_muted': [175, 185, 195]
    },
    'cyber_tech': {
        'bg_card': [10, 16, 28],
        'accent': [0, 229, 255],
        'accent_secondary': [56, 189, 248],
        'text_primary': [255, 255, 255],
        'text_secondary': [0, 229, 255],
        'text_muted': [148, 163, 184]
    },
    'luxury_gold': {
        'bg_card': [13, 15, 20],
        'accent': [212, 175, 55],
        'accent_secondary': [245, 215, 127],
        'text_primary': [255, 255, 255],
        'text_secondary': [212, 175, 55],
        'text_muted': [205, 210, 220]
    },
}


def infer_layout_style(prompt: str = '', designation: str = '', company: str = '') -> str:
    """
    Heuristic layout style inference based on prompt, profession/title, or company.
    Guarantees that fallbacks receive a diverse, contextually appropriate style
    rather than always repeating a single default.
    """
    import re
    combined = f"{prompt} {designation} {company}".lower()

    # Tech / Engineering / IT / Data / Web
    tech_patterns = [
        r'tech', r'software', r'developer', r'engineer', r'programmer', r'coder',
        r'it', r'ai', r'data', r'cyber', r'web', r'full[\s_-]?stack', r'backend',
        r'frontend', r'devops', r'cloud', r'system'
    ]
    if re.search(r'\b(?:' + '|'.join(tech_patterns) + r')\b', combined) or any(k in combined for k in ['কম্পিউটার', 'সফটওয়্যার', 'প্রকৌশলী', 'আইটি']):
        return 'cyber_tech'

    # Creative / Design / Art / Media / Photo / Food (checked before generic director)
    creative_patterns = [
        r'design', r'designer', r'artist', r'creative', r'art', r'photo',
        r'photographer', r'video', r'media', r'marketing', r'content', r'writer',
        r'chef', r'food', r'restaurant', r'cafe', r'graphic', r'ui', r'ux'
    ]
    if re.search(r'\b(?:' + '|'.join(creative_patterns) + r')\b', combined) or any(k in combined for k in ['ডিজাইনার', 'ফটোগ্রাফার']):
        return 'organic_waves'

    # Executive / Founder / CEO / Luxury / Finance / Legal / Law / Director
    exec_patterns = [
        r'ceo', r'founder', r'co-founder', r'executive', r'director', r'president',
        r'partner', r'luxury', r'gold', r'vip', r'finance', r'bank', r'invest',
        r'wealth', r'lawyer', r'attorney', r'advocate', r'legal'
    ]
    if re.search(r'\b(?:' + '|'.join(exec_patterns) + r')\b', combined) or any(k in combined for k in ['ব্যবসায়ী', 'আইনজীবী', 'প্রতিষ্ঠাতা']):
        return 'luxury_gold'

    # Corporate / Consultant / Agency / Architecture / Medical / Doctor
    corp_patterns = [
        r'doctor', r'medical', r'clinic', r'hospital', r'health', r'physician',
        r'surgeon', r'dr', r'consultant', r'advisor', r'agency', r'architect',
        r'real[\s_-]?estate', r'manager', r'officer', r'sales', r'corporate'
    ]
    if re.search(r'\b(?:' + '|'.join(corp_patterns) + r')\b', combined) or any(k in combined for k in ['ডাক্তার', 'চিকিৎসক', 'পরামর্শক']):
        return 'corner_arcs'

    # Deterministic fallback based on hash so different prompts produce diverse styles
    styles = ['organic_waves', 'cyber_tech', 'luxury_gold', 'corner_arcs']
    return styles[abs(hash(combined)) % len(styles)]


def generate_hybrid_business_card(prompt: str) -> tuple[bytes, dict]:
    """
    Main entry point for visiting card generation:
    1. GPT-4o-mini extracts exact facts, enforces zero hallucination of missing contacts.
    2. Constructs a bespoke prompt with whitelisted text and strict prohibitions.
    3. OpenAI Image Model generates the flat 2D edge-to-edge card.
    4. Auto-crop cleanly strips any outer border / backdrop while preserving logos.
    """
    from card_project.key_manager import get_active_openai_key
    api_key = get_active_openai_key()

    if not api_key:
        raise ValueError("OpenAI API key not configured — card generation requires an active key.")

    logger.info("Step 0: Creative Director deep reasoning & strict fact extraction...")
    card_spec = analyze_and_design_card(prompt, api_key)

    inferred_style = card_spec.get('layout_style') or infer_layout_style(
        prompt=prompt,
        designation=card_spec.get('designation', ''),
        company=card_spec.get('company_name', '') or card_spec.get('address', '')
    )
    theme = card_spec.get('theme') or DEFAULT_THEMES.get(inferred_style, DEFAULT_THEMES['organic_waves'])
    card_spec['layout_style'] = inferred_style
    card_spec['theme'] = theme

    card_data = normalize_card_data(card_spec)
    card_data['layout_style'] = inferred_style
    card_data['theme'] = theme

    dalle_prompt = card_spec.get('dalle_prompt') or build_precision_dalle_prompt(card_data)

    logger.info("Step 1: Generating bespoke visiting card via OpenAI image model...")
    raw_bytes = generate_dalle_card(dalle_prompt, api_key)

    if not raw_bytes:
        logger.error(f"OpenAI image generation failed for prompt: {prompt}")
        raise RuntimeError("AI card generation failed: OpenAI image generation returned no image.")

    card_bytes = auto_crop_card_surface(raw_bytes)
    logger.info("Step 2: Successfully produced pure visiting card!")
    return card_bytes, card_data


