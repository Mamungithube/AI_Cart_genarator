import io
import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

from generator.services.card_drawer import generate_business_card, STYLE_DISPATCHER


class GeneratorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', '')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.health_url = reverse('health-check')
        self.generate_url = reverse('generate-card')
        self.chat_url = reverse('card-chat')

    def test_unauthorized_without_api_key(self):
        """Request without API key to protected endpoint must return 403."""
        unauth_client = APIClient()
        response = unauth_client.post(self.generate_url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_health_check_endpoint(self):
        """Health check endpoint must return 200 OK without requiring authentication."""
        unauth_client = APIClient()
        response = unauth_client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("status"), "healthy")

    def test_generate_card_missing_prompt_returns_400(self):
        """Prompt-based generation requires 'prompt' field."""
        response = self.client.post(self.generate_url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('prompt', response.json())

    def test_chat_card_missing_message_returns_400(self):
        """Card studio chat requires 'message' field."""
        response = self.client.post(self.chat_url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.json())

    def test_generate_card_all_styles_render(self):
        """Verify that all 4 modern card styles render full-bleed 1200x700 PNG."""
        sample_card_data = {
            "name": "Sarah Connor",
            "designation": "Chief Technology Officer",
            "phone": "+1 (555) 019-2834",
            "email": "sarah.connor@cyberdyne.io",
            "website": "https://cyberdyne.io",
            "company_name": "Cyberdyne Systems",
            "theme": {}
        }
        for style_key in STYLE_DISPATCHER.keys():
            payload = sample_card_data.copy()
            payload['layout_style'] = style_key
            img_bytes = generate_business_card(payload)
            self.assertTrue(img_bytes.startswith(b'\x89PNG\r\n\x1a\n'))
            image = Image.open(io.BytesIO(img_bytes))
            self.assertEqual(image.size, (1200, 700))
            self.assertEqual(image.format, 'PNG')


class OpenAIKeyManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', 'card_sec_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.config_url = reverse('api-config-openai-key')

    def test_crypto_roundtrip(self):
        """Verify AES-256 Fernet encryption and decryption accurately restores key."""
        from card_project.key_manager import encrypt_key, decrypt_key
        raw_key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = encrypt_key(raw_key)

        # Ciphertext must not match raw key in any way
        self.assertNotEqual(raw_key, encrypted)
        self.assertNotIn(raw_key, encrypted)

        # Decryption must restore identical key
        decrypted = decrypt_key(encrypted)
        self.assertEqual(raw_key, decrypted)

    def test_masking_and_fingerprint(self):
        """Verify safe masking and SHA-256 fingerprint generation."""
        from card_project.key_manager import mask_key, hash_fingerprint
        raw = "sk-proj-1234567890abcdef"
        self.assertEqual(mask_key(raw), "sk-proj...cdef")
        self.assertEqual(len(hash_fingerprint(raw)), 64)

    def test_database_storage_is_encrypted_not_plaintext(self):
        """Verify that the database row never contains plaintext API key."""
        from card_project.key_manager import set_active_openai_key, get_active_openai_key
        from generator.models import OpenAIKeyConfig

        raw_test_key = "sk-proj-topsecretkeyneverleak123456"
        config = set_active_openai_key(raw_test_key)

        # Reload directly from DB
        db_record = OpenAIKeyConfig.objects.get(id=config.id)
        self.assertNotIn(raw_test_key, db_record.encrypted_key)
        self.assertTrue(db_record.encrypted_key.startswith("gAAAAA"))  # Standard Fernet header

        # get_active_openai_key decodes it on demand
        self.assertEqual(get_active_openai_key(), raw_test_key)

    def test_config_endpoint_requires_api_key(self):
        """Unauthenticated requests must be rejected with 403 Forbidden."""
        unauth_client = APIClient()
        get_res = unauth_client.get(self.config_url)
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)

        post_res = unauth_client.post(self.config_url, data={"api_key": "sk-proj-test"}, format='json')
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_config_endpoint_get_post_delete_flow(self):
        """Verify full GET, POST (update key), and DELETE (clear/revert) flow."""
        # 1. GET status
        get_res = self.client.get(self.config_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertTrue(get_res.json()["success"])

        # 2. POST update key (skip live OpenAI network call in unit test)
        new_key = "sk-proj-clientcustomrotatedkey9876543210"
        post_res = self.client.post(
            self.config_url,
            data={"api_key": new_key, "validate": False},
            format='json'
        )
        self.assertEqual(post_res.status_code, status.HTTP_200_OK)
        self.assertTrue(post_res.json()["success"])
        self.assertEqual(post_res.json()["source"], "database")
        self.assertIn("sk-proj...3210", post_res.json()["masked_key"])

        # 3. Verify get_active_openai_key reflects the newly set key
        from card_project.key_manager import get_active_openai_key
        self.assertEqual(get_active_openai_key(), new_key)

        # 4. DELETE to clear DB key and revert to environment
        del_res = self.client.delete(self.config_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertTrue(del_res.json()["success"])
        self.assertNotEqual(get_active_openai_key(), new_key)
