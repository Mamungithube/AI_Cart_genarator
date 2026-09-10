import json
import logging
import threading
import urllib.error
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_NOTIFICATION_URL = "https://server.milo22.cloud/api/notifications/openai-notification"
DEFAULT_NOTIFICATION_API_KEY = "notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a"


def get_notification_config() -> tuple[str, str]:
    """
    Returns (webhook_url, api_key) resolved from Django settings, os.environ, or defaults.
    """
    try:
        url = getattr(settings, 'OPENAI_NOTIFICATION_URL', None) or DEFAULT_NOTIFICATION_URL
        api_key = getattr(settings, 'OPENAI_NOTIFICATION_API_KEY', None) or DEFAULT_NOTIFICATION_API_KEY
    except Exception:
        import os
        url = os.environ.get('OPENAI_NOTIFICATION_URL') or DEFAULT_NOTIFICATION_URL
        api_key = os.environ.get('OPENAI_NOTIFICATION_API_KEY') or DEFAULT_NOTIFICATION_API_KEY
    return url.strip(), api_key.strip()


def parse_openai_error_message(raw_error) -> str:
    """
    Extracts a clean, human-readable error message from an OpenAI error payload.
    Supports bytes, strings, dicts, or Exceptions.
    """
    if not raw_error:
        return "Unknown OpenAI error"

    if isinstance(raw_error, dict):
        # Format: {"error": {"message": "...", "type": "...", "code": "..."}}
        err_obj = raw_error.get("error")
        if isinstance(err_obj, dict):
            msg = err_obj.get("message")
            code = err_obj.get("code")
            err_type = err_obj.get("type")
            parts = [msg] if msg else []
            if code:
                parts.append(f"[code: {code}]")
            if err_type:
                parts.append(f"[type: {err_type}]")
            return " ".join(parts) if parts else str(raw_error)
        elif isinstance(err_obj, str):
            return err_obj
        return str(raw_error)

    if isinstance(raw_error, (bytes, bytearray)):
        try:
            raw_error = raw_error.decode("utf-8", errors="replace")
        except Exception:
            raw_error = str(raw_error)

    if isinstance(raw_error, str):
        try:
            parsed = json.loads(raw_error)
            if isinstance(parsed, dict) and "error" in parsed:
                return parse_openai_error_message(parsed)
        except Exception:
            pass
        return raw_error

    if isinstance(raw_error, urllib.error.HTTPError):
        try:
            body = raw_error.read().decode("utf-8", errors="replace")
            parsed_msg = parse_openai_error_message(body)
            return f"OpenAI HTTP {raw_error.code}: {parsed_msg}"
        except Exception:
            return f"OpenAI HTTP {raw_error.code}: {raw_error.reason}"

    return str(raw_error)


def is_openai_error(exc: Exception) -> bool:
    """
    Determines whether an exception is related to OpenAI API communication or configuration.
    """
    if exc is None:
        return False

    exc_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    openai_keywords = [
        "openai", "gpt-4", "gpt-3.5", "dall-e",
        "api.openai.com", "rate limit", "insufficient_quota",
        "invalid api key", "billing", "model not found",
        "authenticationerror", "ratelimiterror", "apierror"
    ]

    for kw in openai_keywords:
        if kw in exc_str or kw in exc_type:
            return True

    if isinstance(exc, urllib.error.HTTPError):
        if hasattr(exc, "url") and exc.url and "openai.com" in str(exc.url):
            return True

    return False


def _send_payload(url: str, api_key: str, message: str) -> bool:
    """Synchronously sends the error notification payload."""
    try:
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Milo22-Card-Generator/1.0"
        }
        payload = {
            "message": str(message)
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code in (200, 201):
            logger.info(f"OpenAI error notification successfully delivered to {url} (status {resp.status_code})")
            return True
        else:
            logger.warning(
                f"OpenAI error notification webhook returned status {resp.status_code}: {resp.text[:200]}"
            )
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to deliver OpenAI error notification to {url}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error while sending OpenAI notification: {e}")
        return False


def send_openai_error_notification(error_message, async_send: bool = True):
    """
    Triggers an immediate error notification to the Milo22 webhook:
    POST https://server.milo22.cloud/api/notifications/openai-notification
    Headers:
      X-API-KEY: notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a
    Body:
      {"message": "error message"}

    Parameters:
      error_message: str, dict, or Exception representing the OpenAI error.
      async_send: bool, defaults to True. When True, executes in a background thread
                  to prevent any latency or webhook failure from impacting the user request.
    """
    clean_message = parse_openai_error_message(error_message)
    if not clean_message or not clean_message.strip():
        clean_message = "An unspecified error occurred with OpenAI service."

    url, api_key = get_notification_config()

    if async_send:
        t = threading.Thread(
            target=_send_payload,
            args=(url, api_key, clean_message),
            daemon=True,
            name="openai-notification-thread"
        )
        t.start()
        return t
    else:
        return _send_payload(url, api_key, clean_message)
