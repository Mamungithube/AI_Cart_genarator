import os
import json
import re
import logging
from pathlib import Path
from django.conf import settings
from PIL import Image
from .card_templates import render_fallback_card

logger = logging.getLogger(__name__)

def get_active_ai_config():
    """
    Returns configured API keys and settings from config file or environment
    """
    config_file = getattr(settings, 'AI_CONFIG_FILE', settings.BASE_DIR / 'ai_config.json')
    api_key = ""
    project_id = ""
    provider = "gemini" # default

    if Path(config_file).exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                api_key = data.get('api_key') or data.get('gemini_key') or data.get('openai_key') or ""
                project_id = data.get('project_id') or ""
                provider = data.get('provider') or ("openai" if api_key.startswith("sk-") else "gemini")
        except Exception as e:
            logger.warning(f"Failed to read ai_config.json: {e}")

    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', '')
        if api_key:
            provider = "gemini"
        else:
            api_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', '')
            if api_key:
                provider = "openai"

    return {
        "api_key": api_key.strip(),
        "project_id": project_id.strip(),
        "provider": provider,
    }


def save_ai_config(api_key, provider=None, project_id=None):
    """
    Saves API key to ai_config.json
    """
    config_file = getattr(settings, 'AI_CONFIG_FILE', settings.BASE_DIR / 'ai_config.json')
    if not provider:
        provider = "openai" if api_key.strip().startswith("sk-") else "gemini"

    data = {
        "api_key": api_key.strip(),
        "provider": provider,
    }
    if project_id:
        data["project_id"] = project_id.strip()

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return data



SYSTEM_CARD_PROMPT = """
You are a World-Class Creative Director and Principal Brand Identity Designer for Fortune 500 corporations and luxury design houses.
Your mission is to craft an exceptionally refined, balanced, and prestigious business card (Front & Back) that commands respect and admiration.

### 📐 CARD GEOMETRY & CONTAINER RULES:
- Standard business card aspect ratio: 3.5" x 2" (1.75:1 aspect ratio).
- Base container: `.business-card { width: 100%; height: 100%; aspect-ratio: 1.75 / 1; box-sizing: border-box; border-radius: 12px; overflow: hidden; position: relative; font-family: 'Plus Jakarta Sans', 'Outfit', 'Inter', system-ui, sans-serif; -webkit-font-smoothing: antialiased; }`
- STRICT RESPONSIVE REQUIREMENT: NEVER write fixed pixel dimensions on `.business-card` (e.g. NEVER write `width: 1050px;` or `height: 600px;`). ALWAYS write `width: 100%; height: 100%;` so the card fits seamlessly without being cropped!
- Premium Inset Border: Include `box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08), 0 20px 40px -15px rgba(0, 0, 0, 0.6);` (or subtle dark hairline for light cards) to give a crisp, luxury matte-card feel.

### 🎨 BESPOKE DESIGN ARCHITECTURE — STRICTLY NO FIXED TEMPLATES:
Every business card must be a unique, custom-engineered work of art. NEVER recycle rigid templates or hardcoded shapes.
Your code must dynamically adapt to whatever visual style, geometry, or reference image is provided:

1. **Multimodal Vision Fidelity (When Reference Image is Attached)**:
   - Visually deconstruct the reference image's unique visual geometry:
     * **Intricate Curves / Twisted Ribbons / Flowing Waves**: When the design features organic bezier curves, twisted ribbons, fluid liquid waves, or multi-layered flowing bands, engineer custom inline vector SVG (`<svg viewBox="0 0 1050 600" preserveAspectRatio="none" style="position: absolute; inset: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none;"><path d="..." fill="url(#grad)"/></svg>`) OR layered CSS geometric containers (`border-radius`, `transform: rotate(...) skew(...)`) specifically matching the curves seen in the image.
     * **Sharp Geometric Cuts / Angular Slashes / Origami Facets**: Use CSS `clip-path: polygon(...)` or rotated background panels matching the exact angles and facets of the reference.
     * **Executive Luxury / Swiss Minimalist / Modern Corporate**: Use pristine negative space, elegant typography hierarchy, subtle radial glows, or fine hairline borders.
   - Extract the exact color palette (primary canvas, secondary gradients, accent highlights, and text tones) directly from the reference image.
   - Replicate the exact spatial layout: Place the brand logo, company name, cardholder credentials, and contact rows in the corresponding layout zones seen in the reference.
   - Ignore QR Codes & Barcodes: If the reference card image contains any QR code, barcode, or scan box, IGNORE IT COMPLETELY. Do NOT replicate or render any QR codes or barcodes on the business card. Keep that area clean with elegant negative space or a luxury monogram emblem instead.

2. **Autonomous Design Synthesis (When No Image is Provided)**:
   - Dynamically craft a brand-new, bespoke visual identity inspired by the user's prompt, industry, company name, and aesthetic mood:
     * Tech / Software / AI: Midnight dark theme with electric cyan/emerald accents and clean modern vectors.
     * Executive / Finance / Luxury: Deep obsidian or royal charcoal paired with brushed champagne gold (#D4AF37) or warm bronze.
     * Creative / Architecture / Fashion: Bold Swiss typography, minimalist contrast, architectural grid balance.
     * Medical / Healthcare / Science: Crisp alabaster white with clinical teal/cyan accents.
     * Startups / Marketing / Media: Dynamic gradient mesh and modern glassmorphism.

3. **Structural Layer Separation (Zero Text Clipping Guarantee)**:
   - **Background Artwork Layer (`z-index: 1`)**: All decorative artwork, twisted ribbons, waves, geometric shapes, and SVGs MUST reside in a background layer with `position: absolute; inset: 0; z-index: 1; pointer-events: none; overflow: hidden;`.
   - **Foreground Content Layer (`z-index: 5`)**: The brand logo/company section and the cardholder identity section MUST reside in clean foreground containers with `position: relative; z-index: 5;`.
   - **Breathing Room**: Ensure all text has comfortable padding and margins. No decorative artwork may ever collide with, overlap, or clip any text.

### ✒️ TYPOGRAPHIC MASTERY & HIERARCHY:
- **Full Name**: Bold, crisp, commanding (`font-size: 24px - 28px; font-weight: 700; letter-spacing: -0.4px; line-height: 1.15; color: #FFFFFF on dark / #0F172A on light;`).
- **Job Title**: Refined, readable (`font-size: 13px - 14.5px; font-weight: 400; color: #d0d7de on dark / #64748B on light; margin-top: 4px; margin-bottom: 8px;`).
- **Accent Hairline Bar**: A 50px - 60px wide, 2px tall bar beneath the title (`background: #FFFFFF on dark / accent_color; margin-top: 6px; margin-bottom: 18px;`).
- **Contact Rows**: Clean vertical stack (`display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 12.5px; font-weight: 500; color: #e6edf3;`).
  - Icons: Crisp vector SVG or Font Awesome icon (`width: 16px; text-align: center; color: accent_color or #ffffff;`).

### 👑 HARMONIOUS COMPANION BACK SIDE:
The back side must share the exact same aesthetic DNA, color scheme, and graphic language as the front:
- Mirror or complement the front's graphic motif (e.g. if the front has twisted ribbons or angular cuts on the left, the back carries a coordinated accent framing the brand presentation).
- Center Brand Presentation:
  - Brand Emblem / Monogram: An iconic vector emblem or monogram badge.
  - Company Title: Bold uppercase heading (`font-size: 20px - 22px; font-weight: 800; letter-spacing: 3.5px; text-transform: uppercase; color: #FFFFFF;`).
  - Company Tagline: Refined micro-caps (`font-size: 9px - 10px; letter-spacing: 2px; text-transform: uppercase; color: #94A3B8; margin-top: 4px; margin-bottom: 16px;`).
  - Website Pill Badge: Glassmorphic pill (`padding: 6px 18px; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); font-size: 10px; color: accent_color; font-weight: 600;`).

### 🚨 FORBIDDEN PRACTICES (ZERO TOLERANCE):
1. NO fixed or repetitive templates — design must adapt specifically to the reference or prompt.
2. NO decorative shape or SVG may ever cover, clip, or collide with any text.
3. NO hardcoded placeholder or dummy text ("YOUR NAME", "GRAPHIC DESIGNER", "123 Dummy Street", "Lorem Ipsum").
4. NO low contrast text (e.g. dark text on dark background, or light text on light shapes).
5. STRICTLY NO QR CODES OR BARCODES: Even if the user reference card image contains a QR code, barcode, or scan box, NEVER generate or include any QR code, barcode, QR SVG, or scan frame in the Front HTML, Back HTML, or CSS. Completely omit all QR codes from the design!

### OUTPUT FORMAT:
You MUST output ONLY valid JSON matching this schema:
{
  "bot_reply": "Executive design rationale explaining the visual thinking, geometric structure, typography pairing, and color harmony",
  "title": "Person Name - Company Card",
  "card_data": {
    "name": "Full Name",
    "title": "Job Title",
    "company": "Company Name",
    "tagline": "Company Tagline",
    "phone": "+880 1xxx",
    "email": "email@example.com",
    "website": "www.example.com",
    "address": "City, Country",
    "primary_color": "#hex",
    "accent_color": "#hex"
  },
  "front_html": "<div class=\\"business-card front ...\\">...</div>",
  "back_html": "<div class=\\"business-card back ...\\">...</div>",
  "css": ".business-card { ... } .business-card.front { ... } .business-card.back { ... }"
}
"""




def extract_json_from_text(text):
    """Safely extracts JSON object from response text"""
    try:
        # Check for ```json ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            return json.loads(match.group(1))
        
        # Check for first { to last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
            
        return json.loads(text)
    except Exception as e:
        logger.error(f"JSON parsing error: {e}, text sample: {text[:200]}")
        return None


def extract_contact_info_from_prompt(prompt):
    """Accurately extracts contact info from prompt without ANY hardcoded dummy names"""
    name = ""
    title = ""
    company = ""
    tagline = ""
    phone = ""
    email = ""
    website = ""
    address = ""

    # Search for phone
    phone_match = re.search(r'(\+?\d[\d\s\-\(\)]{8,}\d)', prompt)
    if phone_match:
        phone = phone_match.group(1).strip()

    # Search for email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
    if email_match:
        email = email_match.group(0).strip()

    # Search for website
    web_match = re.search(r'(?:https?:\/\/)?(?:www\.)?[\w\.-]+\.(?:com|io|net|org|xyz|ai|co|bd|info)', prompt)
    if web_match:
        website = web_match.group(0).strip()

    # Check lines
    raw_lines = [l.strip() for l in prompt.split('\n') if l.strip()]
    candidate_lines = []

    for line in raw_lines:
        lower = line.lower()
        if any(k in lower for k in ['name:', 'নাম:', 'name -']):
            name = re.sub(r'^(name|নাম)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['title:', 'পদবী:', 'পদবি:', 'role:', 'designation:']):
            title = re.sub(r'^(title|পদবী|পদবি|role|designation)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['company:', 'কোম্পানি:', 'org:']):
            company = re.sub(r'^(company|কোম্পানি|org)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['address:', 'ঠিকানা:', 'location:']):
            address = re.sub(r'^(address|ঠিকানা|location)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['tagline:', 'slogan:']):
            tagline = re.sub(r'^(tagline|slogan)\s*[:\-]\s*', '', line, flags=re.I).strip()
        else:
            # Check if this line is NOT a phone, email, website, or meta prompt instruction
            if not re.search(r'[\w\.-]+@[\w\.-]+', line) and \
               not re.search(r'\+?\d{7,}', line) and \
               not any(kw in lower for kw in ['create', 'business card', 'visiting card', 'minimal', 'modern', 'design', 'layout', 'for:', 'white text', 'blue accent', 'style']):
                candidate_lines.append(line)

    # If name/title/company weren't explicitly labeled, infer from candidate lines
    if not name and candidate_lines:
        name = candidate_lines[0]
        if len(candidate_lines) > 1 and not title:
            title = candidate_lines[1]
        if len(candidate_lines) > 2 and not company:
            company = candidate_lines[2]

    # Check for sentence pattern: "for [Name], [Title] at [Company]"
    inline_match = re.search(r'for\s+([A-Za-z\.\s]+?),\s*([A-Za-z\s]+?)\s+at\s+([^,]+)', prompt, re.I)
    if inline_match:
        if not name:
            name = inline_match.group(1).strip()
        if not title:
            title = inline_match.group(2).strip()
        if not company:
            company = inline_match.group(3).strip()

    return {
        "name": name,
        "title": title,
        "company": company,
        "tagline": tagline,
        "phone": phone,
        "email": email,
        "website": website,
        "address": address
    }


def is_new_card_intent(prompt):
    """Detects if prompt is an explicit instruction to create a new card from scratch"""
    if not prompt:
        return False
    lower = prompt.lower().strip()
    lower = re.sub(r'^["\']|["\']$', '', lower)
    patterns = [
        r'\b(make|create|design|generate)\s+(a\s+)?(new\s+)?(visiting|business)?\s*card\b',
        r'\b(card\s+for|visiting\s+card\s+for|business\s+card\s+for)\b',
        r'\b(নতুন\s+কার্ড|কার্ড\s+বানাও|ভিজিটিং\s+কার্ড\s+বানাও)\b',
    ]
    return any(re.search(pat, lower) for pat in patterns)




def sanitize_and_preserve_user_data(ai_data, active_user_data):
    """
    Ensures placeholder text from reference images ('YOUR NAME', 'GRAPHIC DESIGNER',
    '123 Dummy', 'your email space', etc.) NEVER replaces real user data.
    """
    if not ai_data or not active_user_data:
        return ai_data

    card_data = ai_data.get('card_data', {})
    dummy_names = ['YOUR NAME', 'NAME HERE', 'JOHN DOE', 'JANE DOE', 'SAMPLE NAME', 'YOURNAME']
    dummy_titles = ['GRAPHIC DESIGNER', 'YOUR TITLE', 'DESIGNATION', 'CREATIVE DESIGNER', 'TITLE HERE']
    dummy_companies = ['COMPANY NAME', 'YOUR COMPANY', 'BRAND NAME', 'TAGLINE HERE']

    user_name = active_user_data.get('name')
    user_title = active_user_data.get('title')
    user_company = active_user_data.get('company')
    user_phone = active_user_data.get('phone')
    user_email = active_user_data.get('email')
    user_website = active_user_data.get('website')
    user_address = active_user_data.get('address')

    # Guard card_data dict
    if user_name and (not card_data.get('name') or any(d in str(card_data.get('name', '')).upper() for d in dummy_names)):
        card_data['name'] = user_name
    if user_title and (not card_data.get('title') or any(d in str(card_data.get('title', '')).upper() for d in dummy_titles)):
        card_data['title'] = user_title
    if user_company and (not card_data.get('company') or any(d in str(card_data.get('company', '')).upper() for d in dummy_companies)):
        card_data['company'] = user_company
    if user_phone and (not card_data.get('phone') or '1234 5xxx' in str(card_data.get('phone', '')).lower() or 'dummy' in str(card_data.get('phone', '')).lower()):
        card_data['phone'] = user_phone
    if user_email and (not card_data.get('email') or 'your email' in str(card_data.get('email', '')).lower() or 'email@' in str(card_data.get('email', '')).lower()):
        card_data['email'] = user_email
    if user_website and (not card_data.get('website') or 'website address' in str(card_data.get('website', '')).lower()):
        card_data['website'] = user_website
    if user_address and (not card_data.get('address') or 'dummy' in str(card_data.get('address', '')).lower() or 'lorem' in str(card_data.get('address', '')).lower()):
        card_data['address'] = user_address

    ai_data['card_data'] = card_data

    # Sanitize HTML
    front_html = ai_data.get('front_html', '')
    back_html = ai_data.get('back_html', '')

    replacements = []
    if user_name:
        replacements.extend([
            ('YOUR NAME', user_name),
            ('Your Name', user_name),
            ('your name', user_name),
            ('John Doe', user_name),
        ])
    if user_title:
        replacements.extend([
            ('GRAPHIC DESIGNER', user_title),
            ('Graphic Designer', user_title),
            ('graphic designer', user_title),
            ('CREATIVE DESIGNER', user_title),
            ('Creative Designer', user_title),
        ])
    if user_company:
        replacements.extend([
            ('COMPANY NAME', user_company),
            ('Company Name', user_company),
            ('YOUR COMPANY', user_company),
        ])
    if user_phone:
        replacements.extend([
            ('+00 1234 5XXX 9012', user_phone),
            ('+00 1234 5xxx 9012', user_phone),
            ('+00 1234 5678 9012', user_phone),
            ('+1 234 567 890', user_phone),
        ])
    if user_email:
        replacements.extend([
            ('your email space', user_email),
            ('youremail@email.com', user_email),
            ('name@example.com', user_email),
            ('email@example.com', user_email),
        ])
    if user_website:
        replacements.extend([
            ('website address here', user_website),
            ('www.website.com', user_website),
            ('www.example.com', user_website),
        ])
    if user_address:
        replacements.extend([
            ('123 Dummy, Lorem Ipsum', user_address),
            ('123 Dummy, Lorem', user_address),
            ('123 Street Name, City', user_address),
            ('City, Country', user_address),
        ])

    for target, rep in replacements:
        if target in front_html:
            front_html = front_html.replace(target, rep)
        if target in back_html:
            back_html = back_html.replace(target, rep)

    # Strip any accidental QR code or barcode elements
    for qr_pattern in [
        r'''<div[^>]*class=["'][^"']*(?:qr|barcode|scan-code|scan_code)[^"']*["'][^>]*>[\s\S]*?</div>''',
        r'''<div[^>]*id=["'][^"']*(?:qr|barcode|scan-code|scan_code)[^"']*["'][^>]*>[\s\S]*?</div>''',
        r'''<svg[^>]*class=["'][^"']*(?:qr|barcode)[^"']*["'][^>]*>[\s\S]*?</svg>''',
    ]:
        front_html = re.sub(qr_pattern, '', front_html, flags=re.IGNORECASE)
        back_html = re.sub(qr_pattern, '', back_html, flags=re.IGNORECASE)

    ai_data['front_html'] = front_html
    ai_data['back_html'] = back_html
    return ai_data


def generate_business_card_with_ai(user_prompt, image_path=None, previous_card=None, chat_history=None):
    """
    Main generator supporting Gemini API and OpenAI.
    Supports initial generation and iterative redesigns while strictly preserving user details.
    """
    ai_config = get_active_ai_config()
    api_key = ai_config.get("api_key")
    provider = ai_config.get("provider", "gemini")

    # Check if user explicitly asked to create/make a new card
    if is_new_card_intent(user_prompt):
        previous_card = None
        active_user_data = {}
    else:
        # Track and accumulate active user contact data across redesign iterations
        active_user_data = {}
        if previous_card and previous_card.get("card_data"):
            active_user_data.update(previous_card.get("card_data"))

    # Extract any contact details from the prompt and merge/override
    new_extracted = extract_contact_info_from_prompt(user_prompt)
    for k, v in new_extracted.items():
        if v:
            # Overwrite with newly detected name/title/company/etc. from prompt
            active_user_data[k] = v


    # Fallback if no API key
    if not api_key:
        logger.info("No AI API key found. Using fallback card generator.")
        res = render_fallback_card(active_user_data)
        res["bot_reply"] = (
            "I've generated a corporate card template for you. "
            "(To use full Gemini multimodal AI with image reference analysis, please enter your Gemini API Key in the top settings modal)."
        )
        return res

    # Construct context instructions for Gemini
    task_instructions = []
    if previous_card and previous_card.get("front_html"):
        task_instructions.append(
            "THIS IS A REDESIGN REQUEST FOR AN EXISTING CARD. The user wants you to modify/refine the design based on their feedback."
        )
        task_instructions.append(f"PREVIOUS FRONT HTML:\n{previous_card.get('front_html', '')}")
        task_instructions.append(f"PREVIOUS BACK HTML:\n{previous_card.get('back_html', '')}")
        task_instructions.append(f"PREVIOUS CSS:\n{previous_card.get('css', '')}")
        task_instructions.append(f"USER FEEDBACK / REDESIGN INSTRUCTIONS:\n{user_prompt}")
    else:
        task_instructions.append("THIS IS A NEW BUSINESS CARD REQUEST.")
        task_instructions.append(f"USER PROMPT:\n{user_prompt}")

    # Explicitly require rendering the actual user data
    user_specs = []
    if active_user_data.get('name'):
        user_specs.append(f"- Full Name: {active_user_data['name']}")
    if active_user_data.get('title'):
        user_specs.append(f"- Job Title: {active_user_data['title']}")
    if active_user_data.get('company'):
        user_specs.append(f"- Company: {active_user_data['company']}")
    if active_user_data.get('phone'):
        user_specs.append(f"- Mobile / Phone: {active_user_data['phone']}")
    if active_user_data.get('email'):
        user_specs.append(f"- Email: {active_user_data['email']}")
    if active_user_data.get('website'):
        user_specs.append(f"- Website: {active_user_data['website']}")
    if active_user_data.get('address'):
        user_specs.append(f"- Address: {active_user_data['address']}")

    if user_specs:
        task_instructions.append(
            "🚨 MANDATORY USER CONTACT DATA TO RENDER IN THE DESIGN (USE ONLY THESE DETAILS, DO NOT INVENT NAMES):\n" + "\n".join(user_specs)
        )
    else:
        task_instructions.append(
            "CRITICAL: Carefully parse and extract the person's exact Name, Job Title, Company Name, and Contact details directly from the user's prompt text above. DO NOT use placeholder names."
        )


    if image_path:
        task_instructions.append(
            "CRITICAL: A REFERENCE BUSINESS CARD IMAGE HAS BEEN ATTACHED.\n"
            "🚨 VISION-DRIVEN BESPOKE REPLICATION (STRICTLY NO FIXED TEMPLATES):\n"
            "1. DECONSTRUCT & REPRODUCE THE EXACT ARTWORK OF THE ATTACHED IMAGE:\n"
            "   - Visually analyze the reference image in high fidelity:\n"
            "     * Geometry & Artwork: If it has intricate twisted ribbons, flowing bezier waves, curved arcs, diagonal geometric slashes, isometric blocks, or minimalist whitespace, code custom CSS and/or inline vector SVG (<svg viewBox=\"0 0 1050 600\"><path d=\"...\" fill=\"url(#grad)\"/></svg>) specifically tailored to capture that exact visual effect. NEVER force a generic or pre-existing template!\n"
            "     * Exact Color Palette: Extract the exact hex codes, linear/radial gradients, and drop shadows directly from the reference image.\n"
            "     * Spatial Layout: Position the company branding and cardholder contact details in the exact relative zones where they appear in the reference image.\n"
            "2. LAYER SEPARATION (ZERO TEXT CLIPPING GUARANTEE):\n"
            "   - All decorative shapes, twisted ribbons, and background SVGs MUST be inside a background container with `position: absolute; inset: 0; z-index: 1; pointer-events: none; overflow: hidden;`.\n"
            "   - All text and contact elements MUST be inside foreground containers with `position: relative; z-index: 5;`.\n"
            "   - Ensure text has clean contrast and generous padding so no background artwork ever covers or clips any letters.\n"
            "3. MATCHING BACK-SIDE CREATION:\n"
            "   - Generate a companion back side that echoes the exact visual motif, palette, and design language of the front side.\n"
            "4. RENDER REAL USER DATA (NO DUMMY TEXT):\n"
            f"   - Full Name: {active_user_data.get('name')}\n"
            f"   - Job Title: {active_user_data.get('title')}\n"
            f"   - Company: {active_user_data.get('company')}\n"
            f"   - Phone: {active_user_data.get('phone')}\n"
            f"   - Email: {active_user_data.get('email')}\n"
            f"   - Website: {active_user_data.get('website')}\n"
            f"   - Address: {active_user_data.get('address')}"
            "\n5. STRICTLY NO QR CODES: If the reference card image contains a QR code, barcode, or scan box, IGNORE IT COMPLETELY. Do NOT include any QR code, scan box, or barcode on the card."
        )


    full_prompt = "\n\n".join(task_instructions)
    project_id = ai_config.get("project_id", "")

    # 1. Try Google Gemini API
    if provider == "gemini" or api_key.startswith("AIza") or api_key.startswith("AQ."):
        try:
            res = _call_gemini_api(api_key, full_prompt, image_path, project_id=project_id)
            return sanitize_and_preserve_user_data(res, active_user_data)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            res = render_fallback_card(active_user_data)
            res["bot_reply"] = f"Design created (Gemini API notification: {str(e)[:100]})."
            return sanitize_and_preserve_user_data(res, active_user_data)

    # 2. Try OpenAI API
    try:
        res = _call_openai_api(api_key, full_prompt, image_path)
        return sanitize_and_preserve_user_data(res, active_user_data)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        res = render_fallback_card(active_user_data)
        res["bot_reply"] = f"Design created (AI notification: {str(e)[:100]})."
        return sanitize_and_preserve_user_data(res, active_user_data)



def _call_gemini_api(api_key, prompt_text, image_path=None, project_id=None):
    """Calls Google Gemini using google-genai or google.generativeai"""
    try:
        from google import genai
        from google.genai import types
        
        # Google AI Studio API key does not take project/location
        client = genai.Client(api_key=api_key)
        contents = []

        if image_path:
            if isinstance(image_path, Image.Image):
                contents.append(image_path)
            elif isinstance(image_path, str) and os.path.exists(image_path):
                img = Image.open(image_path)
                contents.append(img)
            
        contents.append(f"{SYSTEM_CARD_PROMPT}\n\nTask:\n{prompt_text}")

        # Models to try in order of availability and quota
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
        last_error = None

        for model_name in candidate_models:
            try:
                # Enable thinking budget so Gemini visually reasons through layout before coding CSS
                gen_config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=2048)
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config
                )
                data = extract_json_from_text(response.text)
                if data and "front_html" in data:
                    return data
            except Exception as e:
                # If thinking_config fails on a model, retry without it
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = extract_json_from_text(response.text)
                    if data and "front_html" in data:
                        return data
                except Exception as inner_e:
                    last_error = inner_e
                    logger.warning(f"Model {model_name} failed: {inner_e}. Trying next model...")
                    continue


        if last_error:
            raise last_error
        raise ValueError("Could not extract card data from Gemini response")

    except ImportError:
        # Fallback to google.generativeai legacy package
        import google.generativeai as gai
        gai.configure(api_key=api_key)
        model = gai.GenerativeModel('gemini-1.5-flash')
        parts = []
        if image_path and os.path.exists(image_path):
            parts.append(Image.open(image_path))
        parts.append(f"{SYSTEM_CARD_PROMPT}\n\nTask:\n{prompt_text}")
        response = model.generate_content(parts)
        data = extract_json_from_text(response.text)
        if data and "front_html" in data:
            return data
        raise ValueError("Invalid JSON from Gemini legacy")


def _call_openai_api(api_key, prompt_text, image_path=None):
    """Calls OpenAI API with vision support"""
    import base64
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_CARD_PROMPT},
    ]

    user_content = [{"type": "text", "text": prompt_text}]

    if image_path:
        if isinstance(image_path, Image.Image):
            import io
            buf = io.BytesIO()
            image_path.save(buf, format='PNG')
            encoded_string = base64.b64encode(buf.getvalue()).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_string}"}
            })
        elif isinstance(image_path, str) and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                mime = "image/jpeg"
                if image_path.lower().endswith('.png'):
                    mime = "image/png"
                elif image_path.lower().endswith('.webp'):
                    mime = "image/webp"
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded_string}"}
                })

    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"}
    )
    data = extract_json_from_text(response.choices[0].message.content)
    if data and "front_html" in data:
        return data
    raise ValueError("Invalid JSON received from OpenAI")
