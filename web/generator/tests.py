import io
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

from generator.services.card_drawer import generate_business_card, STYLE_DISPATCHER


class GeneratorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.health_url = reverse('health-check')
        self.generate_url = reverse('generate-card')
        self.chat_url = reverse('card-chat')

    def test_health_check_endpoint(self):
        """Health check endpoint must return 200 OK and healthy status."""
        response = self.client.get(self.health_url)
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
