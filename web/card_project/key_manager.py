import os
import base64
import hashlib
import logging
import requests
from django.conf import settings

try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTO = True
except ImportError:
    Fernet = None
    InvalidToken = Exception
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


def _get_fernet():
    """
    Derives a deterministic 32-byte Fernet key from Django's SECRET_KEY.
    """
    if not HAS_CRYPTO or Fernet is None:
        raise RuntimeError("cryptography library is not installed in the current Python environment.")
    secret_bytes = getattr(settings, 'SECRET_KEY', 'django-insecure-default-key').encode('utf-8')
    derived_32bytes = hashlib.sha256(secret_bytes).digest()
    fernet_key = base64.urlsafe_b64encode(derived_32bytes)
    return Fernet(fernet_key)


def encrypt_key(raw_key: str) -> str:
    """
    Encrypts a plaintext key string into an authenticated Fernet ciphertext token.
    """
    if not raw_key:
        return ""
    fernet = _get_fernet()
    return fernet.encrypt(raw_key.strip().encode('utf-8')).decode('utf-8')


def decrypt_key(encrypted_key: str) -> str:
    """
    Decrypts a Fernet ciphertext token back into the plaintext key string.
    """
    if not encrypted_key:
        return ""
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted_key.strip().encode('utf-8')).decode('utf-8')
    except InvalidToken:
        logger.error("Failed to decrypt API key: Invalid token or SECRET_KEY mismatch.")
        raise ValueError("Decryption failed. The secret key may have changed.")


def mask_key(raw_key: str) -> str:
    """
    Returns a masked preview of an API key for safe UI and API presentation.
    Example: 'sk-proj-abc...1234'
    """
    if not raw_key:
        return ""
    clean = raw_key.strip()
    if len(clean) <= 12:
        return clean[:3] + "..." + clean[-2:] if len(clean) > 5 else "***"
    return f"{clean[:7]}...{clean[-4:]}"


def hash_fingerprint(raw_key: str) -> str:
    """
    Computes a SHA-256 hex digest for key integrity tracking without revealing the key.
    """
    if not raw_key:
        return ""
    return hashlib.sha256(raw_key.strip().encode('utf-8')).hexdigest()


def get_active_openai_key() -> str:
    """
    Retrieves the currently active OpenAI API key.
    Checks the database first (decrypting the stored ciphertext).
    Falls back to environment variables (OPENAI_API_KEY) if database is empty or inactive.
    """
    if HAS_CRYPTO:
        try:
            from generator.models import OpenAIKeyConfig
            active_config = OpenAIKeyConfig.objects.filter(is_active=True).order_by('-updated_at').first()
            if active_config and active_config.encrypted_key:
                decrypted = decrypt_key(active_config.encrypted_key)
                if decrypted:
                    return decrypted
        except Exception as exc:
            logger.warning(f"Failed to load OpenAI key from database: {exc}. Falling back to environment.")

    # Fallback to environment variable / Django settings
    return (
        os.environ.get('OPENAI_API_KEY') or
        os.environ.get('Open_AI_Key') or
        getattr(settings, 'OPENAI_API_KEY', '') or
        ''
    ).strip()


def get_openai_key_metadata() -> dict:
    """
    Returns non-sensitive status and masked preview of the active key.
    """
    try:
        from generator.models import OpenAIKeyConfig
        active_config = OpenAIKeyConfig.objects.filter(is_active=True).order_by('-updated_at').first()
        if active_config and active_config.encrypted_key:
            return {
                "source": "database",
                "is_configured": True,
                "masked_key": active_config.masked_key,
                "key_fingerprint": active_config.key_hash[:16] + "...",
                "updated_at": active_config.updated_at.isoformat() if active_config.updated_at else None,
            }
    except Exception as exc:
        logger.warning(f"Error fetching OpenAI key metadata: {exc}")

    env_key = (os.environ.get('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', '') or '').strip()
    if env_key:
        return {
            "source": "environment",
            "is_configured": True,
            "masked_key": mask_key(env_key),
            "key_fingerprint": hash_fingerprint(env_key)[:16] + "...",
            "updated_at": None,
        }

    return {
        "source": "none",
        "is_configured": False,
        "masked_key": None,
        "key_fingerprint": None,
        "updated_at": None,
    }


def set_active_openai_key(raw_key: str):
    """
    Encrypts and saves the OpenAI API key into the database.
    """
    from generator.models import OpenAIKeyConfig
    raw_key = raw_key.strip()
    encrypted = encrypt_key(raw_key)
    fingerprint = hash_fingerprint(raw_key)
    masked = mask_key(raw_key)

    config = OpenAIKeyConfig.objects.first()
    if not config:
        config = OpenAIKeyConfig()

    config.encrypted_key = encrypted
    config.key_hash = fingerprint
    config.masked_key = masked
    config.is_active = True
    config.save()
    return config


def clear_active_openai_key():
    """
    Deactivates or deletes the active DB key so the system reverts to environment fallback.
    """
    from generator.models import OpenAIKeyConfig
    count = OpenAIKeyConfig.objects.all().delete()[0]
    return count


def validate_openai_key_live(raw_key: str) -> tuple[bool, str]:
    """
    Optionally tests the key against OpenAI API v1/models.
    Returns (is_valid, message).
    """
    raw_key = raw_key.strip()
    if not raw_key:
        return False, "API key cannot be empty."

    try:
        resp = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {raw_key}"},
            timeout=5
        )
        if resp.status_code == 200:
            return True, "Key verified successfully with OpenAI."
        elif resp.status_code == 401:
            return False, "OpenAI rejected this key: 401 Unauthorized (Invalid API Key)."
        else:
            return True, f"Key accepted with response status {resp.status_code}."
    except requests.exceptions.RequestException as req_err:
        logger.warning(f"Could not reach OpenAI to verify key: {req_err}")
        # Allow saving even if offline/firewalled
        return True, "Notice: Key saved (OpenAI live verification skipped due to network timeout)."
