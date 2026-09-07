import io
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

from generator.services.card_drawer import generate_business_card, THEMES

class BusinessCardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.generate_url = reverse('generate-card')
        self.health_url = reverse('health-check')
        self.valid_payload = {
            "name": "Sarah Connor",
            "designation": "Chief Technology Officer",
            "phone": "+1 (555) 019-2834",
            "email": "sarah.connor@cyberdyne.io",
            "website": "https://cyberdyne.io",
            "company_name": "Cyberdyne Systems",
            "theme": "midnight_gold"
        }

    def test_health_check_endpoint(self):
        """Tests that the health check endpoint returns 200 OK and healthy status."""
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("status"), "healthy")

    def test_generate_card_post_success(self):
        """Tests POST /api/generate-card/ returns a valid image/png."""
        response = self.client.post(self.generate_url, data=self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')
        
        # Verify valid PNG signature
        self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
        
        # Verify it can be opened by Pillow
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (1050, 600))
        self.assertEqual(image.format, 'PNG')

    def test_generate_card_get_success(self):
        """Tests GET /api/generate-card/ with query params returns image/png."""
        response = self.client.get(self.generate_url, data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_generate_card_missing_required_fields(self):
        """Tests validation error when required fields are missing."""
        invalid_payload = {
            "name": "Sarah Connor"
            # Missing designation, phone, email, website
        }
        response = self.client.post(self.generate_url, data=invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('designation', data)
        self.assertIn('phone', data)
        self.assertIn('email', data)
        self.assertIn('website', data)

    def test_generate_card_all_themes_render(self):
        """Tests that all defined themes generate valid images without exceptions."""
        for theme_key in THEMES.keys():
            payload = self.valid_payload.copy()
            payload['theme'] = theme_key
            img_bytes = generate_business_card(payload)
            self.assertTrue(img_bytes.startswith(b'\x89PNG\r\n\x1a\n'))
            image = Image.open(io.BytesIO(img_bytes))
            self.assertEqual(image.size, (1050, 600))
