import io
import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

def make_dummy_png(w=1200, h=700):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), color=(20, 20, 20)).save(buf, format='PNG')
    return buf.getvalue()


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

    def test_generate_card_missing_openai_key_returns_503(self):
        """When OpenAI API key is not configured, endpoint must return 503 error response."""
        from unittest.mock import patch
        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            response = self.client.post(self.generate_url, data={"prompt": "John Doe, Developer"}, format='json')
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(response.json().get("status"), "error")
            self.assertIn("key", response.json().get("error", "").lower())

    def test_generate_card_dalle_failure_returns_502(self):
        """When DALL-E image generation fails across all models, endpoint must return 502 error response."""
        from unittest.mock import patch
        with patch('generator.services.ai_card_drawer.generate_dalle_card', return_value=None):
            response = self.client.post(self.generate_url, data={"prompt": "Jane Doe, Tech Lead"}, format='json')
            self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
            self.assertEqual(response.json().get("status"), "error")
            self.assertIn("AI card generation failed", response.json().get("error", ""))


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


class CardAgentBugFixesTests(TestCase):
    def test_detect_style_intent_boundaries(self):
        """Bug 3: Verify English word-boundary regex prevents accidental style overrides."""
        from generator.services.card_agent import detect_style_intent

        # Substrings inside words/emails/URLs must NOT trigger style intent
        self.assertIsNone(detect_style_intent("Please email me at info@techvision.com"))
        self.assertIsNone(detect_style_intent("Company name is GoldenCorp Ltd"))
        self.assertIsNone(detect_style_intent("I work in biotechnology research"))
        self.assertIsNone(detect_style_intent("Address: Marigold Street 42"))
        self.assertIsNone(detect_style_intent("Visit our website at https://techvision.io"))

        # Explicit English style requests MUST trigger style intent
        self.assertEqual(detect_style_intent("Please make it tech style"), 'cyber_tech')
        self.assertEqual(detect_style_intent("Can we switch to cyber tech?"), 'cyber_tech')
        self.assertEqual(detect_style_intent("I need an IT style layout"), 'cyber_tech')
        self.assertEqual(detect_style_intent("Change to luxury gold design"), 'luxury_gold')
        self.assertEqual(detect_style_intent("Use gold borders"), 'luxury_gold')
        self.assertEqual(detect_style_intent("Use corner arcs layout"), 'corner_arcs')
        self.assertEqual(detect_style_intent("Apply organic waves theme"), 'organic_waves')

    def test_infer_layout_style_heuristics(self):
        """Bug 4: Verify single-shot fallback infers distinct layout styles based on profession."""
        from generator.services.ai_card_drawer import infer_layout_style

        self.assertEqual(infer_layout_style(prompt="Software Engineer at OpenAI"), 'cyber_tech')
        self.assertEqual(infer_layout_style(prompt="Python Developer and Tech Lead"), 'cyber_tech')
        self.assertEqual(infer_layout_style(prompt="Managing Director and CEO"), 'luxury_gold')
        self.assertEqual(infer_layout_style(prompt="Senior Partner at Legal Associates"), 'luxury_gold')
        self.assertEqual(infer_layout_style(prompt="Creative Director & Graphic Designer"), 'organic_waves')
        self.assertEqual(infer_layout_style(prompt="Professional Wedding Photographer"), 'organic_waves')
        self.assertEqual(infer_layout_style(prompt="Doctor at Care Medical Hospital"), 'corner_arcs')
        self.assertEqual(infer_layout_style(prompt="Architecture and Real Estate Consultant"), 'corner_arcs')

    def test_new_session_respects_gpt_chosen_style(self):
        """Bug 1: Verify process_card_agent_turn preserves GPT's layout_style on new sessions."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_gpt_state = {
            "name": "Sarah Connor",
            "designation": "AI Engineer",
            "company_name": "Cyberdyne",
            "layout_style": "cyber_tech",
            "theme": {}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=None,
                    user_message="Make a card for Sarah Connor, AI Engineer at Cyberdyne"
                )
                from generator.models import CardSession
                session = CardSession.objects.get(id=result['session_id'])
                # Must be cyber_tech, NOT overridden by round-robin
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')

    def test_existing_session_preserves_design_on_text_edits(self):
        """Bug 3 regression: Editing text with 'techvision' or 'goldencorp' must not alter style."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Bruce Wayne",
                "designation": "Chairman",
                "layout_style": "luxury_gold",
                "theme": {"bg_card": [13, 15, 20]}
            },
            version=1
        )

        mock_updated_state = {
            "name": "Bruce Wayne",
            "designation": "Chairman",
            "company_name": "TechVision BD",
            "email": "bruce@goldencorp.com",
            "layout_style": "luxury_gold",
            "theme": {"bg_card": [13, 15, 20]}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated card.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="Update company to TechVision BD and email to bruce@goldencorp.com"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['layout_style'], 'luxury_gold')

    def test_rollback_restores_previous_style(self):
        """Ensure rollback flow correctly restores earlier version style."""
        from unittest.mock import patch
        from generator.models import CardSession, CardMessage
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Alice",
                "layout_style": "corner_arcs",
                "theme": {"bg_card": [26, 32, 38]}
            },
            version=2
        )
        # Record v1 message with cyber_tech
        CardMessage.objects.create(
            session=session,
            role='assistant',
            content='Initial card',
            card_data={"name": "Alice", "layout_style": "cyber_tech", "theme": {"bg_card": [10, 16, 28]}},
            version=1
        )

        mock_updated_state = {
            "name": "Alice",
            "layout_style": "corner_arcs",
            "theme": {"bg_card": [26, 32, 38]}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reverted.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="restore previous design"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')

    def test_user_prompt_returned_in_responses(self):
        """Verify user_prompt is returned in process_card_agent_turn and X-User-Prompt in generate-card."""
        import urllib.parse
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        test_msg = "Create a modern visiting card for John Doe"
        mock_state = {"name": "John Doe", "layout_style": "cyber_tech"}

        # 1. Verify process_card_agent_turn returns user_prompt
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message=test_msg)
                self.assertIn("user_prompt", res)
                self.assertEqual(res["user_prompt"], test_msg)

        # 2. Verify CardChatAPIView response contains user_prompt
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                chat_res = client.post(chat_url, data={"message": test_msg}, format='json')
                self.assertEqual(chat_res.status_code, status.HTTP_200_OK)
                self.assertIn("user_prompt", chat_res.json())
                self.assertEqual(chat_res.json()["user_prompt"], test_msg)

        # 3. Verify GenerateCardAPIView response has X-User-Prompt header
        generate_url = reverse('generate-card')
        prompt_text = "Visiting card for Alice Smith at TechCorp"
        with patch('generator.services.ai_card_drawer.generate_dalle_card', return_value=make_dummy_png()):
            gen_res = client.post(generate_url, data={"prompt": prompt_text}, format='json')
            self.assertEqual(gen_res.status_code, status.HTTP_200_OK)
            self.assertIn('X-User-Prompt', gen_res.headers)
            decoded_header = urllib.parse.unquote(gen_res.headers['X-User-Prompt'])
            self.assertEqual(decoded_header, prompt_text)

    def test_card_chat_missing_openai_key_returns_503(self):
        """When OpenAI API key is missing during chat turn, returns 503."""
        from unittest.mock import patch
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            res = client.post(chat_url, data={"message": "Make a card"}, format='json')
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(res.json().get("status"), "error")

    def test_card_chat_dalle_failure_returns_502(self):
        """When DALL-E image generation fails during chat turn, returns 502."""
        from unittest.mock import patch
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        mock_state = {"name": "Test User", "layout_style": "cyber_tech"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reasoned", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=None):
                res = client.post(chat_url, data={"message": "Make a card"}, format='json')
                self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)
                self.assertEqual(res.json().get("status"), "error")
                self.assertIn("AI card generation failed", res.json().get("error", ""))

    def test_build_precision_dalle_prompt_layout_style_and_theme(self):
        """Verify build_precision_dalle_prompt incorporates layout style description and theme RGBs."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt, LAYOUT_STYLE_DESCRIPTIONS

        spec = {
            "name": "Sarah Connor",
            "designation": "CTO",
            "company_name": "Cyberdyne",
            "layout_style": "cyber_tech",
            "theme": {
                "bg_card": [10, 16, 28],
                "accent": [0, 229, 255],
                "accent_secondary": [56, 189, 248]
            }
        }
        prompt = build_precision_dalle_prompt(spec)
        self.assertIn(LAYOUT_STYLE_DESCRIPTIONS['cyber_tech'], prompt)
        self.assertIn("RGB(10, 16, 28)", prompt)
        self.assertIn("RGB(0, 229, 255)", prompt)
        self.assertIn("RGB(56, 189, 248)", prompt)

        # Fallback when layout_style is not present
        spec_no_style = {
            "name": "John Doe",
            "style_description": "Custom vintage style"
        }
        prompt_fallback = build_precision_dalle_prompt(spec_no_style)
        self.assertIn("Custom vintage style", prompt_fallback)

    def test_color_intent_updates_theme(self):
        """Verify explicit color request preserves GPT's updated theme instead of reverting to current_state."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Alice",
                "layout_style": "organic_waves",
                "theme": {"bg_card": [22, 37, 54], "accent": [245, 166, 35]}
            },
            version=1
        )

        red_theme = {"bg_card": [180, 20, 20], "accent": [255, 215, 0], "accent_secondary": [220, 50, 50]}
        mock_updated_state = {
            "name": "Alice",
            "layout_style": "organic_waves",
            "theme": red_theme
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Changed background to red.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="change background to red"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['theme']['bg_card'], [180, 20, 20])

    def test_phone_number_mandate_in_dalle_prompt(self):
        """Verify prompt contains strict character-by-character mandate for phone number."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        phone_num = "0183774747467463"
        spec = {
            "name": "Bob",
            "phone": phone_num,
            "layout_style": "cyber_tech"
        }
        prompt = build_precision_dalle_prompt(spec)
        self.assertIn(f"CRITICAL PHONE NUMBER MANDATE: render the phone number EXACTLY as '{phone_num}'", prompt)
        self.assertIn("Double-check every single digit matches", prompt)

    def test_note_included_in_responses(self):
        """Verify note is present in chat JSON and X-AI-Note header in generate-card."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_state = {"name": "Test User", "layout_style": "cyber_tech"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card please")
                self.assertIn("note", res)
                self.assertIn("manually verified", res["note"])

        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        generate_url = reverse('generate-card')

        with patch('generator.services.ai_card_drawer.generate_dalle_card', return_value=make_dummy_png()):
            gen_res = client.post(generate_url, data={"prompt": "Visiting card for Bob"}, format='json')
            self.assertEqual(gen_res.status_code, status.HTTP_200_OK)
            self.assertIn('X-AI-Note', gen_res.headers)
            self.assertIn("manually verified", gen_res.headers['X-AI-Note'])

    def test_detect_color_intent_precision(self):
        """Verify detect_color_intent only triggers on genuine color instructions, not text containing color words."""
        from generator.services.card_agent import detect_color_intent

        # Genuine color instructions -> True
        self.assertTrue(detect_color_intent("change background to red"))
        self.assertTrue(detect_color_intent("change background to red, keep same layout style"))
        self.assertTrue(detect_color_intent("make it red"))
        self.assertTrue(detect_color_intent("turn it blue"))
        self.assertTrue(detect_color_intent("red background"))
        self.assertTrue(detect_color_intent("accent color green"))
        self.assertTrue(detect_color_intent("dark theme please"))
        self.assertTrue(detect_color_intent("switch color to cyan"))

        # Text edits containing color names as proper nouns or fields -> False
        self.assertFalse(detect_color_intent("add my company name Red Horizon Solutions"))
        self.assertFalse(detect_color_intent("my name is Scarlett Johansson"))
        self.assertFalse(detect_color_intent("company is Blackrock Ltd"))
        self.assertFalse(detect_color_intent("email is john@greenpeace.org"))
        self.assertFalse(detect_color_intent("designation: Light Rail Architect"))
        self.assertFalse(detect_color_intent("Golden Gate Software Inc"))

    def test_company_name_with_color_word_does_not_break_design_stability(self):
        """Verify adding company 'Red Horizon Solutions' does not trigger color intent and preserves layout/theme."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession

        initial_theme = {'bg_card': [26, 32, 38], 'accent': [245, 95, 30], 'accent_secondary': [210, 70, 20]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Mamun Or Rashid',
                'designation': 'Senior Software Engineer',
                'layout_style': 'corner_arcs',
                'theme': initial_theme
            },
            version=1
        )

        # Mock GPT hallucinating cyber_tech and cyan theme on tech company name
        hallucinated_gpt_state = {
            'name': 'Mamun Or Rashid',
            'designation': 'Senior Software Engineer',
            'company_name': 'Red Horizon Solutions',
            'layout_style': 'cyber_tech',
            'theme': {'bg_card': [10, 16, 28], 'accent': [0, 229, 255]}
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Added company.", hallucinated_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="add my company name Red Horizon Solutions"
                )
                session.refresh_from_db()
                # Deterministic override MUST preserve corner_arcs and initial_theme
                self.assertEqual(session.current_state['layout_style'], 'corner_arcs')
                self.assertEqual(session.current_state['theme'], initial_theme)
                self.assertEqual(session.current_state['company_name'], 'Red Horizon Solutions')

    def test_repeated_text_only_edits_keep_design_strictly_stable(self):
        """Verify consecutive text-only edits preserve layout_style and theme across multiple turns."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession

        initial_theme = {'bg_card': [22, 37, 54], 'accent': [245, 166, 35], 'accent_secondary': [217, 83, 47]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Original Name',
                'layout_style': 'organic_waves',
                'theme': initial_theme
            },
            version=1
        )

        turns = [
            ("change name to Dr. Strange", {"name": "Dr. Strange", "layout_style": "cyber_tech", "theme": {"bg_card": [0, 0, 0]}}),
            ("add phone 0183774747467463", {"name": "Dr. Strange", "phone": "0183774747467463", "layout_style": "luxury_gold", "theme": {"bg_card": [99, 99, 99]}}),
            ("add address Banani, Dhaka", {"name": "Dr. Strange", "address": "Banani, Dhaka", "layout_style": "corner_arcs", "theme": {"bg_card": [50, 50, 50]}}),
        ]

        with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
            for user_msg, mock_returned_state in turns:
                with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated", mock_returned_state)):
                    process_card_agent_turn(session_id=str(session.id), user_message=user_msg)
                    session.refresh_from_db()
                    # Layout and theme MUST remain organic_waves and initial_theme across all turns
                    self.assertEqual(session.current_state['layout_style'], 'organic_waves')
                    self.assertEqual(session.current_state['theme'], initial_theme)

    def test_image_returned_as_base64_without_saving_to_disk(self):
        """Verify generated card image is returned as base64 without saving files to media directory."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession, CardMessage

        mock_state = {"name": "Alice in Wonderland", "layout_style": "corner_arcs"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for Alice")
                self.assertIn("image_base64", res)
                self.assertTrue(res["image_base64"].startswith("data:image/png;base64,"))
                self.assertEqual(res["image_url"], res["image_base64"])

                # Check that CardMessage stores base64 string
                msg = CardMessage.objects.filter(session_id=res["session_id"]).order_by('-created_at').first()
                self.assertIsNotNone(msg)
                self.assertTrue(msg.image_base64.startswith("data:image/png;base64,"))

    def test_card_data_returned_in_chat_response(self):
        """Verify card_data dictionary is included directly in the chat response and history."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_state = {
            "name": "Bruce Wayne",
            "designation": "Chairman",
            "company_name": "Wayne Enterprises",
            "layout_style": "luxury_gold"
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for Bruce")
                self.assertIn("card_data", res)
                self.assertEqual(res["card_data"]["name"], "Bruce Wayne")
                self.assertEqual(res["card_data"]["company_name"], "Wayne Enterprises")
                self.assertEqual(res["card_data"]["layout_style"], "luxury_gold")

    def test_multiple_phones_and_emails_as_array(self):
        """Verify phone and email support multiple items in array format across card_data and prompt."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        multiple_state = {
            "name": "Dr. Mamun",
            "phone": ["+880 1837000000", "+880 1700111222"],
            "email": ["mamun@techvision.com", "info@mamun.dev"],
            "layout_style": "cyber_tech"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", multiple_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card with 2 phones and 2 emails")
                card_data = res["card_data"]

                # Check phone is list
                self.assertIsInstance(card_data["phone"], list)
                self.assertEqual(len(card_data["phone"]), 2)
                self.assertIn("+880 1837000000", card_data["phone"])
                self.assertIn("+880 1700111222", card_data["phone"])

                # Check email is list
                self.assertIsInstance(card_data["email"], list)
                self.assertEqual(len(card_data["email"]), 2)
                self.assertIn("mamun@techvision.com", card_data["email"])
                self.assertIn("info@mamun.dev", card_data["email"])

                # Check prompt contains both phones and emails
                prompt = build_precision_dalle_prompt(card_data)
                self.assertIn("+880 1837000000", prompt)
                self.assertIn("+880 1700111222", prompt)
                self.assertIn("mamun@techvision.com", prompt)
                self.assertIn("info@mamun.dev", prompt)

    def test_comma_separated_contacts_normalized_to_array(self):
        """Verify string inputs with multiple comma-separated contacts are cleanly normalized to arrays."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        string_contacts_state = {
            "name": "John Doe",
            "phone": "01837747474, 01711223344",
            "email": "john@doe.com, john.work@corp.io",
            "layout_style": "corner_arcs"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", string_contacts_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for John")
                card_data = res["card_data"]
                self.assertEqual(card_data["phone"], ["01837747474", "01711223344"])
                self.assertEqual(card_data["email"], ["john@doe.com", "john.work@corp.io"])

    def test_single_shot_multiple_contacts_generation(self):
        """Verify single-shot generate_hybrid_business_card extracts and formats multiple contacts as lists."""
        from unittest.mock import patch
        from generator.services.ai_card_drawer import generate_hybrid_business_card

        mock_spec = {
            "name": "Jane Doe",
            "phone": ["01837747474", "01711223344"],
            "email": ["jane@work.com", "jane@personal.com"],
            "layout_style": "cyber_tech"
        }
        with patch('generator.services.ai_card_drawer.analyze_and_design_card', return_value=mock_spec):
            with patch('generator.services.ai_card_drawer.generate_dalle_card', return_value=make_dummy_png()):
                with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test'):
                    img_bytes, card_data = generate_hybrid_business_card("Jane Doe with 2 phones and 2 emails")
                    self.assertIsInstance(card_data["phone"], list)
                    self.assertEqual(card_data["phone"], ["01837747474", "01711223344"])
                    self.assertIsInstance(card_data["email"], list)
                    self.assertEqual(card_data["email"], ["jane@work.com", "jane@personal.com"])

    def test_comprehensive_visiting_card_fields_json(self):
        """Verify all possible visiting card data fields exist in JSON response and prompt."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        full_doctor_card = {
            "name": "Dr. Sarah Connor",
            "designation": "Chief Cardiac Surgeon & Professor",
            "department": "Department of Cardiology",
            "qualifications": ["MBBS (DMC)", "FCPS (Surgery)", "FRCS (Glasgow)"],
            "company_name": "Apollo Heart Institute",
            "tagline": "Excellence in Cardiovascular Care",
            "phone": ["+880 1812345678", "+880 1798765432"],
            "email": ["dr.sarah@apolloheart.org", "sarah.personal@med.com"],
            "website": ["https://apolloheart.org", "https://drsarahconnor.med"],
            "address": "Plot 15, Road 71, Gulshan-2",
            "branch": "Main Hospital Campus",
            "city": "Dhaka",
            "postal_code": "1212",
            "country": "Bangladesh",
            "schedule": "Saturday to Wednesday: 5:00 PM - 9:00 PM",
            "services": ["Bypass Surgery", "Angioplasty", "Valve Replacement"],
            "social_links": {
                "linkedin": "https://linkedin.com/in/drsarah",
                "github": "",
                "twitter": "@drsarahconnor",
                "facebook": "https://facebook.com/drsarah.cardiac",
                "instagram": "",
                "youtube": "https://youtube.com/@drsarahconnor"
            },
            "layout_style": "luxury_gold"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created full profile card", full_doctor_card)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Create full doctor card")
                data = res["card_data"]

                # 1. Identity & Credentials
                self.assertEqual(data["name"], "Dr. Sarah Connor")
                self.assertEqual(data["designation"], "Chief Cardiac Surgeon & Professor")
                self.assertEqual(data["department"], "Department of Cardiology")
                self.assertEqual(data["qualifications"], ["MBBS (DMC)", "FCPS (Surgery)", "FRCS (Glasgow)"])
                self.assertEqual(data["monogram"], "DS")

                # 2. Organization & Slogan
                self.assertEqual(data["company_name"], "Apollo Heart Institute")
                self.assertEqual(data["tagline"], "Excellence in Cardiovascular Care")

                # 3. Multi-value Contacts
                self.assertEqual(data["phone"], ["+880 1812345678", "+880 1798765432"])
                self.assertEqual(data["phones"], ["+880 1812345678", "+880 1798765432"])
                self.assertEqual(data["email"], ["dr.sarah@apolloheart.org", "sarah.personal@med.com"])
                self.assertEqual(data["emails"], ["dr.sarah@apolloheart.org", "sarah.personal@med.com"])
                self.assertEqual(data["website"], "https://apolloheart.org")
                self.assertEqual(data["websites"], ["https://apolloheart.org", "https://drsarahconnor.med"])

                # 4. Location & Address
                self.assertEqual(data["address"], "Plot 15, Road 71, Gulshan-2")
                self.assertEqual(data["branch"], "Main Hospital Campus")
                self.assertEqual(data["city"], "Dhaka")
                self.assertEqual(data["postal_code"], "1212")
                self.assertEqual(data["country"], "Bangladesh")

                # 5. Operational Details & Services
                self.assertEqual(data["schedule"], "Saturday to Wednesday: 5:00 PM - 9:00 PM")
                self.assertEqual(data["services"], ["Bypass Surgery", "Angioplasty", "Valve Replacement"])

                # 6. Social Profiles
                self.assertIn("linkedin", data["social_links"])
                self.assertEqual(data["social_links"]["linkedin"], "https://linkedin.com/in/drsarah")
                self.assertEqual(data["linkedin"], "https://linkedin.com/in/drsarah")
                self.assertEqual(data["twitter"], "@drsarahconnor")

                # 7. Verify DALL-E prompt synthesis includes all fields
                prompt = build_precision_dalle_prompt(data)
                self.assertIn("Dr. Sarah Connor", prompt)
                self.assertIn("Chief Cardiac Surgeon & Professor", prompt)
                self.assertIn("MBBS (DMC)", prompt)
                self.assertIn("Excellence in Cardiovascular Care", prompt)
                self.assertIn("Apollo Heart Institute", prompt)
                self.assertIn("+880 1812345678", prompt)
                self.assertIn("dr.sarah@apolloheart.org", prompt)
                self.assertIn("https://apolloheart.org", prompt)
                self.assertIn("Saturday to Wednesday", prompt)
                self.assertIn("Bypass Surgery", prompt)


class OpenAINotificationTests(TestCase):
    """
    Tests for the OpenAI error notification webhook:
    POST https://server.milo22.cloud/api/notifications/openai-notification
    X-API-KEY: notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a
    Body: {"message": "..."}
    """
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', '')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.chat_url = reverse('card-chat')

    def test_notification_service_payload_and_headers(self):
        """send_openai_error_notification must deliver the correct URL, headers, and body."""
        from unittest.mock import patch
        from card_project.notifications import send_openai_error_notification

        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            test_error = "OpenAI API rate limit exceeded: quota 429"
            send_openai_error_notification(test_error, async_send=False)

            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://server.milo22.cloud/api/notifications/openai-notification")
            self.assertEqual(kwargs['headers']['X-API-KEY'], "notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a")
            self.assertEqual(kwargs['json']['message'], test_error)

    def test_card_chat_missing_openai_key_triggers_notification(self):
        """When OpenAI API key is missing during chat, notification webhook must be triggered."""
        from unittest.mock import patch

        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            with patch('generator.views.send_openai_error_notification') as mock_notify_view, \
                 patch('generator.services.card_agent.send_openai_error_notification') as mock_notify_agent:
                response = self.client.post(self.chat_url, data={"message": "Create a modern visiting card"}, format='json')
                self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
                self.assertTrue(mock_notify_view.called or mock_notify_agent.called)

    def test_card_chat_openai_error_triggers_notification(self):
        """When OpenAI API fails (e.g. 429 Insufficient Quota), notification webhook must be triggered."""
        from unittest.mock import patch

        with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test-valid-key'):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=None):
                with patch('generator.services.card_agent.send_openai_error_notification') as mock_notify_agent, \
                     patch('generator.views.send_openai_error_notification') as mock_notify_view:
                    response = self.client.post(self.chat_url, data={"message": "Visiting card for Alice"}, format='json')
                    self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
                    self.assertTrue(mock_notify_agent.called or mock_notify_view.called)

    def test_notification_network_failure_is_resilient(self):
        """Even if webhook endpoint fails or times out, the notification service does not crash."""
        from unittest.mock import patch
        import requests
        from card_project.notifications import send_openai_error_notification

        with patch('requests.post', side_effect=requests.exceptions.ConnectTimeout("Connection timed out")):
            result = send_openai_error_notification("Some OpenAI error", async_send=False)
            self.assertFalse(result)




