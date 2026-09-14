import os
import base64
import json
import logging
import cv2
import numpy as np
import requests
import concurrent.futures
from card_project.notifications import send_openai_error_notification, is_openai_error

logger = logging.getLogger(__name__)

FINANCIAL_CARD_TYPES = {"Credit Card", "Debit Card", "ATM Card", "Gift Card"}

BUSINESS_TYPES = [
    'Accountant', 'App Developer', 'Auto Parts', 'Barber', 'Cafe', 'Car Rental',
    'Carpenter', 'Catering', 'Cleaner', 'Clothing Store', 'Coaching Center',
    'Construction', 'Courier Service', 'Dentist', 'Digital Marketer', 'Doctor',
    'Electrician', 'Electronics Store', 'Grocery Store', 'Home Inspector',
    'Hospital', 'Insurance Agent', 'Lawyer', 'Loan Officer', 'Mechanic',
    'Painter', 'Pharmacy', 'Plumber', 'Property Dealer', 'Realtor',
    'Restaurant', 'Salon', 'Software Company', 'Teacher', 'Travel Agent'
]

PERSONAL_TYPES = [
    "ATM Card", "Boarding Pass", "Business Card", "Credit Card", "Debit Card",
    "Driving License", "Employee ID", "Gift Card", "Gym Card", "Library Card",
    "Loyalty Card", "Membership Card", "National ID", "Passport", "Personal Card",
    "Student ID", "Transport Card", "Travel Card", "Visiting Card"
]

_HTTP_SESSION = None


def _get_http_session():
    """
    Reuses an HTTP session with connection pooling to eliminate TLS handshake latency.
    """
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        _HTTP_SESSION = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
        _HTTP_SESSION.mount("https://", adapter)
        _HTTP_SESSION.mount("http://", adapter)
    return _HTTP_SESSION


def _mask_card_number(number: str) -> str:
    digits = number.replace(" ", "").replace("-", "")
    if len(digits) >= 4:
        return f"****  ****  ****  {digits[-4:]}"
    return "****  ****  ****  ****"


def _prepare_b64_for_ocr(bgr: np.ndarray, max_dim: int = 1024) -> str:
    """
    Downscales image for fast network transmission to Google Vision / OpenAI.
    """
    if bgr is None:
        return ""
    h, w = bgr.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        target_w = int(w * scale)
        target_h = int(h * scale)
        small = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        small = bgr
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    success, buffer = cv2.imencode(".jpg", small, encode_params)
    if not success:
        return ""
    return base64.b64encode(buffer).decode("utf-8")


def _detect_rotation_and_extract_text(image_b64: str, vision_api_key: str):
    if not vision_api_key or not image_b64:
        return 0, ""

    url = f"https://vision.googleapis.com/v1/images:annotate?key={vision_api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION"}],
                "imageContext": {"languageHints": ["en"]}
            }
        ]
    }
    rotation = 0
    raw_text = ""

    try:
        session = _get_http_session()
        response = session.post(url, json=payload, timeout=20)
        data = response.json()
        pages = data.get("responses", [{}])[0].get("fullTextAnnotation", {}).get("pages", [])

        if pages and pages[0].get("blocks"):
            blocks = pages[0]["blocks"]
            vertices = blocks[0]["boundingBox"]["vertices"]
            v0, v1, v3 = vertices[0], vertices[1], vertices[3]
            x0, y0 = v0.get("x", 0), v0.get("y", 0)
            x1, y1 = v1.get("x", 0), v1.get("y", 0)
            x3, y3 = v3.get("x", 0), v3.get("y", 0)

            if x1 >= x0 and y3 >= y0:
                rotation = 0
            elif x1 <= x0 and y3 >= y0:
                rotation = 90
            elif x1 <= x0 and y3 <= y0:
                rotation = 180
            else:
                rotation = 270

        raw_text = data.get("responses", [{}])[0].get("fullTextAnnotation", {}).get("text", "").strip()
    except Exception as e:
        logger.warning(f"Google Vision API call failed: {e}")

    return rotation, raw_text


def _rotate_image_upright(bgr: np.ndarray, rotation: int) -> np.ndarray:
    if bgr is None:
        return None
    if rotation == 90:
        return cv2.rotate(bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation == 180:
        return cv2.rotate(bgr, cv2.ROTATE_180)
    elif rotation == 270:
        return cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    return bgr


def _process_single_card_ocr(bgr: np.ndarray, vision_api_key: str):
    """
    Performs OCR and upright rotation for a single card image.
    """
    if bgr is None:
        return None, ""
    image_b64 = _prepare_b64_for_ocr(bgr)
    rotation = 0
    raw_text = ""
    if vision_api_key:
        rotation, raw_text = _detect_rotation_and_extract_text(image_b64, vision_api_key)
    rotated_bgr = _rotate_image_upright(bgr, rotation)
    return rotated_bgr, raw_text


def _build_prompt(raw_text: str) -> str:
    return f"""
You are a card data extractor. Below is raw text extracted from a card image via OCR.
Your job is to parse it into structured JSON.
Only return is_card: false if the text is completely empty or pure gibberish with no meaningful words.
Otherwise always treat it as a card and extract whatever is visible.

RAW TEXT:
{raw_text}

Step 1: Is this text from a card?
If not, return only: {{"is_card": false}}

Step 2: Identify the card type.
Business types: {json.dumps(BUSINESS_TYPES)}
Personal types: {json.dumps(PERSONAL_TYPES)}
If none match, write your best short label.

Step 3: Extract visible data based on card type.

If card_type is one of: Credit Card, Debit Card, ATM Card, Gift Card:
{{
  "is_card": true,
  "card_type": "",
  "bank_name": "",
  "cardholder_name": "",
  "card_number": "****  ****  ****  XXXX",
  "expiry": "**/**",
  "cvv": "***"
}}

For all other card types:
{{
  "is_card": true,
  "card_type": "",
  "name": "",
  "job_title": "",
  "company": "",
  "phones": [],
  "emails": [],
  "websites": [],
  "address": "",
  "social_media": {{
    "facebook": [],
    "linkedin": [],
    "twitter": [],
    "instagram": [],
    "other": []
  }},
  "other_details": ""
}}

Rules:
- Only use data from the raw text above
- Never hallucinate or guess
- Multiple values go in arrays
- Return JSON only, no explanation, no markdown
"""


def extract_with_rotation(front_bgr, back_bgr, openai_api_key: str, vision_api_key: str):
    """
    Rotates front & back correctly, sends OCR text to GPT-4o-mini (4x faster), and extracts structured data.
    Runs front and back OCR concurrently when both are provided.
    """
    if not openai_api_key:
        err_msg = "OpenAI API key not configured — card extraction requires an active key."
        send_openai_error_notification(err_msg)
        raise ValueError(err_msg)

    # 1. Concurrently process rotation & OCR for front and back
    if front_bgr is not None and back_bgr is not None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            front_future = executor.submit(_process_single_card_ocr, front_bgr, vision_api_key)
            back_future = executor.submit(_process_single_card_ocr, back_bgr, vision_api_key)
            rotated_front, front_text = front_future.result()
            rotated_back, back_text = back_future.result()
    elif front_bgr is not None:
        rotated_front, front_text = _process_single_card_ocr(front_bgr, vision_api_key)
        rotated_back, back_text = None, ""
    elif back_bgr is not None:
        rotated_front, front_text = None, ""
        rotated_back, back_text = _process_single_card_ocr(back_bgr, vision_api_key)
    else:
        rotated_front, front_text = None, ""
        rotated_back, back_text = None, ""

    raw_text = front_text if front_text else ""
    if back_text:
        raw_text = (raw_text + "\n---\n" + back_text).strip()

    card_model = os.environ.get("OPENAI_CARD_MODEL", "gpt-4o-mini").strip()
    session = _get_http_session()

    # 2. Structured JSON parsing
    if raw_text:
        payload = json.dumps({
            "model": card_model,
            "messages": [{"role": "user", "content": _build_prompt(raw_text)}],
            "max_tokens": 650,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        try:
            req = session.post(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=25
            )
            if req.status_code != 200:
                err_text = req.text
                try:
                    err_json = req.json()
                    err_text = err_json.get("error", {}).get("message") or str(err_json)
                except Exception:
                    pass
                err_msg = f"OpenAI API error ({req.status_code}): {err_text}"
                send_openai_error_notification(err_msg)
                raise RuntimeError(err_msg)

            content = req.json()["choices"][0]["message"]["content"]
            clean = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)
        except requests.exceptions.RequestException as e:
            err_msg = f"OpenAI request failed: {e}"
            send_openai_error_notification(err_msg)
            raise RuntimeError(err_msg)
    else:
        # Direct OpenAI Vision fallback if Google Vision OCR yielded no text
        content = [
            {"type": "text", "text": _build_prompt("Card images uploaded")}
        ]
        if rotated_front is not None:
            fb_b64 = _prepare_b64_for_ocr(rotated_front)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{fb_b64}"}
            })
        if rotated_back is not None:
            bb_b64 = _prepare_b64_for_ocr(rotated_back)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{bb_b64}"}
            })

        payload = json.dumps({
            "model": card_model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 650,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        try:
            req = session.post(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            if req.status_code != 200:
                err_text = req.text
                try:
                    err_json = req.json()
                    err_text = err_json.get("error", {}).get("message") or str(err_json)
                except Exception:
                    pass
                err_msg = f"OpenAI Vision API error ({req.status_code}): {err_text}"
                send_openai_error_notification(err_msg)
                raise RuntimeError(err_msg)

            content = req.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
        except requests.exceptions.RequestException as e:
            err_msg = f"OpenAI Vision request failed: {e}"
            send_openai_error_notification(err_msg)
            raise RuntimeError(err_msg)

    # 3. Mask financial card numbers
    if result.get("card_type") in FINANCIAL_CARD_TYPES:
        result["card_number"] = _mask_card_number(result.get("card_number", ""))
        result["cvv"] = "***"
        result["expiry"] = "**/**"
        for field in ["name", "job_title", "company", "phones", "emails",
                      "websites", "address", "social_media", "other_details"]:
            result.pop(field, None)

    return rotated_front, rotated_back, result
