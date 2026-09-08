import os
import io
import re
import json
import base64
import logging
import urllib.request
from pathlib import Path
from django.conf import settings
from ..models import CardSession, CardMessage
from .ai_card_drawer import (
    build_precision_dalle_prompt,
    generate_dalle_card,
    auto_crop_card_surface,
)
from .card_drawer import generate_business_card

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

1. CRITICAL RULE: DESIGN STABILITY ON TEXT EDITS (DO NOT CHANGE DESIGN RANDOMLY!):
   - When a user updates text fields (e.g. "change name to Dodul ch.", "add phone 012555555555", "change designation", "add email"):
     * YOU MUST PRESERVE the existing "layout_style" and "theme" EXACTLY as they are in "current_card_state"!
     * NEVER change the visual layout style or colors when only text/contact info is being updated or added!
     * Compute "monogram" automatically from the initials of the new name if the name changed (e.g. "Dodul ch." -> "DO").

2. CRITICAL RULE: ROLLBACK & RESTORING PREVIOUS DESIGNS:
   - If the user asks to revert or bring back an earlier design (e.g. "bring back the previous design", "আগের ডিজাইন আনো", "আগেরটা ফিরিয়ে দাও", "কেন ডিজাইন চ্যাঞ্জ করলে", "undo design change"):
     * If the user names a specific style (e.g. "organic waves" / "অর্গানিক ওয়েভ"), set layout_style to that style.
     * Otherwise, inspect "recent_conversation_history", find the earlier version before the redesign, and restore its "layout_style" and "theme"!
     * Keep the user's latest text fields (name, phone, company, etc.) intact.
     * In "assistant_message", warmly confirm in the user's language (e.g. Bengali if spoken by user) that you have restored their preferred previous design while keeping their updated contact info.

3. SUPPORTED FLAGSHIP LAYOUT STYLES ("layout_style"):
   - "organic_waves": Fluid organic waves/ribbons, sun disc, striped circle accent, bold 2-letter monogram on the left, clean right typography (Dark Navy & Warm Gold/Terracotta by default).
   - "corner_arcs": Bold concentric rounded arcs hugging top-right corner, 45-degree diagonal accent stripes in bottom-left corner, bold monogram, modern agency typography (Dark Slate & Vibrant Orange by default).
   - "cyber_tech": Circuit trace grid, neon cyan glow brackets, glowing hexagon monogram badge, tech divider line (Midnight Obsidian & Cyan by default).
   - "luxury_gold": Double hairline gold borders with corner notches, delicate circular crest emblem with monogram, high-fashion typography (Matte Obsidian Black & Champagne Gold).

4. EXPLICIT VISUAL REDESIGN:
   - If the user asks for "corner arcs" / "কর্নার আর্ক", set "layout_style" to "corner_arcs".
   - If the user asks for "organic waves" / "অর্গানিক ওয়েভ", set "layout_style" to "organic_waves".
   - If the user asks for "cyber tech" / "সাইবার টেক", set "layout_style" to "cyber_tech".
   - If the user asks for "luxury gold" / "লাক্সারি গোল্ড", set "layout_style" to "luxury_gold".
   - ONLY change "layout_style" when the user explicitly requests a design change.
   - ONLY change "theme" when the user explicitly asks to change colors (e.g. "make it red", "change background to black", "change accent to green").

5. THEME COLOR SPECIFICATION:
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

6. ZERO HALLUCINATION:
   - Never invent dummy phone numbers, fake emails, or placeholder addresses.
   - If a contact field is not provided, keep it empty "".

Return ONLY a JSON object:
{
  "assistant_message": string,
  "card_state": {
    "layout_style": "organic_waves" | "corner_arcs" | "cyber_tech" | "luxury_gold",
    "name": string,
    "designation": string,
    "company_name": string,
    "phone": string,
    "email": string,
    "website": string,
    "address": string,
    "schedule": string,
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
            return assistant_msg, new_state
    except Exception as e:
        logger.error(f"Agent reasoning failed: {e}")
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
    t = text.lower()
    if any(k in t for k in ['corner arc', 'corner_arc', 'corner-arc', 'কর্নার আর্ক', 'কর্নার']):
        return 'corner_arcs'
    if any(k in t for k in ['organic wave', 'organic_wave', 'organic-wave', 'অর্গানিক ওয়েভ', 'অর্গানিক', 'তরঙ্গ']):
        return 'organic_waves'
    if any(k in t for k in ['cyber', 'tech', 'সাইবার', 'টেক', 'আইটি']):
        return 'cyber_tech'
    if any(k in t for k in ['luxury', 'gold', 'লাক্সারি', 'গোল্ড', 'সোনালী']):
        return 'luxury_gold'
    return None

def detect_rollback_intent(text: str) -> bool:
    t = text.lower()
    rollback_keywords = [
        'আগের ডিজাইন', 'আগেরটা', 'আগেরটি', 'আগের টা', 'পূর্বে যে ডিজাইন', 'পূর্বের ডিজাইন',
        'কেন ডিজাইন চ্যাঞ্জ', 'কেন চ্যাঞ্জ', 'আগের মত', 'আগের মতো', 'ফিরিয়ে দাও', 'ফিরিয়ে আনো',
        'bring back', 'previous design', 'revert', 'restore design', 'undo', 'earlier design'
    ]
    return any(k in t for k in rollback_keywords)


def get_next_fresh_layout_style(last_style: str | None = None) -> str:
    """
    Guarantees that every newly initiated card session (without session_id)
    uses a DIFFERENT design from the previous card, so consecutive cards are never identical.
    """
    available_styles = ['organic_waves', 'cyber_tech', 'luxury_gold', 'corner_arcs']
    if last_style and last_style in available_styles:
        next_idx = (available_styles.index(last_style) + 1) % len(available_styles)
        return available_styles[next_idx]
    return 'luxury_gold'


def process_card_agent_turn(session_id: str | None, user_message: str, request=None) -> dict:
    """
    Main entry point for conversational agentic card design.
    Handles session retrieval, LLM design reasoning, precision vector rendering, and storage.
    """
    from card_project.key_manager import get_active_openai_key
    api_key = get_active_openai_key()

    # 1. Retrieve or Create Session
    session = None
    is_new_session = False
    last_system_style = None

    if session_id:
        try:
            session = CardSession.objects.filter(id=session_id).first()
        except Exception:
            session = None

    if not session:
        last_sess = CardSession.objects.order_by('-created_at').first()
        if last_sess and last_sess.current_state:
            last_system_style = last_sess.current_state.get('layout_style')

        session = CardSession.objects.create(current_state={}, version=1)
        version = 1
        is_new_session = True
    else:
        version = session.version + 1
        is_new_session = False

    current_state = session.current_state or {}

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

    # Ensure clean string values
    for k in ['name', 'designation', 'company_name', 'address', 'schedule', 'phone', 'email', 'website', 'monogram']:
        updated_state[k] = str(updated_state.get(k) or '').strip()

    # 4. Deterministic State Preservation, Explicit Redesign, and Rollback
    explicit_style = detect_style_intent(user_message)
    is_rollback = detect_rollback_intent(user_message)

    if is_rollback and not is_new_session:
        # Rollback intent detected in ongoing session
        if explicit_style:
            updated_state['layout_style'] = explicit_style
            updated_state['theme'] = DEFAULT_THEMES.get(explicit_style, DEFAULT_THEMES['organic_waves'])
        else:
            restored = False
            for m in history_messages:
                prev_data = m.card_data or {}
                prev_style = prev_data.get('layout_style')
                if prev_style and prev_style != current_state.get('layout_style'):
                    updated_state['layout_style'] = prev_style
                    if prev_data.get('theme'):
                        updated_state['theme'] = prev_data['theme']
                    restored = True
                    break
            if not restored:
                updated_state['layout_style'] = 'organic_waves'
                updated_state['theme'] = DEFAULT_THEMES['organic_waves']
    elif explicit_style:
        # Explicit style change requested by user
        updated_state['layout_style'] = explicit_style
        if not updated_state.get('theme') or updated_state.get('theme') == current_state.get('theme'):
            updated_state['theme'] = DEFAULT_THEMES.get(explicit_style, DEFAULT_THEMES['corner_arcs'])
    elif is_new_session:
        # BRAND NEW CARD (No session_id passed):
        # Guarantee a DIFFERENT design from the last card!
        chosen_style = get_next_fresh_layout_style(last_style=last_system_style)
        updated_state['layout_style'] = chosen_style
        updated_state['theme'] = DEFAULT_THEMES.get(chosen_style, DEFAULT_THEMES['luxury_gold'])
    else:
        # ONGOING SESSION (session_id passed):
        # Strictly preserve the user's established design on text/phone/name edits
        if current_state.get('layout_style'):
            updated_state['layout_style'] = current_state['layout_style']
        if current_state.get('theme'):
            updated_state['theme'] = current_state['theme']
        elif not updated_state.get('theme'):
            updated_state['theme'] = DEFAULT_THEMES.get(updated_state['layout_style'], DEFAULT_THEMES['organic_waves'])

    # Compute monogram if empty
    if not updated_state.get('monogram') and updated_state.get('name'):
        parts = updated_state['name'].split()
        if len(parts) >= 2:
            updated_state['monogram'] = (parts[0][0] + parts[1][0]).upper()
        else:
            updated_state['monogram'] = updated_state['name'][:2].upper()

    # 5. Generate High-Definition Visiting Card Image
    user_wants_dalle = any(w in user_message.lower() for w in ['dall-e', 'dalle', 'diffusion image', 'ai illustration'])

    image_bytes = None
    if user_wants_dalle and api_key:
        logger.info("User explicitly requested DALL-E generation...")
        dalle_prompt = build_precision_dalle_prompt(updated_state)
        raw_bytes = generate_dalle_card(dalle_prompt, api_key)
        if raw_bytes:
            image_bytes = auto_crop_card_surface(raw_bytes)

    # Primary High-Definition Precision Vector Engine
    if not image_bytes:
        image_bytes = generate_business_card(updated_state)

    # 5. Save Image to Media Directory
    media_cards_dir = Path(settings.MEDIA_ROOT) / 'cards'
    media_cards_dir.mkdir(parents=True, exist_ok=True)

    filename = f"card_{session.id}_v{version}.png"
    filepath = media_cards_dir / filename
    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    relative_url = f"{settings.MEDIA_URL}cards/{filename}"
    if request:
        image_url = request.build_absolute_uri(relative_url)
    else:
        image_url = relative_url

    # 6. Update Session & Record Assistant Message
    session.current_state = updated_state
    session.version = version
    session.save()

    CardMessage.objects.create(
        session=session,
        role='assistant',
        content=assistant_message,
        card_data=updated_state,
        image_url=relative_url,
        version=version
    )

    return {
        "status": "success",
        "session_id": str(session.id),
        "version": version,
        "assistant_message": assistant_message,
        "image_url": image_url,
    }
