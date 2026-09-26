import os
import logging
import requests

logger = logging.getLogger(__name__)


def is_openai_error(exception: Exception) -> bool:
    """
    Checks if an exception is related to OpenAI API errors (quota, rate limit, auth, invalid key).
    """
    msg = str(exception).lower()
    openai_keywords = ['openai', 'quota', 'rate limit', '429', '401', 'api key', 'authentication', 'unauthorized']
    return any(keyword in msg for keyword in openai_keywords)


def send_openai_error_notification(message: str) -> bool:
    """
    Sends notification about OpenAI errors (e.g. to a webhook or logger).
    """
    logger.error(f"[OpenAI Error Notification] {message}")
    webhook_url = os.getenv('ERROR_WEBHOOK_URL')
    if webhook_url:
        try:
            requests.post(webhook_url, json={"error": message, "service": "image_processor"}, timeout=5)
            return True
        except Exception as e:
            logger.warning(f"Failed to send webhook error notification: {e}")
    return False
