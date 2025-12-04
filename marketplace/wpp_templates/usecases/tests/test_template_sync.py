from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from marketplace.wpp_templates.usecases.template_sync import TemplateSyncUseCase


class TestTemplateSyncUseCase(SimpleTestCase):
    """Unit tests for TemplateSyncUseCase using dependency injection and instance-level mocks."""

    def _make_app(self, with_waba: bool = False):
        app = MagicMock()
        app.uuid = "app-uuid-1"
        app.flow_object_uuid = "flow-uuid-1"
        app.apptype.get_access_token.return_value = "access-token"
        app.config = (
            {"waba": {"id": "waba-in-config"}}
            if with_waba
            else {"wa_waba_id": "waba-direct"}
        )
        return app

    def test_init_access_token_error(self):
        """__init__ should log and raise when get_access_token raises ValueError."""
        app = MagicMock()
        app.uuid = "app-uuid-err"
        app.apptype.get_access_token.side_effect = ValueError("bad token")
        with self.assertRaises(ValueError):
            TemplateSyncUseCase(app)

    def test_sync_templates_error_from_service(self):
        """When Meta service returns error, handle_error_and_update_config is called and returns early."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        # Replace external services with mocks
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()
        uc.template_service.list_template_messages.return_value = {"error": {"code": 1}}

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.handle_error_and_update_config"
        ) as mock_handle:
            uc.sync_templates()
            mock_handle.assert_called_once()
            uc.flows_client.update_facebook_templates.assert_not_called()

    def test_sync_templates_success_existing_translation(self):
        """Successful sync with existing translation and all component types present."""
        app = self._make_app(with_waba=False)
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payload = {
            "id": "tpl-1",
            "name": "welcome",
            "category": "UTILITY",
            "language": "en_US",
            "status": "APPROVED",
            "components": [
                {"type": "BODY", "text": "Hello", "example": {"body_text": ["a", "b"]}},
                {"type": "FOOTER", "text": "Bye"},
                {
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": "Header",
                    "example": {"header_handle": "hdr-1"},
                },
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {"type": "URL", "text": "Open", "url": "https://x"},
                        {
                            "type": "PHONE_NUMBER",
                            "text": "Call",
                            "phone_number": "+55 9",
                        },
                    ],
                },
            ],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.extract_body_example",
            return_value=["a", "b"],
        ) as mock_extract, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ), patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateHeader"
        ) as mock_header, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateButton"
        ) as mock_button:
            # Configure get_or_create tuples
            mock_header.objects.get_or_create.return_value = (MagicMock(), True)
            mock_button.objects.get_or_create.return_value = (MagicMock(), True)
            # Existing translation branch
            existing_translation = MagicMock()
            found_template = MagicMock()
            existing_translation.template = found_template
            mock_qs = MagicMock()
            mock_qs.__bool__.return_value = True
            mock_qs.last.return_value = existing_translation
            mock_translation.objects.filter.return_value = mock_qs

            returned_translation = MagicMock()
            mock_translation.objects.get_or_create.return_value = (
                returned_translation,
                True,
            )

            uc.sync_templates()

            uc.flows_client.update_facebook_templates.assert_called_once()
            mock_extract.assert_called_once()
            # Header created
            mock_header.objects.get_or_create.assert_called()
            # Buttons created
            self.assertGreaterEqual(mock_button.objects.get_or_create.call_count, 1)
            # Translation saved
            returned_translation.save.assert_called_once()

    def test_sync_templates_success_no_existing_translation(self):
        """Successful sync creating new TemplateMessage when no translation exists."""
        app = self._make_app(with_waba=True)
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payload = {
            "id": "tpl-2",
            "name": "promo",
            "category": "MARKETING",
            "language": "es",
            "status": "PENDING",
            "components": [{"type": "BODY", "text": "Hola"}],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message:
            mock_translation.objects.filter.return_value = []
            tmpl = MagicMock()
            mock_message.objects.get_or_create.return_value = (tmpl, True)
            returned_translation = MagicMock()
            mock_translation.objects.get_or_create.return_value = (
                returned_translation,
                True,
            )

            uc.sync_templates()

            mock_message.objects.get_or_create.assert_called_once()
            returned_translation.save.assert_called_once()

    def test_sync_templates_flows_update_raises_but_continues(self):
        """Flows update exception should be logged but processing continues."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()
        uc.flows_client.update_facebook_templates.side_effect = Exception("boom")

        template_payload = {
            "id": "tpl-3",
            "name": "sale",
            "category": "UTILITY",
            "language": "en",
            "status": "APPROVED",
            "components": [],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            mock_translation.objects.filter.return_value = []
        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation2:
            mock_message.objects.get_or_create.return_value = (MagicMock(), True)
            mock_translation2.objects.filter.return_value = []
            mock_translation2.objects.get_or_create.return_value = (MagicMock(), True)

            uc.sync_templates()  # Should not raise
            mock_translation2.objects.get_or_create.assert_called_once()

    def test_sync_templates_per_item_exception_continue(self):
        """Exceptions inside per-template loop should be caught and continue."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payloads = [
            {
                "id": "tpl-bad",
                "name": "bad",
                "category": "U",
                "language": "en",
                "status": "A",
                "components": [],
            },
            {
                "id": "tpl-ok",
                "name": "ok",
                "category": "U",
                "language": "en",
                "status": "A",
                "components": [],
            },
        ]
        uc.template_service.list_template_messages.return_value = {
            "data": template_payloads
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            mock_message.objects.get_or_create.return_value = (MagicMock(), True)
            # First raises, second passes
            mock_translation.objects.filter.return_value = []
            mock_translation.objects.get_or_create.side_effect = [
                Exception("item error"),
                (MagicMock(), True),
            ]

            uc.sync_templates()  # Should not raise
            self.assertEqual(mock_translation.objects.get_or_create.call_count, 2)

    def test_delete_unexistent_translations(self):
        """Covers cleanup logic for missing translations and templates."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        # Prepare app templates
        t1 = MagicMock()
        t1.name = "t1"
        t1.translations.all().count.return_value = 1
        t2 = MagicMock()
        t2.name = "t2"
        t2.translations.all().count.return_value = 0  # Trigger delete if reached
        app.templates.all.return_value = [t1, t2]

        templates = [{"id": "keep"}]  # Only 'keep' remains on remote
        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            # For t1: no translations -> delete and continue
            mock_translation.objects.filter.side_effect = [
                [],  # For t1, falsy -> delete
                [
                    MagicMock(message_template_id="remove")
                ],  # For t2, 1 translation to delete
            ]

            uc._delete_unexistent_translations(templates)

            # t1 should be deleted due to no translations
            t1.delete.assert_called_once()
            # t2's translation should be deleted (not in 'keep')
            # We can't access the exact translation mock easily due to side_effect,
            # but ensure filter was called twice and t2 was also deleted after count==0
            self.assertEqual(mock_translation.objects.filter.call_count, 2)
            t2.delete.assert_called_once()
