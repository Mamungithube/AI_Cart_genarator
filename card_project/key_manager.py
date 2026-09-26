import os
import json
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def get_active_openai_key() -> str:
    """
    Returns the active OpenAI API key from ai_config.json or environment variables.
    """
    config_file = getattr(settings, 'AI_CONFIG_FILE', settings.BASE_DIR / 'ai_config.json')
    if Path(config_file).exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                key = data.get('openai_key') or data.get('api_key') or ''
                if key and (key.startswith('sk-') or data.get('provider') == 'openai'):
                    return key.strip()
        except Exception as e:
            logger.warning(f"Error reading ai_config.json: {e}")

    key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', '')
    return key.strip() if key else ''
