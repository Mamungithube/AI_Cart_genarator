import os
import re
import json
import logging
import requests
from django.conf import settings
from .key_manager import get_active_gemini_key, get_active_openai_key

logger = logging.getLogger(__name__)


def extract_json_from_response(text: str) -> dict:
    """
    Safely extracts and parses JSON dictionary from LLM text output.
    """
    if not text:
        return {}
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\n", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\n```$", "", clean).strip()

    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Regex search for outermost JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {}


def call_gemini_json(
    prompt: str = None,
    contents: list = None,
    temperature: float = 0.1,
    api_key: str = None,
    model: str = "gemini-2.0-flash"
) -> dict:
    """
    Calls Google Gemini API with JSON output mode.
    Falls back gracefully to requests REST API for zero-dependency execution.
    """
    active_key = api_key or get_active_gemini_key() or get_active_openai_key()
    if not active_key:
        raise ValueError("Gemini API key is not configured.")

    # 1. If key is an OpenAI key (starts with sk-), use OpenAI
    if active_key.startswith("sk-"):
        return _call_openai_json_fallback(prompt, contents, temperature, active_key)

    # 2. Try official SDK if available
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=active_key)
        sdk_contents = []
        if prompt:
            sdk_contents.append(prompt)
        elif contents:
            for item in contents:
                for part in item.get("parts", []):
                    if "text" in part:
                        sdk_contents.append(part["text"])

        response = client.models.generate_content(
            model=model,
            contents=sdk_contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
            )
        )
        data = extract_json_from_response(response.text)
        if data:
            return data
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"google.genai SDK call failed: {e}. Falling back to REST API...")

    # 3. Direct REST API via requests (zero external SDK requirements)
    candidate_models = [model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    session = requests.Session()
    last_error = None

    for m in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={active_key}"

        if contents:
            req_contents = contents
        else:
            req_contents = [{"role": "user", "parts": [{"text": prompt or ""}]}]

        payload = {
            "contents": req_contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = session.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                resp_data = resp.json()
                candidates = resp_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        parsed = extract_json_from_response(parts[0]["text"])
                        if parsed:
                            return parsed
            else:
                last_error = f"Gemini API HTTP {resp.status_code}: {resp.text}"
                logger.warning(f"Model {m} HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as ex:
            last_error = str(ex)
            logger.warning(f"REST call for model {m} failed: {ex}")

    if last_error:
        raise RuntimeError(f"Gemini API request failed: {last_error}")
    raise RuntimeError("Failed to parse valid JSON from Gemini response.")


def _call_openai_json_fallback(prompt, contents, temperature, api_key):
    """Fallback when an OpenAI sk- key is provided."""
    session = requests.Session()
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_content = prompt or ""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }

    resp = session.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return extract_json_from_response(content)
    raise RuntimeError(f"OpenAI fallback failed HTTP {resp.status_code}: {resp.text}")
