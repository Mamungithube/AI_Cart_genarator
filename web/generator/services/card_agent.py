import os
import io
import re
import json
import time
import base64
import logging
import urllib.request
import urllib.error
from pathlib import Path
from django.conf import settings
from card_project.notifications import send_openai_error_notification, is_openai_error
from ..models import CardSession, CardMessage
from .ai_card_drawer import (
    build_precision_dalle_prompt,
    generate_dalle_card,
    auto_crop_card_surface,
    normalize_card_data,
    COMPOSITION_VARIANTS,
    DEFAULT_COMPOSITION_VARIANT,
    get_next_fresh_composition,
)
from .card_drawer import generate_business_card
from .dynamic_card_coder import (
    generate_card_code,
    refine_card_code,
    execute_card_code,
)

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an expert Conversational AI Visiting Card Designer & Art Director.
You work iteratively with users (turn by turn) to create, refine, and perfect professional visiting cards.

You will receive:
1. "current_card_state": The current attributes of the card (if this is an ongoing session).
2. "recent_conversation_history": Recent user instructions and past card states (with version numbers).
3. "user_instruction": The user's new message.

YOUR TASK & CORE RULES:

0. INITIAL CARD CREATION (TURN 1 - WHEN CURRENT_CARD_STATE IS EMPTY):
   - Intelligently select the best-matching flagship layout style based on profession, industry, company, or prompt context:
     * TECH / SOFTWARE / ENGINEERING / IT / DEVELOPER / DATA / DEV: Choose "cyber_tech" (circuit traces, glowing neon cyan badge).
     * EXECUTIVE / FOUNDER / CEO / LUXURY / FINANCE / LEGAL / WEALTH: Choose "luxury_gold" (hairline gold borders, luxury crest).
     * CREATIVE / DESIGN / ART / PHOTO / MARKETING / FOOD: Choose "organic_waves" (fluid organic ribbons, warm gold/navy).
     * CORPORATE / CONSULTANT / AGENCY / ARCHITECT / BUSINESS / MEDICAL: Choose "corner_arcs" (bold concentric geometric arcs).
   - If profession or industry is not clearly specified, choose creatively among the 4 styles so new cards are diverse and never repetitive duplicates!
   - In addition, independently select the best-matching "composition_variant" based on profession/style among:
     ["left_monogram_stack", "centered_hero", "split_diagonal", "right_aligned_monogram", "top_banner", "asymmetric_offset"]
     so consecutive new cards are diverse not only in color and pattern, but fundamentally distinct in structural composition!

1. CRITICAL RULE: DESIGN STABILITY ON TEXT EDITS (DO NOT CHANGE DESIGN RANDOMLY!):
   - When a user updates or adds text fields (e.g. "change name to Dodul ch.", "add phone 012555555555", "change designation", "add email", "add my company name ..."):
     * YOU MUST PRESERVE the existing "layout_style", "theme", AND "composition_variant" EXACTLY as they are in "current_card_state"!
     * NEVER change the visual layout style, colors, or structural composition when only text/contact info/company name is being updated or added!
     * Compute "monogram" automatically from the initials of the new name if the name changed (e.g. "Dodul ch." -> "DO").

2. CRITICAL RULE: ROLLBACK & RESTORING PREVIOUS DESIGNS:
   - If the user asks to revert or bring back an earlier design (e.g. "bring back the previous design", "revert to previous design", "restore earlier version", "why did you change the design", "undo design change"):
     * If the user names a specific style (e.g. "organic waves", "corner arcs", "cyber tech", "luxury gold"), set layout_style to that style.
     * Otherwise, inspect "recent_conversation_history", find the earlier version before the redesign, and restore its "layout_style", "theme", and "composition_variant"!
     * Keep the user's latest text fields (name, phone, company, etc.) intact.
     * In "assistant_message", clearly confirm in English that you have restored their preferred previous design while keeping their updated contact info.

3. SUPPORTED FLAGSHIP LAYOUT STYLES ("layout_style"):
   - "organic_waves": Fluid organic waves/ribbons, sun disc, striped circle accent, bold 2-letter monogram on the left, clean right typography (Dark Navy & Warm Gold/Terracotta by default).
   - "corner_arcs": Bold concentric rounded arcs hugging top-right corner, 45-degree diagonal accent stripes in bottom-left corner, bold monogram, modern agency typography (Dark Slate & Vibrant Orange by default).
   - "cyber_tech": Circuit trace grid, neon cyan glow brackets, glowing hexagon monogram badge, tech divider line (Midnight Obsidian & Cyan by default).
   - "luxury_gold": Double hairline gold borders with corner notches, delicate circular crest emblem with monogram, high-fashion typography (Matte Obsidian Black & Champagne Gold).

4. SUPPORTED COMPOSITION VARIANTS ("composition_variant"):
   - "left_monogram_stack": Monogram badge on the far left, all text left-aligned in a vertical stack to its right.
   - "centered_hero": Name and title centered horizontally at the top, monogram badge centered below as a hero element, contact info centered at the bottom.
   - "split_diagonal": Card divided diagonally — monogram and branding occupy the top-right triangle, name/title/contact info occupy the bottom-left triangle.
   - "right_aligned_monogram": All text right-aligned, monogram badge positioned on the far right edge.
   - "top_banner": Name and title in a bold horizontal banner across the top third, monogram small in a corner, contact info in a separate band at the bottom.
   - "asymmetric_offset": Monogram badge offset toward one corner (not centered vertically), text block positioned with significant asymmetric whitespace, avoiding a simple two-column split.

5. VISUAL REDESIGN & DISSATISFACTION:
   - If the user asks for a specific style ("corner arcs", "organic waves", "cyber tech", "luxury gold"), set "layout_style" to that style.
   - If the user asks for a redesign or gives negative/dissatisfaction feedback (e.g. "redesign this", "different design", "fresh look", "this design is very bad", "i don't like it", "looks bad", "hate this design", "not what i wanted"):
     * You MUST choose a DIFFERENT "layout_style", a DIFFERENT "composition_variant" (chosen from the 6 variants), and an appropriate "theme" to provide a truly fresh, upgraded look!
   - ONLY change "theme" when the user explicitly asks to change colors (e.g. "make it red", "change background to black", "change accent to green") or during a redesign.

6. THEME COLOR SPECIFICATION:
   - Each theme has RGB arrays:
     {
       "bg_card": [r, g, b],
       "accent": [r, g, b],
       "accent_secondary": [r, g, b],
       "text_primary": [r, g, b],
       "text_secondary": [r, g, b],
       "text_muted": [r, g, b]
     }
   - Default for organic_waves:
     bg_card: [22, 37, 54], accent: [245, 166, 35], accent_secondary: [217, 83, 47], text_primary: [255, 255, 255], text_secondary: [245, 166, 35], text_muted: [200, 210, 220]
   - Default for corner_arcs:
     bg_card: [26, 32, 38], accent: [245, 95, 30], accent_secondary: [210, 70, 20], text_primary: [255, 255, 255], text_secondary: [200, 210, 220], text_muted: [175, 185, 195]
   - Default for cyber_tech:
     bg_card: [10, 16, 28], accent: [0, 229, 255], accent_secondary: [56, 189, 248], text_primary: [255, 255, 255], text_secondary: [0, 229, 255], text_muted: [148, 163, 184]
   - Default for luxury_gold:
     bg_card: [13, 15, 20], accent: [212, 175, 55], accent_secondary: [245, 215, 127], text_primary: [255, 255, 255], text_secondary: [212, 175, 55], text_muted: [205, 210, 220]

7. ZERO HALLUCINATION & COMPREHENSIVE VISITING CARD DATA SCHEMA:
   - Never invent dummy phone numbers, fake emails, or placeholder addresses.
   - All possible data on a professional visiting card is captured in "card_state":
     * "name": Full name string.
     * "designation": Professional title / role string.
     * "department": Department or division string.
     * "qualifications": Array of degrees / certifications [string] (e.g. ["MBBS (DMC)", "FCPS", "PhD in AI"]). If none, [].
     * "company_name": Organization, company, or clinic name string.
     * "tagline": Company slogan, motto, or subtitle string.
     * "phone": Array of phone numbers [string] (e.g. ["+880 1837000000", "+880 1700111222"]). If none, [].
     * "email": Array of email addresses [string] (e.g. ["mamun@techvision.com", "info@mamun.dev"]). If none, [].
     * "website": Array of website URLs [string] (e.g. ["https://www.techvision.com.bd"]). If none, [].
     * "address": Full street or chamber address string.
     * "branch": Branch, chamber, or office location string.
     * "city": City or district string.
     * "postal_code": Postal/ZIP code string.
     * "country": Country string.
     * "schedule": Working hours, clinic schedule, or visiting hours string.
     * "services": Array of key services or medical specialties [string]. If none, [].
     * "social_links": Object with {"linkedin": "", "github": "", "twitter": "", "facebook": "", "instagram": "", "youtube": ""}.
     * "monogram": 2-3 letter monogram initials (e.g. "MM").
     * "composition_variant": One of "left_monogram_stack", "centered_hero", "split_diagonal", "right_aligned_monogram", "top_banner", "asymmetric_offset".
     * "theme": Color theme dictionary with RGB values.

8. LANGUAGE & ASSISTANT MESSAGE RULE:
   - Always write "assistant_message" in fluent, professional, courteous English (e.g., "I've updated your visiting card information and preserved your existing layout style.").
   - Even if the user instruction is in another language, always deliver the assistant explanation in English.

Return ONLY a JSON object:
{
  "assistant_message": string,
  "card_state": {
    "layout_style": "organic_waves" | "corner_arcs" | "cyber_tech" | "luxury_gold",
    "composition_variant": "left_monogram_stack" | "centered_hero" | "split_diagonal" | "right_aligned_monogram" | "top_banner" | "asymmetric_offset",
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
    "theme": {
      "bg_card": [r, g, b],
      "accent": [r, g, b],
      "accent_secondary": [r, g, b],
      "text_primary": [r, g, b],
      "text_secondary": [r, g, b],
      "text_muted": [r, g, b]
    }
  }
}"""


def reason_card_modifications(current_state: dict, history_list: list, user_message: str, api_key: str) -> tuple[str, dict]:
    """Uses GPT-4o-mini to calculate state diffs, enforce design stability or rollback, and generate conversational response."""
    logger.info(f"Reasoning input - current_card_state: {current_state}")
    logger.info(f"Reasoning input - user_instruction: {user_message}")

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({
                    "current_card_state": current_state,
                    "recent_conversation_history": history_list,
                    "user_instruction": user_message
                })
            }
        ],
        "temperature": 0.2,
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
            parsed = json.loads(content)
            assistant_msg = parsed.get('assistant_message', 'Updated your visiting card design.')
            new_state = parsed.get('card_state', {})
            logger.info(f"Agent reasoning raw parsed assistant_message: {assistant_msg}")
            logger.info(f"Agent reasoning raw parsed card_state theme: {new_state.get('theme')}")
            logger.info(f"Agent reasoning raw parsed layout_style: {new_state.get('layout_style')}")
            logger.info(f"Agent reasoning raw parsed composition_variant: {new_state.get('composition_variant')}")
            return assistant_msg, new_state
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, 'read') else str(e)
        logger.error(f"Agent reasoning OpenAI HTTP error {e.code}: {err_body}")
        send_openai_error_notification(f"Card agent reasoning failed (HTTP {e.code}): {err_body}")
        fallback_state = dict(current_state)
        if not fallback_state.get('name'):
            fallback_state['name'] = user_message[:30]
        return "I've updated your visiting card.", fallback_state
    except Exception as e:
        logger.error(f"Agent reasoning failed: {e}")
        if is_openai_error(e):
            send_openai_error_notification(f"Card agent reasoning error: {e}")
        fallback_state = dict(current_state)
        if not fallback_state.get('name'):
            fallback_state['name'] = user_message[:30]
        return "I've updated your visiting card.", fallback_state


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

def detect_style_intent(text: str) -> str | None:
    if not text:
        return None
    # Strip URLs and emails to avoid matching keywords within them (e.g. user@techvision.com, https://goldencorp.io)
    cleaned = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', ' ', text)
    cleaned = re.sub(r'https?://\S+|www\.\S+', ' ', cleaned)
    t = cleaned.lower()

    if re.search(r'\bcorner[\s_-]?arcs?\b', t):
        return 'corner_arcs'
    if re.search(r'\borganic[\s_-]?waves?\b', t):
        return 'organic_waves'
    if re.search(r'\b(?:cyber[\s_-]?tech|cyber)\b', t):
        return 'cyber_tech'
    # Match 'tech' or 'IT' (uppercase) only when referring to tech style or department, not pronoun 'it'
    if re.search(r'\btech\b', t) or re.search(r'\bIT\b', cleaned):
        return 'cyber_tech'
    if re.search(r'\b(?:luxury[\s_-]?gold|luxury|gold)\b', t):
        return 'luxury_gold'

    return None

def detect_composition_intent(text: str) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', ' ', text)
    cleaned = re.sub(r'https?://\S+|www\.\S+', ' ', cleaned)
    t = cleaned.lower()

    if re.search(r'\b(?:centered[\s_-]?hero|centered|center|centre|middle)\b', t) or 'সেন্টার' in t or 'মাঝখানে' in t:
        return 'centered_hero'
    if re.search(r'\b(?:left[\s_-]?monogram(?:[\s_-]?stack)?|left[\s_-]?aligned|left[\s_-]?side|on the left)\b', t) or 'বাম পাশে' in t or 'বামে' in t:
        return 'left_monogram_stack'
    if re.search(r'\b(?:right[\s_-]?aligned(?:[\s_-]?monogram)?|right[\s_-]?side|on the right)\b', t) or 'ডান পাশে' in t or 'ডানে' in t:
        return 'right_aligned_monogram'
    if re.search(r'\b(?:split[\s_-]?diagonal|diagonal|split)\b', t) or 'ডায়াগোনাল' in t or 'কোনাকুনি' in t:
        return 'split_diagonal'
    if re.search(r'\b(?:top[\s_-]?banner|banner|header)\b', t) or 'ব্যানার' in t or 'টপ' in t:
        return 'top_banner'
    if re.search(r'\b(?:asymmetric[\s_-]?offset|asymmetric|offset)\b', t) or 'অফসেট' in t:
        return 'asymmetric_offset'
    return None


def detect_rollback_intent(text: str) -> bool:
    t = text.lower()
    rollback_keywords = [
        'আগের ডিজাইন', 'আগেরটা', 'আগেরটি', 'আগের টা', 'পূর্বে যে ডিজাইন', 'পূর্বের ডিজাইন',
        'কেন ডিজাইন চ্যাঞ্জ', 'কেন চ্যাঞ্জ', 'আগের মত', 'আগের মতো', 'ফিরিয়ে দাও', 'ফিরিয়ে আনো',
        'bring back', 'previous design', 'revert', 'restore design', 'undo', 'earlier design'
    ]
    return any(k in t for k in rollback_keywords)

def detect_color_intent(text: str) -> bool:
    if not text:
        return False
    # Strip URLs and emails
    cleaned = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', ' ', text)
    cleaned = re.sub(r'https?://\S+|www\.\S+', ' ', cleaned)
    t = cleaned.lower()

    color_names = (
        r'(?:red|blue|green|yellow|orange|purple|pink|black|white|'
        r'dark|light|navy|cyan|gold|teal|maroon|gray|grey|crimson|scarlet|amber)'
    )

    # 1. Direct color properties: background, bg, theme, palette, accent, color, colour
    if re.search(r'\b(?:background|bg|theme|palette|accent|color|colour)\b', t):
        if re.search(rf'\b{color_names}\b', t) or re.search(r'\b(?:change|make|set|switch|update|use|bright|darker|lighter|dark|light)\b', t):
            return True

    # 2. Action + color target: e.g. "make it red", "turn it blue", "paint it green", "change to red"
    if re.search(rf'\b(?:make|turn|paint|change|switch)\s+(?:it\s+)?(?:to\s+)?{color_names}\b', t):
        return True

    # 3. Explicit color phrase: "<color> color", "<color> background", "<color> theme", "<color> design"
    if re.search(rf'\b{color_names}\s+(?:color|colour|bg|background|theme|palette|accent|shade|tone|tint|design)\b', t):
        return True

    return False

def detect_redesign_intent(text: str) -> bool:
    if not text:
        return False
    # Strip URLs and emails
    cleaned = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', ' ', text)
    cleaned = re.sub(r'https?://\S+|www\.\S+', ' ', cleaned)
    t = cleaned.lower()

    # Bengali redesign & dissatisfaction phrases
    bengali_redesign_keywords = [
        'ডিজাইন চ্যাঞ্জ', 'ডিজাইন চেঞ্জ', 'ডিজাইন পরিবর্তন', 'ডিজাইন বদল', 'টেমপ্লেট পরিবর্তন',
        'টেমপ্লেট চ্যাঞ্জ', 'টেমপ্লেট চেঞ্জ', 'অন্য ডিজাইন', 'অন্য টেমপ্লেট', 'নতুন ডিজাইন',
        'নতুন লুক', 'নতুন টেমপ্লেট', 'স্টাইল চ্যাঞ্জ', 'স্টাইল চেঞ্জ', 'স্টাইল পরিবর্তন',
        'লেআউট চ্যাঞ্জ', 'লেআউট চেঞ্জ', 'লেআউট পরিবর্তন', 'ডিজাইন ভালো না', 'ডিজাইন ফালতু',
        'একই ডিজাইন', 'একই টেমপ্লেট', 'ডিজাইন পছন্দ হয়নি', 'অন্য স্টাইল', 'ডিজাইন বদলাও',
        'টেমপ্লেট বদলাও', 'চ্যাঞ্জ কর', 'চেঞ্জ কর', 'পরিবর্তন কর'
    ]
    if any(k in t for k in bengali_redesign_keywords):
        return True

    # 1. Explicit redesign phrases
    redesign_patterns = [
        r'\bredesign\b',
        r'\bdifferent\s+(?:design|template|layout|style|look)\b',
        r'\b(?:new|fresh)\s+(?:look|design|template|layout|style)\b',
        r'\bchange\s+(?:the\s+)?(?:design|template|layout|style)(?:\s+completely)?\b',
        r'\bswitch\s+(?:the\s+)?(?:design|template|layout|style)\b',
        r'\bchange\s+(?:it\s+)?(?:completely|totally|entirely)\b',
        r'\bmake\s+it\s+look\s+different\b',
        r'\bsame\s+(?:design|template|layout)\b',
        r'\bnot\s+changing\s+(?:the\s+)?(?:design|template|layout)\b',
    ]
    for pat in redesign_patterns:
        if re.search(pat, t):
            return True

    # 2. Negative feedback / dissatisfaction phrases
    dissatisfaction_patterns = [
        r'\bthis\s+(?:[\w-]+\s+)?design\s+is\s+(?:very\s+)?bad\b',
        r'\bi\s+don\'?t\s+like\s+(?:this|it)\b',
        r'\bnot\s+good\b',
        r'\blooks\s+bad\b',
        r'\bdon\'?t\s+like\s+(?:the\s+)?design\b',
        r'\bhate\s+this\s+design\b',
        r'\bthis\s+(?:[\w-]+\s+)?looks\s+bad\b',
        r'\bnot\s+what\s+i\s+wanted\b',
        r'\bcan\s+you\s+make\s+it\s+better\b',
        r'\bthis\s+isn\'?t\s+good\b',
    ]
    for pat in dissatisfaction_patterns:
        if re.search(pat, t):
            return True

    return False

def verify_phone_in_image(image_bytes: bytes, expected_phone: str | list) -> bool | None:
    if not expected_phone:
        return None
    if isinstance(expected_phone, (list, tuple)):
        expected_phones = [str(p) for p in expected_phone if str(p).strip()]
    else:
        expected_phones = [str(expected_phone).strip()]
    if not expected_phones:
        return None
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(img)
        clean_ocr = re.sub(r'\D', '', ocr_text)
        for ep in expected_phones:
            clean_expected = re.sub(r'\D', '', ep)
            if clean_expected and clean_expected not in clean_ocr:
                return False
        return True
    except Exception:
        return None


def get_next_fresh_layout_style(seed_text: str | None = None) -> str:
    """
    Diverse layout selector fallback when LLM provides no valid style.
    Uses prompt/text hash to ensure diversity without cross-user database queries.
    """
    available_styles = ['organic_waves', 'cyber_tech', 'luxury_gold', 'corner_arcs']
    if seed_text:
        idx = abs(hash(seed_text)) % len(available_styles)
        return available_styles[idx]
    return 'luxury_gold'


def process_card_agent_turn(session_id: str | None, user_message: str, request=None) -> dict:
    """
    Main entry point for conversational agentic card design.
    Handles session retrieval, LLM design reasoning, precision vector rendering, and storage.
    """
    from card_project.key_manager import get_active_openai_key
    api_key = get_active_openai_key()

    # 1. Retrieve or Create Session (Isolated per session - no cross-user table querying)
    session = None
    is_new_session = False

    if session_id:
        try:
            session = CardSession.objects.filter(id=session_id).first()
        except Exception:
            session = None

    if not session:
        session = CardSession.objects.create(current_state={}, version=1)
        version = 1
        is_new_session = True
    else:
        version = session.version + 1
        is_new_session = False

    current_state = session.current_state or {}
    logger.info(f"Turn start for session {session.id} (v{version}): current_state={current_state}")

    # 2. Extract recent conversation history with full state snapshots
    history_messages = list(session.messages.order_by('-created_at')[:8])
    history_list = []
    for m in reversed(history_messages):
        history_list.append({
            "role": m.role,
            "content": m.content,
            "card_data": m.card_data,
            "version": m.version
        })

    # Record User Message
    CardMessage.objects.create(
        session=session,
        role='user',
        content=user_message,
        version=version
    )

    # 3. Agentic Reasoning: compute new state & assistant explanation
    if api_key:
        assistant_message, updated_state = reason_card_modifications(
            current_state=current_state,
            history_list=history_list,
            user_message=user_message,
            api_key=api_key
        )
    else:
        assistant_message = "Generating visiting card."
        updated_state = dict(current_state)
        if not updated_state.get('name'):
            updated_state['name'] = user_message[:40]

    # Normalize comprehensive visiting card data structure
    updated_state = normalize_card_data(updated_state)

    # 4. Deterministic State Preservation, Explicit Redesign, and Rollback
    explicit_style = detect_style_intent(user_message)
    explicit_composition = detect_composition_intent(user_message)
    is_redesign = detect_redesign_intent(user_message)
    is_rollback = detect_rollback_intent(user_message)
    is_color_intent = detect_color_intent(user_message)

    logger.info(
        f"Session {session.id} v{version} intent analysis: "
        f"is_new_session={is_new_session}, explicit_style={explicit_style}, "
        f"explicit_composition={explicit_composition}, "
        f"is_redesign={is_redesign}, is_color_intent={is_color_intent}, is_rollback={is_rollback}"
    )

    if is_rollback and not is_new_session:
        # Rollback intent detected in ongoing session
        if explicit_style:
            updated_state['layout_style'] = explicit_style
            updated_state['theme'] = DEFAULT_THEMES.get(explicit_style, DEFAULT_THEMES['organic_waves'])
            restored_comp = False
            for m in history_messages:
                prev_data = m.card_data if isinstance(m.card_data, dict) else {}
                if prev_data.get('layout_style') == explicit_style:
                    prev_comp = prev_data.get('composition_variant')
                    updated_state['composition_variant'] = prev_comp if (prev_comp and prev_comp in COMPOSITION_VARIANTS) else DEFAULT_COMPOSITION_VARIANT
                    restored_comp = True
                    break
            if not restored_comp:
                updated_state['composition_variant'] = current_state.get('composition_variant', DEFAULT_COMPOSITION_VARIANT)
        else:
            restored = False
            for m in history_messages:
                prev_data = m.card_data if isinstance(m.card_data, dict) else {}
                prev_style = prev_data.get('layout_style')
                prev_comp = prev_data.get('composition_variant')
                if (prev_style and prev_style != current_state.get('layout_style')) or \
                   (prev_comp and prev_comp != current_state.get('composition_variant')):
                    updated_state['layout_style'] = prev_style or current_state.get('layout_style', 'organic_waves')
                    if prev_data.get('theme'):
                        updated_state['theme'] = prev_data['theme']
                    # Safe fallback for pre-migration card_data missing composition_variant
                    updated_state['composition_variant'] = prev_comp if (prev_comp and prev_comp in COMPOSITION_VARIANTS) else DEFAULT_COMPOSITION_VARIANT
                    restored = True
                    break
            if not restored:
                updated_state['layout_style'] = 'organic_waves'
                updated_state['theme'] = DEFAULT_THEMES['organic_waves']
                updated_state['composition_variant'] = DEFAULT_COMPOSITION_VARIANT
    elif is_new_session:
        # BRAND NEW CARD (No session_id passed):
        # 1. Prioritize explicit_style or GPT's intelligent layout selection based on prompt/profession
        if explicit_style:
            chosen_style = explicit_style
            updated_state['layout_style'] = chosen_style
            if not isinstance(updated_state.get('theme'), dict) or not updated_state.get('theme').get('bg_card'):
                updated_state['theme'] = DEFAULT_THEMES.get(chosen_style, DEFAULT_THEMES['organic_waves'])
        else:
            gpt_style = updated_state.get('layout_style')
            if gpt_style and gpt_style in DEFAULT_THEMES:
                chosen_style = gpt_style
                if not isinstance(updated_state.get('theme'), dict) or not updated_state.get('theme').get('bg_card'):
                    updated_state['theme'] = DEFAULT_THEMES.get(chosen_style, DEFAULT_THEMES['organic_waves'])
            else:
                chosen_style = get_next_fresh_layout_style(seed_text=user_message)
                updated_state['layout_style'] = chosen_style
                updated_state['theme'] = DEFAULT_THEMES.get(chosen_style, DEFAULT_THEMES['luxury_gold'])

        # 2. Composition variant
        if explicit_composition:
            updated_state['composition_variant'] = explicit_composition
        else:
            gpt_comp = updated_state.get('composition_variant')
            if gpt_comp and gpt_comp in COMPOSITION_VARIANTS:
                updated_state['composition_variant'] = gpt_comp
            else:
                updated_state['composition_variant'] = get_next_fresh_composition(seed_text=user_message)
    elif is_redesign:
        # 2. is_redesign (Priority 2: generic redesign / dissatisfaction / change design request)
        logger.info(f"Session {session.id} v{version}: Redesign / dissatisfaction intent detected. Bypassing deterministic override.")

        # Layout style
        current_style = current_state.get('layout_style', 'corner_arcs')
        styles = ['organic_waves', 'cyber_tech', 'luxury_gold', 'corner_arcs']
        if explicit_style:
            updated_state['layout_style'] = explicit_style
        else:
            gpt_style = updated_state.get('layout_style')
            if gpt_style and gpt_style in DEFAULT_THEMES and gpt_style != current_style:
                updated_state['layout_style'] = gpt_style
            else:
                if current_style in styles:
                    next_idx = (styles.index(current_style) + 1) % len(styles)
                    updated_state['layout_style'] = styles[next_idx]
                else:
                    updated_state['layout_style'] = get_next_fresh_layout_style(seed_text=user_message)

        # Composition variant
        current_comp = current_state.get('composition_variant', DEFAULT_COMPOSITION_VARIANT)
        if explicit_composition:
            updated_state['composition_variant'] = explicit_composition
        else:
            gpt_comp = updated_state.get('composition_variant')
            if gpt_comp and gpt_comp in COMPOSITION_VARIANTS and gpt_comp != current_comp:
                updated_state['composition_variant'] = gpt_comp
            else:
                updated_state['composition_variant'] = get_next_fresh_composition(last_variant=current_comp)

        # Theme
        if updated_state.get('theme') and updated_state.get('theme') != current_state.get('theme'):
            pass
        else:
            updated_state['theme'] = DEFAULT_THEMES.get(updated_state['layout_style'], DEFAULT_THEMES['organic_waves'])
    elif explicit_style or explicit_composition:
        # 3. Explicit style or composition request without full redesign
        if explicit_style:
            updated_state['layout_style'] = explicit_style
            if not is_color_intent or not updated_state.get('theme') or updated_state.get('theme') == current_state.get('theme'):
                updated_state['theme'] = DEFAULT_THEMES.get(explicit_style, DEFAULT_THEMES['corner_arcs'])
        else:
            updated_state['layout_style'] = current_state.get('layout_style', 'corner_arcs')

        if explicit_composition:
            updated_state['composition_variant'] = explicit_composition
        else:
            updated_state['composition_variant'] = current_state.get('composition_variant', DEFAULT_COMPOSITION_VARIANT)
    elif is_color_intent:
        # 4. is_color_intent (Priority 4: specific color change instruction like "make it red")
        # layout_style and composition_variant strictly preserved
        updated_state['layout_style'] = current_state.get('layout_style', 'corner_arcs')
        updated_state['composition_variant'] = current_state.get('composition_variant', DEFAULT_COMPOSITION_VARIANT)
        if updated_state.get('theme') and updated_state.get('theme') != current_state.get('theme'):
            logger.info(f"Session {session.id} v{version}: Honoring color change intent: {updated_state.get('theme')}")
        elif current_state.get('theme'):
            logger.info(f"Session {session.id} v{version}: Preserving previous theme {current_state.get('theme')}")
            updated_state['theme'] = current_state['theme']
        else:
            updated_state['theme'] = DEFAULT_THEMES.get(updated_state['layout_style'], DEFAULT_THEMES['organic_waves'])
    else:
        # 5. Plain text edits (Priority 5: name, phone, company, etc.)
        # layout_style, theme, and composition_variant strictly preserved
        if current_state.get('layout_style'):
            logger.info(f"Session {session.id} v{version}: Deterministic override: strictly preserving layout_style '{current_state['layout_style']}'")
            updated_state['layout_style'] = current_state['layout_style']
        elif not updated_state.get('layout_style'):
            updated_state['layout_style'] = 'corner_arcs'

        if current_state.get('theme'):
            logger.info(f"Session {session.id} v{version}: Deterministic override: strictly preserving previous theme {current_state.get('theme')}")
            updated_state['theme'] = current_state['theme']
        elif not updated_state.get('theme'):
            updated_state['theme'] = DEFAULT_THEMES.get(updated_state['layout_style'], DEFAULT_THEMES['organic_waves'])

        if current_state.get('composition_variant'):
            logger.info(f"Session {session.id} v{version}: Deterministic override: strictly preserving composition_variant '{current_state['composition_variant']}'")
            updated_state['composition_variant'] = current_state['composition_variant']
        else:
            updated_state['composition_variant'] = DEFAULT_COMPOSITION_VARIANT

    # Strictly ensure composition_variant is a valid key from COMPOSITION_VARIANTS
    if not updated_state.get('composition_variant') or updated_state.get('composition_variant') not in COMPOSITION_VARIANTS:
        updated_state['composition_variant'] = DEFAULT_COMPOSITION_VARIANT

    # Compute monogram if empty
    if not updated_state.get('monogram') and updated_state.get('name'):
        parts = updated_state['name'].split()
        if len(parts) >= 2:
            updated_state['monogram'] = (parts[0][0] + parts[1][0]).upper()
        else:
            updated_state['monogram'] = updated_state['name'][:2].upper()

    # 5. Generate Visiting Card via Precision Vector Engine (Controlled by AI Decisions)
    if not api_key:
        err_msg = "OpenAI API key not configured — card generation requires an active key."
        send_openai_error_notification(err_msg)
        raise ValueError(err_msg)

    t_img_start = time.time()
    existing_code = current_state.get('_python_code')
    if existing_code and not is_new_session and not is_redesign:
        try:
            refine_card_code(existing_code, updated_state, user_message, api_key)
        except Exception as ref_err:
            logger.debug(f"Refinement pass: {ref_err}")

    try:
        image_bytes = generate_business_card(updated_state)
        updated_state['_python_code'] = f"# Visiting Card Vector Engine: {updated_state.get('layout_style')} / {updated_state.get('composition_variant')}"
        logger.info(f"Vector card rendering took: {time.time() - t_img_start:.3f}s")
    except Exception as e:
        logger.error(f"Vector card rendering failed for session {session.id}: {e}")
        send_openai_error_notification(f"AI card rendering failed: {e}")
        raise RuntimeError(f"AI card rendering failed: {e}")

    # 6. Convert Image to Base64 (In-memory, no disk file saving)
    b64_str = base64.b64encode(image_bytes).decode('utf-8')
    image_base64 = f"data:image/png;base64,{b64_str}"

    # 6. Update Session & Record Assistant Message
    session.current_state = updated_state
    session.version = version
    session.save()

    CardMessage.objects.create(
        session=session,
        role='assistant',
        content=assistant_message,
        card_data=updated_state,
        image_url=image_base64,
        image_base64=image_base64,
        version=version
    )

    ret = {
        "status": "success",
        "session_id": str(session.id),
        "version": version,
        "assistant_message": assistant_message,
        "card_data": updated_state,
        "image_base64": image_base64,
        "image_url": image_base64,
        "user_prompt": user_message,
        "note": "AI-generated cards should be manually verified for text accuracy before printing or sharing.",
    }

    # Optional OCR validation
    phone_check = verify_phone_in_image(image_bytes, updated_state.get('phone', ''))
    if phone_check is False:
        ret["warning"] = "Please verify the phone number on the generated card matches your input exactly, as AI-generated text can occasionally contain errors."

    return ret
