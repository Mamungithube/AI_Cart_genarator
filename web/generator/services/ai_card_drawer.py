import io
import os
import json
import base64
import logging
import urllib.request
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

SYSTEM_MSG = """You are an elite Senior Graphic Designer & Art Director specializing in world-class, award-winning corporate and professional visiting cards (like Behance, Dribbble, and GraphicRiver top sellers).

Analyze the user's prompt with deep creative intelligence. You must strictly understand and support the complete anatomy of a visiting card:

1. ESSENTIAL INFORMATION:
   - Name: Full name (prominent, bold, modern typography).
   - Designation / Title: (e.g., CEO, Manager, Developer, Consultant).
     * If the user provided a designation: Render it cleanly directly under the name (e.g. 'MANAGING DIRECTOR' or 'LEAD AI ENGINEER').
     * If the user did NOT explicitly provide a designation: Keep it completely EMPTY ("") and do NOT draw any title or subtitle! ABSOLUTELY DO NOT guess or invent titles like 'Medical Practitioner', 'Doctor', 'Specialist', 'Executive', or 'Engineer'!
   - Company Name: Company, Clinic, Hospital, Firm, or Lab name.
   - Phone Number: Mobile/Phone number(s). ONLY if explicitly provided.

2. CONTACT INFORMATION:
   - Email Address: e.g. alex@neuralcraft.ai. ONLY if provided.
   - Address: Office, Chamber, Clinic, or Business address (e.g. 'Aqua Tower, Mohakhali, Dhaka'). Extract the FULL address and explicitly instruct DALL-E to render it with a location pin icon (📍).
   - Website URL: e.g. www.company.com. ONLY if provided.

3. SOCIAL / PROFESSIONAL LINKS:
   - LinkedIn / GitHub / Twitter / Facebook / Social handles. Render with clean minimalist icons. ONLY if provided.

4. ADDITIONAL / OPTIONAL INFORMATION:
   - Working Hours / Visiting Schedule: (especially for clinics, doctors, salons, service businesses, e.g. 'Visiting Hours: Sunday to Thursday 09:00 AM to 06:00 PM'). Explicitly instruct DALL-E to render the full schedule with a clock icon (🕒).
   - Tagline or Slogan / Degrees: (e.g., 'MBBS, FCPS', 'Empowering AI Innovation'). Place elegantly.
   - Company Logo / Monogram: A stunning vector monogram emblem derived from person's name or company initials (e.g., 'HP', 'AR', 'RI') inside a stylish crest/hexagon badge with glowing neon/metallic accents.
   - QR Code: If requested or appropriate for tech cards, include a sleek minimalist digital QR code square.
   - Fax Number: Only if provided.

5. DYNAMIC ASYMMETRIC GRAPHIC LAYOUT (AWARD-WINNING STYLE):
   - One zone (left): Name, and neatly aligned contact/address/schedule rows with minimalist clean icons.
   - Opposite zone (right): Flowing organic curved wave or sharp geometric color block holding the glowing vector monogram emblem badge and company/clinic branding.
   - Professional color harmony suited for the profession (e.g. healthcare/doctor: clean white/pearl base with fresh mint/cyan/emerald green accent wave; tech: dark matte slate with glowing electric cyan blue).

6. 100% FULL-BLEED VISITING CARD:
   - Standard horizontal landscape (1536x1024).
   - The visiting card fills 100% of the canvas edge-to-edge.
   - ABSOLUTELY NO desk, NO table, NO outer border, NO frame, NO studio mockup backdrop. The canvas IS the card surface.

Return ONLY a JSON object:
{
  "name": string,
  "designation": string (MUST be empty "" if not explicitly stated in prompt),
  "company_name": string,
  "address": string,
  "schedule": string,
  "phone": string,
  "email": string,
  "website": string,
  "social_media": string,
  "tagline_or_degrees": string,
  "dalle_prompt": string
}"""


def analyze_and_design_card(user_prompt: str, api_key: str) -> dict:
    """Uses GPT-4o-mini as a Creative Director to extract exact facts and craft the DALL-E prompt."""
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
            'linkedin': '',
            'dalle_prompt': (
                f"Full-bleed visiting card graphic design for {user_prompt[:40]}. "
                "The visiting card fills 100% of the entire 1536x1024 rectangular canvas edge-to-edge with zero margins, "
                "zero table, and zero outer background. Elegant typography and refined branding."
            )
        }


def generate_dalle_card(dalle_prompt: str, api_key: str) -> bytes | None:
    """Calls OpenAI image generation model with the tailor-made creative prompt."""
    logger.info(f"Generating DALL-E image with prompt: {dalle_prompt}")

    for model in ['gpt-image-1', 'chatgpt-image-latest', 'gpt-image-1.5']:
        try:
            payload = json.dumps({
                'model': model,
                'prompt': dalle_prompt,
                'n': 1,
                'size': '1536x1024'
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
            logger.error(f"OpenAI error model={model}: {e.code} {e.read().decode(errors='ignore')}")
            continue
        except Exception as e:
            logger.error(f"OpenAI exception model={model}: {e}")
            continue
    return None


def auto_crop_card_surface(image_bytes: bytes) -> bytes:
    """
    Detects if DALL-E generated a card sitting on a background / mockup desk / table,
    and accurately crops to the card's 4 outer boundaries so that 100% of the
    returned image is ONLY the visiting card surface with zero outer borders.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        gray = img.convert("L")

        # 1. Left boundary (scan x from 2% to 22% of w)
        best_left = 0
        max_cnt_left = 0
        for x in range(int(w * 0.02), int(w * 0.22), 2):
            cnt = sum(1 for y in range(int(h * 0.25), int(h * 0.75), 2)
                      if abs(gray.getpixel((x + 2, y)) - gray.getpixel((x - 2, y))) > 12)
            if cnt > max_cnt_left and cnt > (h * 0.10):
                max_cnt_left = cnt
                best_left = x

        # 2. Right boundary (scan x from 98% down to 78% of w)
        best_right = w
        max_cnt_right = 0
        for x in range(int(w * 0.98), int(w * 0.78), -2):
            cnt = sum(1 for y in range(int(h * 0.25), int(h * 0.75), 2)
                      if abs(gray.getpixel((x - 2, y)) - gray.getpixel((x + 2, y))) > 12)
            if cnt > max_cnt_right and cnt > (h * 0.10):
                max_cnt_right = cnt
                best_right = x

        # 3. Top boundary (scan y from 2% to 26% of h)
        best_top = 0
        max_cnt_top = 0
        for y in range(int(h * 0.02), int(h * 0.26), 2):
            cnt = sum(1 for x in range(int(w * 0.25), int(w * 0.75), 2)
                      if abs(gray.getpixel((x, y + 2)) - gray.getpixel((x, y - 2))) > 12)
            if cnt > max_cnt_top and cnt > (w * 0.08):
                max_cnt_top = cnt
                best_top = y

        # 4. Bottom boundary (scan y from 98% down to 74% of h)
        best_bottom = h
        max_cnt_bottom = 0
        for y in range(int(h * 0.98), int(h * 0.74), -2):
            cnt = sum(1 for x in range(int(w * 0.25), int(w * 0.75), 2)
                      if abs(gray.getpixel((x, y - 2)) - gray.getpixel((x, y + 2))) > 12)
            if cnt > max_cnt_bottom and cnt > (w * 0.08):
                max_cnt_bottom = cnt
                best_bottom = y

        # Apply a 3px inset inside the detected card boundary to ensure ZERO border remnant
        c_left = best_left + 3 if best_left > 15 else 0
        c_top = best_top + 3 if best_top > 15 else 0
        c_right = best_right - 3 if best_right < (w - 15) else w
        c_bottom = best_bottom - 3 if best_bottom < (h - 15) else h

        # Validate that cropped area is realistic (at least 60% of canvas)
        if (c_right - c_left) > int(w * 0.6) and (c_bottom - c_top) > int(h * 0.5):
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
    1. GPT-4o-mini analyzes prompt, strictly avoids predicting missing titles,
       extracts full address, schedule, contacts, and crafts a bespoke DALL-E prompt.
    2. OpenAI Image Model (gpt-image-1) generates the visiting card with stunning AI aesthetics.
    3. Auto-crop cleans any outer backdrop, guaranteeing 100% pure visiting card.
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

    dalle_prompt = card_spec.get('dalle_prompt') or (
        f"Full-bleed visiting card design for {card_data['name']}. "
        "Fills 100% of the 1536x1024 canvas edge-to-edge. Zero outer background, zero table."
    )

    logger.info("Step 1: Generating full-bleed card via OpenAI image model...")
    card_bytes = generate_dalle_card(dalle_prompt, api_key)

    if card_bytes:
        card_bytes = auto_crop_card_surface(card_bytes)
        logger.info("Step 2: Successfully produced pure visiting card!")
        return card_bytes, card_data
    else:
        logger.warning("OpenAI image generation failed. Falling back to Pillow.")
        from .card_drawer import generate_business_card
        return generate_business_card(card_data), card_data
