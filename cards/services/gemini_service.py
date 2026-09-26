import os
import io
import json
import re
import base64
import logging
import requests
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

### ✒️ TYPOGRAPHIC MASTERY & HIERARCHY (PERFECTLY PROPORTIONED FOR 1050x600 CANVAS):
- **Full Name**: Bold, commanding, highly legible and prominent (`font-size: 38px - 44px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.15; color: #FFFFFF on dark / #0F172A on light;`).
- **Job Title**: Refined, prestigious (`font-size: 18px - 21px; font-weight: 500; letter-spacing: 0.5px; color: #d0d7de on dark / #475569 on light; margin-top: 6px; margin-bottom: 12px;`).
- **Accent Hairline Bar**: A 60px - 80px wide, 3px tall bar beneath the title (`background: #FFFFFF on dark / accent_color; margin-top: 6px; margin-bottom: 22px;`).
- **Company Name / Brand Header**: (`font-size: 26px - 32px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; color: #FFFFFF;`).
- **Company Tagline**: (`font-size: 13px - 15px; letter-spacing: 2px; text-transform: uppercase; color: #94A3B8; margin-top: 4px;`).
- **Contact Rows**: Clean vertical stack (`display: flex; align-items: center; gap: 14px; margin-bottom: 14px; font-size: 16px - 18px; font-weight: 500; color: #e6edf3;`).
  - Icons: Crisp vector SVG or icon (`width: 20px; height: 20px; text-align: center; color: accent_color or #ffffff;`).

### 👑 HARMONIOUS COMPANION BACK SIDE:
The back side must share the exact same aesthetic DNA, color scheme, and graphic language as the front:
- Mirror or complement the front's graphic motif (e.g. if the front has twisted ribbons or angular cuts on the left, the back carries a coordinated accent framing the brand presentation).
- Center Brand Presentation:
  - Brand Emblem / Monogram: An iconic vector emblem or monogram badge (`width: 76px; height: 76px; font-size: 32px; font-weight: 900; border-radius: 20px;`).
  - Company Title: Bold uppercase heading (`font-size: 32px - 36px; font-weight: 800; letter-spacing: 4px; text-transform: uppercase; color: #FFFFFF;`).
  - Company Tagline: Refined micro-caps (`font-size: 13px - 15px; letter-spacing: 2.5px; text-transform: uppercase; color: #94A3B8; margin-top: 6px; margin-bottom: 24px;`).
  - Website Pill Badge: Glassmorphic pill (`padding: 10px 28px; border-radius: 25px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); font-size: 15px - 17px; color: accent_color; font-weight: 600;`).

### 📐 RADICAL LAYOUT DIVERSITY & "CHANGE DESIGN" RULES:
When the user asks to "change the design", "change design", "disign change", "different layout", "new design", "design change not color", "ডিজাইন পরিবর্তন করো", "নতুন লেআউট", etc.:
1. NEVER RECYCLE THE SAME LAYOUT STRUCTURE:
   Do NOT simply change colors or tweak a curve and call it a redesign! The user expects a genuine, dramatic structural transformation in layout geometry and spatial composition.
2. DIVERSE LAYOUT ARCHETYPES (CHOOSE A COMPLETELY DIFFERENT ONE ON REDESIGN):
   - **Archetype 1: Swiss Minimalist Architectural Grid**:
     * Clean, crisp whitespace with stark modern hierarchy.
     * Left-aligned typography, razor-sharp hairline dividers, zero curved ribbons. High-end editorial feel.
   - **Archetype 2: Centered Executive Monogram & Symmetrical Horizon**:
     * Centered luxury monogram emblem at the top.
     * Large centered cardholder name and title in the middle.
     * Balanced horizontal two-column contact details aligned along the bottom.
   - **Archetype 3: Vertical Brand Sidebar / Pillar Layout**:
     * Strong contrasting vertical sidebar/pillar on the left (or right) housing the brand logo and company name vertically or stacked.
     * The remaining clean card area dedicated to the cardholder credentials with rich generous margins.
   - **Archetype 4: Sharp Angular / Origami Polygonal Facets**:
     * Bold diagonal cuts using CSS `clip-path: polygon(...)` or sharp 45-degree architectural panels with metallic edges.
   - **Archetype 5: Dual-Tone Split Horizon**:
     * Top half deep tone with brand identity; bottom half contrasting executive tone with contact matrix.
3. "DESIGN CHANGE, NOT COLOR" DIRECTIVE:
   - When the user says "design change not color", "disign change not color", "কালার না, ডিজাইন চেঞ্জ করো", or similar:
   - PRESERVE the exact current color scheme (the user is happy with the colors!).
   - RADICALLY CHANGE the layout structure, geometry, and placement to a totally different archetype!
4. "COLOR CHANGE ONLY" DIRECTIVE:
   - When the user asks ONLY for a color tweak (e.g. "make it navy blue", "লাল ব্যাকগ্রাউন্ড দিন"):
   - Maintain the structural layout while re-engineering the color palette, gradients, and contrast.

### 🧠 CONVERSATION REASONING & INTENT RECOGNITION (PROMPT ENGINEERING):
1. **Dynamic Intent Recognition**:
   - Autonomously understand the user's intent from conversational context and session history:
     * **Aesthetic / Styling Revision**: When the user requests a color change, dark/light theme switch, font adjustment, or layout tweak (e.g. 'change background color red', 'make it midnight black with gold accents', 'লাল ব্যাকগ্রাউন্ড দিন', 'can we make it look more corporate?'):
       - Treat this strictly as a visual design and styling directive.
       - NEVER treat the styling instruction or color name as the person's name, title, or company!
       - Retain all existing cardholder credentials (Name, Title, Company, Phone, Email, etc.) in `card_data` and in the HTML.
       - Dynamically rethink the entire visual composition: canvas background, gradients, SVG geometric artwork, typography contrast, and companion back side.
     * **Layout & Design Overhaul**: When the user asks to change the design or layout ('change the design', 'design change not color', 'নতুন ডিজাইন'):
       - Completely revolutionize the layout geometry, choosing a different archetype from above.
     * **Contact Details Update**: When the user asks to change or provide contact details (e.g. 'my name is ...', 'change phone to ...', 'company: TechCorp'):
       - Update that specific field in `card_data` and on the card. Keep all other fields untouched.
     * **New Card Request**: When the user asks to create a new card from scratch:
       - Autonomously extract the person's real credentials into `card_data` and synthesize a new bespoke brand identity.

2. **Multimodal Reference Image with Redesign Freedom**:
   - If a reference card image is attached:
     * Visually deconstruct and capture its graphic artwork (twisted ribbons, waves, angular cuts, monogram).
     * If the user in the current turn requests a different color or style (e.g. red, gold, minimal), YOUR NEW COLOR PALETTE MUST OVERRIDE the reference image colors! Do not lock into old colors when the user asks for a change.

### 🚨 FORBIDDEN PRACTICES (ZERO TOLERANCE):
1. NO fixed or repetitive templates — design must adapt specifically to the reference or prompt.
2. NO decorative shape or SVG may ever cover, clip, or collide with any text.
3. NO hardcoded placeholder or dummy text ("YOUR NAME", "GRAPHIC DESIGNER", "123 Dummy Street", "Lorem Ipsum").
4. NO low contrast text (e.g. dark text on dark background, or light text on light shapes).
5. STRICTLY NO QR CODES OR BARCODES: Even if the user reference card image contains a QR code, barcode, or scan box, NEVER generate or include any QR code, barcode, QR SVG, or scan frame in the Front HTML, Back HTML, or CSS. Completely omit all QR codes from the design!
6. STRICTLY NO TINY OR COMPACT FONTS: The card canvas is 1050x600 px (high resolution). Tiny fonts (such as 8px - 14px for names/titles, or under 16px for contact details) are completely unreadable and strictly prohibited! You MUST use generous, prominent font sizes:
   - Full Name: 38px - 44px (bold, prominent, commanding)
   - Job Title: 18px - 21px (clear and legible)
   - Company Name: 26px - 32px (bold header)
   - Company Tagline: 13px - 15px
   - Contact Items (Phone, Email, Web, Address): 16px - 18px (with 20px icons)
   - Back Side Brand Name: 32px - 36px, Tagline: 13px - 15px, Website Pill: 15px - 17px

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
    """
    Extracts explicitly labeled contact fields (e.g. 'Name: John', 'Phone: +880...', 'Email: ...')
    without any hardcoded keyword lists or fragile regex guessing.
    All semantic intent recognition and reasoning is delegated to the AI model.
    """
    info = {
        "name": "", "title": "", "company": "", "tagline": "",
        "phone": "", "email": "", "website": "", "address": ""
    }
    if not prompt:
        return info

    phone_match = re.search(r'(\+?\d[\d\s\-\(\)]{8,}\d)', prompt)
    if phone_match:
        info['phone'] = phone_match.group(1).strip()

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
    if email_match:
        info['email'] = email_match.group(0).strip()

    web_match = re.search(r'(?:https?:\/\/)?(?:www\.)?[\w\.-]+\.(?:com|io|net|org|xyz|ai|co|bd|info)', prompt)
    if web_match:
        info['website'] = web_match.group(0).strip()

    # Search for explicit labeled lines only
    for line in prompt.split('\n'):
        line = line.strip()
        lower = line.lower()
        if any(k in lower for k in ['name:', 'নাম:', 'name -']):
            info['name'] = re.sub(r'^(name|নাম)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['title:', 'পদবী:', 'পদবি:', 'role:', 'designation:']):
            info['title'] = re.sub(r'^(title|পদবী|পদবি|role|designation)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['company:', 'কোম্পানি:', 'org:']):
            info['company'] = re.sub(r'^(company|কোম্পানি|org)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['address:', 'ঠিকানা:', 'location:']):
            info['address'] = re.sub(r'^(address|ঠিকানা|location)\s*[:\-]\s*', '', line, flags=re.I).strip()
        elif any(k in lower for k in ['tagline:', 'slogan:']):
            info['tagline'] = re.sub(r'^(tagline|slogan)\s*[:\-]\s*', '', line, flags=re.I).strip()

    return info


def preserve_card_identity(ai_data, previous_card_data):
    """
    Ensures that during iterative design sessions, any existing contact credentials
    (phone, email, website, etc.) that were not explicitly modified remain preserved in card_data.
    All text embedding and visual styling is handled natively by Gemini.
    """
    if not ai_data or not isinstance(ai_data, dict):
        return ai_data

    card_data = ai_data.get('card_data', {})
    if previous_card_data and isinstance(previous_card_data, dict):
        for k, v in previous_card_data.items():
            if v and not card_data.get(k):
                card_data[k] = v

    ai_data['card_data'] = card_data
    return ai_data


def generate_business_card_with_ai(user_prompt, image_path=None, previous_card=None, chat_history=None, session_id=None):
    """
    Main generator supporting Gemini API and OpenAI.
    Supports initial generation and autonomous, creative redesigns without fixed templates.
    Leverages complete session context, conversation history, and reference images.
    """
    ai_config = get_active_ai_config()
    api_key = ai_config.get("api_key")
    provider = ai_config.get("provider", "gemini")

    is_redesign = bool(previous_card and previous_card.get("front_html"))
    active_user_data = {}
    if previous_card and previous_card.get("card_data"):
        active_user_data.update(previous_card.get("card_data"))

    # Extract any explicit labeled fields (e.g. 'Name: John') from prompt if present
    new_extracted = extract_contact_info_from_prompt(user_prompt)
    for k, v in new_extracted.items():
        if v:
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

    # Construct context instructions for Gemini with full Prompt Engineering
    task_instructions = []

    if session_id:
        task_instructions.append(f"SESSION ID: {session_id}")

    if chat_history:
        history_lines = ["RECENT CONVERSATION HISTORY IN THIS STUDIO SESSION:"]
        for msg in chat_history[-6:]:
            role = "User" if msg.get("role") == "user" else "AI Assistant"
            txt = msg.get("content") or msg.get("text") or msg.get("message") or ""
            if txt:
                history_lines.append(f"- {role}: {txt}")
        task_instructions.append("\n".join(history_lines))

    if is_redesign:
        lower_p = user_prompt.lower()
        is_design_redesign = any(w in lower_p for w in [
            'design', 'disign', 'layout', 'style', 'structure', 'ডিজাইন', 'লেআউট', 'স্টাইল', 'গঠন', 'আর্কিটেকচার'
        ])
        is_not_color = any(w in lower_p for w in [
            'not color', 'no color', 'কালার না', 'কালার নয়', 'কালার ছাড়া', 'রং না', 'without color'
        ])

        redesign_blocks = [
            f"🚨 THIS IS A REDESIGN / DESIGN REVISION REQUEST FOR AN EXISTING CARD.\n"
            f"USER REDESIGN INSTRUCTIONS:\n"
            f"\"{user_prompt}\"\n\n"
            f"🚨 AUTONOMOUS DESIGN THINKING DIRECTIVES (STRICTLY NO FIXED TEMPLATES):\n"
        ]

        if is_design_redesign:
            redesign_blocks.append(
                "💥 RADICAL ARCHITECTURAL & LAYOUT METAMORPHOSIS REQUIRED:\n"
                "- The user explicitly commanded: 'CHANGE THE DESIGN' / 'NEW LAYOUT'!\n"
                "- YOU ARE STRICTLY FORBIDDEN from recycling the previous layout, DOM structure, or wave/ribbon shapes!\n"
                "- You MUST craft a RADICALLY DIFFERENT visual archetype from scratch:\n"
                "  * Choice A: Luxury Swiss Minimalist Grid (left-aligned stark hierarchy, elegant thin accent divider, high-impact whitespace, zero waves).\n"
                "  * Choice B: Centered Executive Monogram & Symmetrical Horizon (centered luxury monogram at top, prominent name centered, horizontal contact matrix below).\n"
                "  * Choice C: Vertical Brand Sidebar Pillar (distinct contrasting vertical brand pillar on left/right, spacious credential area).\n"
                "  * Choice D: Sharp Angular / Origami Polygonal Facets (bold diagonal polygon clips, crisp architectural cuts).\n"
            )
            if is_not_color:
                redesign_blocks.append(
                    "🎨 'NOT COLOR' CONSTRAINT: The user explicitly said 'NOT COLOR'!\n"
                    "  * KEEP the existing color palette (primary: " + str(active_user_data.get('primary_color') or '#090d16') + ", accent: " + str(active_user_data.get('accent_color') or '#d4af37') + ").\n"
                    "  * Do NOT change the colors — focus 100% on a COMPLETELY DIFFERENT layout geometry and visual architecture!\n"
                )
        else:
            redesign_blocks.append(
                "1. DYNAMIC COLOR & AESTHETIC TRANSFORMATION:\n"
                f"   - The user's feedback (\"{user_prompt}\") OVERRIDES all previous colors and styles!\n"
                "   - Synthesize a harmonious, rich palette with high-contrast typography and companion back side.\n"
            )

        redesign_blocks.append(
            f"2. USER CONTACT DATA INTEGRITY (PRESERVE ORIGINAL DATA):\n"
            f"   - The instruction \"{user_prompt}\" is a DESIGN COMMAND, NOT A PERSON'S NAME OR TITLE!\n"
            f"   - You MUST keep the cardholder's real details intact:\n"
            f"     * Full Name: {active_user_data.get('name')}\n"
            f"     * Job Title: {active_user_data.get('title') or active_user_data.get('designation')}\n"
            f"     * Company: {active_user_data.get('company') or active_user_data.get('company_name')}\n"
            f"     * Phone: {active_user_data.get('phone')}\n"
            f"     * Email: {active_user_data.get('email')}\n"
            f"     * Website: {active_user_data.get('website')}\n"
            f"     * Address: {active_user_data.get('address')}\n"
        )

        if not is_design_redesign:
            redesign_blocks.append(
                f"3. PREVIOUS HTML & CSS FOR REFERENCE:\n"
                f"   - Previous Front HTML: {previous_card.get('front_html', '')}\n"
                f"   - Previous Back HTML: {previous_card.get('back_html', '')}\n"
                f"   - Previous CSS: {previous_card.get('css', '')}\n"
            )
        else:
            redesign_blocks.append(
                "3. PREVIOUS DESIGN TO DEVIATE FROM:\n"
                "   - The user explicitly wants a fresh new design. Generate brand-new HTML and CSS without imitating the previous layout structure!\n"
            )

        task_instructions.append("\n".join(redesign_blocks))
    else:
        task_instructions.append("THIS IS A NEW BUSINESS CARD REQUEST.")
        task_instructions.append(f"USER PROMPT:\n{user_prompt}")

    # Explicitly require rendering the actual user data
    user_specs = []
    if active_user_data.get('name'):
        user_specs.append(f"- Full Name: {active_user_data['name']}")
    if active_user_data.get('title') or active_user_data.get('designation'):
        user_specs.append(f"- Job Title: {active_user_data.get('title') or active_user_data.get('designation')}")
    if active_user_data.get('company') or active_user_data.get('company_name'):
        user_specs.append(f"- Company: {active_user_data.get('company') or active_user_data.get('company_name')}")
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

    if image_path and not is_redesign:
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
    elif image_path and is_redesign:
        task_instructions.append(
            f"NOTE ON REFERENCE IMAGE: A reference image from earlier is attached for structural layout reference, "
            f"BUT the user's redesign instruction (\"{user_prompt}\") STRICTLY OVERRIDES its color palette and theme! Do NOT stick to the reference image colors."
        )

    full_prompt = "\n\n".join(task_instructions)
    project_id = ai_config.get("project_id", "")

    # 1. Try Google Gemini API
    if provider == "gemini" or api_key.startswith("AIza") or api_key.startswith("AQ."):
        try:
            res = _call_gemini_api(api_key, full_prompt, image_path, project_id=project_id)
            return preserve_card_identity(res, active_user_data)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            res = render_fallback_card(active_user_data)
            res["bot_reply"] = f"Design created (Gemini API notification: {str(e)[:100]})."
            return preserve_card_identity(res, active_user_data)

    # 2. Try OpenAI API
    try:
        res = _call_openai_api(api_key, full_prompt, image_path)
        return preserve_card_identity(res, active_user_data)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        res = render_fallback_card(active_user_data)
        res["bot_reply"] = f"Design created (AI notification: {str(e)[:100]})."
        return preserve_card_identity(res, active_user_data)



def _prepare_image_data(image_path):
    """
    Normalizes any image input (PIL Image, BytesIO, UploadedFile, file path, base64 string)
    into:
    - pil_img: PIL.Image in RGB mode
    - b64_str: base64 string
    - mime_type: e.g. 'image/jpeg'
    """
    if not image_path:
        return None, None, None

    pil_img = None
    try:
        if isinstance(image_path, Image.Image):
            pil_img = image_path
        elif hasattr(image_path, 'read'):
            try:
                image_path.seek(0)
            except Exception:
                pass
            pil_img = Image.open(image_path)
        elif isinstance(image_path, str):
            image_path_str = image_path.strip()
            if image_path_str.startswith('data:image'):
                b64_part = image_path_str.split(',', 1)[1] if ',' in image_path_str else image_path_str
                img_bytes = base64.b64decode(b64_part)
                pil_img = Image.open(io.BytesIO(img_bytes))
            elif os.path.exists(image_path_str):
                pil_img = Image.open(image_path_str)
            elif len(image_path_str) > 100:
                try:
                    img_bytes = base64.b64decode(image_path_str)
                    pil_img = Image.open(io.BytesIO(img_bytes))
                except Exception:
                    pass

        if pil_img:
            pil_img.load()
            if pil_img.mode not in ('RGB', 'L'):
                pil_img = pil_img.convert('RGB')
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG', quality=92)
            b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
            return pil_img, b64_str, 'image/jpeg'
    except Exception as e:
        logger.warning(f"Error preparing image data for vision model: {e}")

    return None, None, None


def _call_gemini_api(api_key, prompt_text, image_path=None, project_id=None):
    """
    Calls Google Gemini using google-genai SDK or direct REST API fallback.
    Supported models: gemini-3.8-flash, gemini-3.5-flash-lite, gemini-3.6-flash, gemini-flash-latest.
    """
    candidate_models = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]
    full_prompt_text = f"{SYSTEM_CARD_PROMPT}\n\nTask:\n{prompt_text}"

    pil_img, b64_img, mime_type = _prepare_image_data(image_path)
    last_error = None

    # 1. Attempt using official google-genai SDK if available
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        sdk_contents = []
        if pil_img:
            sdk_contents.append(pil_img)
        sdk_contents.append(full_prompt_text)

        for model_name in candidate_models:
            try:
                gen_config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=sdk_contents,
                    config=gen_config
                )
                if response and response.text:
                    data = extract_json_from_text(response.text)
                    if data and "front_html" in data:
                        return data
            except Exception as e:
                last_error = e
                logger.warning(f"google.genai SDK model {model_name} failed: {e}. Trying next...")
                continue
    except ImportError:
        pass
    except Exception as e:
        last_error = e
        logger.warning(f"google.genai SDK call failed: {e}. Falling back to REST API...")

    # 2. Direct HTTP REST API via requests (zero SDK dependency, 100% reliable)
    session = requests.Session()

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        parts = []
        if b64_img and mime_type:
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_img
                }
            })
        parts.append({
            "text": full_prompt_text
        })

        payload = {
            "contents": [{
                "role": "user",
                "parts": parts
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        try:
            resp = session.post(url, json=payload, timeout=45)
            if resp.status_code == 200:
                resp_json = resp.json()
                candidates = resp_json.get("candidates", [])
                if candidates:
                    parts_resp = candidates[0].get("content", {}).get("parts", [])
                    if parts_resp and "text" in parts_resp[0]:
                        data = extract_json_from_text(parts_resp[0]["text"])
                        if data and "front_html" in data:
                            return data
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                logger.warning(f"Gemini REST model {model_name} failed with status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Gemini REST model {model_name} error: {e}")

    # 3. Legacy google.generativeai fallback if all above fail
    try:
        import google.generativeai as gai
        gai.configure(api_key=api_key)
        for legacy_model in ["gemini-1.5-flash-latest", "gemini-1.5-pro"]:
            try:
                model = gai.GenerativeModel(legacy_model)
                parts = []
                if pil_img:
                    parts.append(pil_img)
                parts.append(full_prompt_text)
                response = model.generate_content(parts)
                data = extract_json_from_text(response.text)
                if data and "front_html" in data:
                    return data
            except Exception:
                continue
    except Exception:
        pass

    if last_error:
        raise ValueError(f"Gemini API generation failed across all models: {last_error}")
    raise ValueError("Could not extract card design from Gemini response")


def _call_openai_api(api_key, prompt_text, image_path=None):
    """Calls OpenAI API with vision support"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_CARD_PROMPT},
    ]

    user_content = [{"type": "text", "text": prompt_text}]

    pil_img, b64_img, mime_type = _prepare_image_data(image_path)
    if b64_img:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}
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
