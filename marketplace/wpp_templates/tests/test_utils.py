from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime

from marketplace.wpp_templates.utils import WebhookEventProcessor, extract_template_data
from marketplace.wpp_templates.error_handlers import handle_error_and_update_config
from marketplace.applications.models import App


class TestWebhookEventProcessor(TestCase):
    def setUp(self):
        self.mock_app_filter = patch(
            "marketplace.wpp_templates.utils.App.objects.filter"
        ).start()
        self.mock_template_filter = patch(
            "marketplace.wpp_templates.utils.TemplateMessage.objects.filter"
        ).start()
        self.handler = MagicMock()
        self.processor = WebhookEventProcessor(handler=self.handler)
        self.addCleanup(patch.stopall)

    def test_process_template_status_update_no_apps(self):
        self.mock_app_filter.return_value.exists.return_value = False
        self.processor.process_template_status_update("123", {}, {})
        self.handler.handle.assert_not_called()

    def test_process_template_status_update_with_apps(self):
        mock_app = MagicMock()
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]

        mock_template = MagicMock()
        mock_translation = MagicMock()
        mock_template.translations.filter.return_value = [mock_translation]
        self.mock_template_filter.return_value.first.return_value = mock_template

        self.processor.process_template_status_update(
            "123",
            {
                "event": "APPROVED",
                "message_template_name": "t",
                "message_template_language": "pt_BR",
                "message_template_id": "1",
            },
            {},
        )

        self.handler.handle.assert_called_once()

    def test_skips_if_template_is_none(self):
        mock_app = MagicMock()
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]
        self.mock_template_filter.return_value.first.return_value = None

        self.processor.process_template_status_update(
            "123",
            {
                "event": "APPROVED",
                "message_template_name": "missing",
                "message_template_language": "pt_BR",
                "message_template_id": "1",
            },
            {},
        )
        self.handler.handle.assert_not_called()

    def test_unexpected_error_logs(self):
        mock_app = MagicMock()
        mock_app.uuid = "123"
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]
        self.mock_template_filter.side_effect = Exception("Fail")

        self.processor.logger = MagicMock()
        self.processor.process_template_status_update(
            "123",
            {
                "event": "APPROVED",
                "message_template_name": "t",
                "message_template_language": "pt_BR",
                "message_template_id": "1",
            },
            {},
        )
        self.processor.logger.error.assert_called_once()

    def test_process_event_delegates_correctly(self):
        self.processor.process_template_status_update = MagicMock()
        self.processor.process_event(
            "waba", {"event": "APPROVED"}, "message_template_status_update", {}
        )
        self.processor.process_template_status_update.assert_called_once()


class TestExtractTemplateData(TestCase):
    def setUp(self):
        self.translation = MagicMock()
        self.translation.template.name = "Template Name"
        self.translation.language = "en"
        self.translation.status = "active"
        self.translation.category = "generic"
        self.translation.message_template_id = 123

    def test_extract_template_data_all_components(self):
        header = MagicMock(header_type="IMAGE", example="['example1']", text="Header")
        self.translation.headers.all.return_value = [header]
        self.translation.body = "Hello"
        self.translation.footer = "Bye"
        button = MagicMock(
            button_type="URL", text="Visit", url="http://x.com", phone_number=None
        )
        self.translation.buttons.all.return_value = [button]

        result = extract_template_data(self.translation)
        self.assertEqual(result["name"], "Template Name")
        self.assertIn("HEADER", [c["type"] for c in result["components"]])
        self.assertIn("BODY", [c["type"] for c in result["components"]])
        self.assertIn("FOOTER", [c["type"] for c in result["components"]])
        self.assertIn("BUTTONS", [c["type"] for c in result["components"]])

    def test_invalid_header_example(self):
        header = MagicMock(header_type="IMAGE", example="not a list", text="Header")
        self.translation.headers.all.return_value = [header]
        result = extract_template_data(self.translation)
        self.assertIn("not a list", result["components"][0]["example"]["header_handle"])

    def test_button_with_phone_number(self):
        button = MagicMock(
            button_type="CALL",
            text="Call",
            url=None,
            phone_number="123456789",
            country_code="55",
        )
        self.translation.buttons.all.return_value = [button]
        result = extract_template_data(self.translation)
        btn = result["components"][-1]["buttons"][0]
        self.assertEqual(btn["phone_number"], "+55 123456789")

    def test_header_with_missing_text_and_example(self):
        header = MagicMock(header_type="TEXT", text=None, example=None)
        self.translation.headers.all.return_value = [header]
        self.translation.body = None
        self.translation.footer = None
        self.translation.buttons.all.return_value = []
        result = extract_template_data(self.translation)
        self.assertEqual(result["components"][0]["text"], "No text provided")

    def test_header_text_with_example(self):
        header = MagicMock(header_type="TEXT", text="Title", example="Example Text")
        self.translation.headers.all.return_value = [header]
        self.translation.body = None
        self.translation.footer = None
        self.translation.buttons.all.return_value = []

        result = extract_template_data(self.translation)
        self.assertEqual(
            result["components"][0]["example"]["header_text"], ["Example Text"]
        )


class TestHandleErrorAndUpdateConfig(TestCase):
    def setUp(self):
        self.app = MagicMock(spec=App)
        self.app.config = {}
        self.app.uuid = "123"
        self.error_data = {
            "code": 100,
            "error_subcode": 33,
            "message": "Error occurred",
        }

    @patch("marketplace.applications.models.App.save")
    @patch("marketplace.wpp_templates.error_handlers.datetime")
    def test_handle_error_and_update_config_correct_condition(
        self, mock_datetime, mock_save
    ):
        mock_datetime.now.return_value = datetime(2024, 1, 1)
        handle_error_and_update_config(self.app, self.error_data)
        self.assertIn("ignores_meta_sync", self.app.config)

    @patch("marketplace.applications.models.App.save")
    def test_handle_error_and_update_config_incorrect_condition(self, mock_save):
        self.error_data["code"] = 101
        handle_error_and_update_config(self.app, self.error_data)
        mock_save.assert_not_called()
