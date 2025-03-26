from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase
from django.db.models.query import QuerySet

from marketplace.wpp_templates.utils import WebhookEventProcessor
from marketplace.wpp_templates.utils import extract_template_data
from marketplace.applications.models import App
from marketplace.wpp_templates.error_handlers import handle_error_and_update_config


class TestWebhookEventProcessor(TestCase):
    @patch("marketplace.applications.models.App.objects.filter")
    def test_process_template_status_update_no_apps(self, mock_filter):
        mock_query_set = MagicMock(spec=QuerySet)
        mock_query_set.exists.return_value = False
        mock_filter.return_value = mock_query_set

        WebhookEventProcessor.process_template_status_update("123", {}, {})
        mock_filter.assert_called_once_with(config__wa_waba_id="123")

    @patch(
        "marketplace.services.flows.service.FlowsService.update_facebook_templates_webhook"
    )
    @patch("marketplace.wpp_templates.utils.extract_template_data")
    @patch("marketplace.wpp_templates.models.TemplateMessage.objects.filter")
    @patch("marketplace.applications.models.App.objects.filter")
    def test_process_template_status_update_with_apps(
        self, mock_filter, mock_template_filter, mock_extract_data, mock_flows_service
    ):
        mock_query_set = MagicMock(spec=QuerySet)
        mock_query_set.exists.return_value = True
        mock_app = MagicMock()
        mock_app.flow_object_uuid = "uuid123"
        mock_query_set.__iter__.return_value = iter([mock_app])
        mock_filter.return_value = mock_query_set

        mock_template = MagicMock()
        mock_translation = MagicMock()
        mock_translation.status = "pending"
        mock_template.translations.filter.return_value = [mock_translation]
        mock_template_filter.return_value.first.return_value = mock_template

        mock_extract_data.return_value = {"data": "value"}

        WebhookEventProcessor.process_template_status_update(
            "123",
            {"event": "approved", "message_template_name": "template1"},
            "webhook_data",
        )
        self.assertEqual(mock_translation.status, "approved")
        mock_flows_service.assert_called_once()

    @patch("marketplace.wpp_templates.utils.logger")
    @patch("marketplace.wpp_templates.utils.WebhookEventProcessor.get_apps_by_waba_id")
    def test_status_already_updated(self, mock_get_apps_by_waba_id, mock_logger):
        mock_query_set = MagicMock()
        mock_query_set.exists.return_value = True
        app = MagicMock()
        app.uuid = "123"
        mock_query_set.__iter__.return_value = iter([app])
        mock_get_apps_by_waba_id.return_value = mock_query_set

        translation = MagicMock()
        translation.status = "updated"
        mock_translation_query = MagicMock()
        mock_translation_query.filter.return_value = [translation]

        # Mock TemplateMessage.objects.filter
        with patch(
            "marketplace.wpp_templates.models.TemplateMessage.objects.filter",
            return_value=MagicMock(
                first=MagicMock(
                    return_value=MagicMock(translations=mock_translation_query)
                )
            ),
        ):
            value = {
                "event": "updated",
                "message_template_name": "test",
                "message_template_language": "pt_BR",
                "message_template_id": "123456789",
            }
            WebhookEventProcessor.process_template_status_update(
                "123456789",
                value,
                {"webhook": "webhook_info"},
            )
        mock_logger.info.assert_called_with(
            "The template status: updated is already updated for this App: 123"
        )

    @patch("marketplace.wpp_templates.utils.logger")
    @patch("marketplace.wpp_templates.utils.WebhookEventProcessor.get_apps_by_waba_id")
    def test_unexpected_error_during_processing(
        self, mock_get_apps_by_waba_id, mock_logger
    ):
        mock_app = MagicMock()
        mock_app.uuid = "123"
        mock_query_set = MagicMock(spec=QuerySet)
        mock_query_set.exists.return_value = True
        mock_query_set.__iter__.return_value = iter([mock_app])
        mock_get_apps_by_waba_id.return_value = mock_query_set

        with patch(
            "marketplace.wpp_templates.models.TemplateMessage.objects.filter",
            side_effect=Exception("Test error"),
        ):
            value = {
                "event": "APPROVE",
                "message_template_name": "test",
                "message_template_language": "pt_BR",
                "message_template_id": "123456789",
            }
            WebhookEventProcessor.process_template_status_update(
                "123456789", value, {"webhook": "webhook_info"}
            )

        mock_logger.error.assert_called_with(
            f"Unexpected error processing template status update by webhook for App {mock_app.uuid}: Test error"
        )

    @patch(
        "marketplace.wpp_templates.utils.WebhookEventProcessor.process_template_status_update"
    )
    def test_process_event_calls_correct_method(
        self, mock_process_template_status_update
    ):
        WebhookEventProcessor.process_event(
            "waba_id", {"some": "data"}, "message_template_status_update", "webhook"
        )
        mock_process_template_status_update.assert_called_once_with(
            "waba_id", {"some": "data"}, "webhook"
        )
        WebhookEventProcessor.process_event(
            "waba_id", {"some": "data"}, "template_category_update", "webhook"
        )
        WebhookEventProcessor.process_event(
            "waba_id", {"some": "data"}, "message_template_quality_update", "webhook"
        )
        mock_process_template_status_update.assert_called_once()

    @patch("marketplace.wpp_templates.utils.logger")
    @patch(
        "marketplace.wpp_templates.utils.FlowsService.update_facebook_templates_webhook"
    )
    @patch("marketplace.wpp_templates.utils.WebhookEventProcessor.get_apps_by_waba_id")
    def test_error_sending_template_update(
        self,
        mock_get_apps_by_waba_id,
        mock_update_facebook_templates_webhook,
        mock_logger,
    ):
        mock_query_set = MagicMock()
        mock_query_set.exists.return_value = True
        app = MagicMock()
        app.uuid = "123"
        app.flow_object_uuid = "flow_uuid"
        mock_query_set.__iter__.return_value = iter([app])
        mock_get_apps_by_waba_id.return_value = mock_query_set

        translation = MagicMock()
        translation.status = "pending"
        translation.language = "pt_BR"
        translation.message_template_id = "123456789"

        template = MagicMock()
        template.name = "test_template"
        translation.template = template

        mock_translation_queryset = MagicMock()
        mock_translation_queryset.__iter__.return_value = iter([translation])
        template.translations.filter.return_value = mock_translation_queryset

        with patch(
            "marketplace.wpp_templates.models.TemplateMessage.objects.filter",
            return_value=MagicMock(first=lambda: template),
        ):
            mock_update_facebook_templates_webhook.side_effect = Exception(
                "Test flow service failure"
            )

            value = {
                "event": "APPROVE",
                "message_template_name": "test_template",
                "message_template_language": "pt_BR",
                "message_template_id": "123456789",
            }
            WebhookEventProcessor.process_template_status_update(
                "123456789", value, {"webhook": "webhook_info"}
            )
        expected_message = (
            "Fail to sends template update: test_template, translation: pt_BR,"
            "translation ID: 123456789. Error: Test flow service failure"
        )
        mock_logger.error.assert_called_with(expected_message)


class TestExtractTemplateData(TestCase):
    def setUp(self):
        self.translation = MagicMock()
        self.translation.template.name = "Template Name"
        self.translation.language = "en"
        self.translation.status = "active"
        self.translation.category = "generic"
        self.translation.message_template_id = 123

    def test_extract_template_data_all_components(self):
        # Mock Headers
        header_mock = MagicMock()
        header_mock.header_type = "IMAGE"
        header_mock.example = "['example1', 'example2']"
        header_mock.text = "Header Text"
        self.translation.headers.all.return_value = [header_mock]

        # Mock Body
        self.translation.body = "Sample body text"

        # Mock Footer
        self.translation.footer = "Sample footer text"

        # Mock Buttons
        button_mock = MagicMock()
        button_mock.button_type = "URL"
        button_mock.text = "Visit"
        button_mock.url = "http://example.com"
        button_mock.phone_number = None
        self.translation.buttons.all.return_value = [button_mock]

        result = extract_template_data(self.translation)

        self.assertIn(
            "HEADER", [component["type"] for component in result["components"]]
        )
        self.assertIn("BODY", [component["type"] for component in result["components"]])
        self.assertIn(
            "FOOTER", [component["type"] for component in result["components"]]
        )
        self.assertIn(
            "BUTTONS", [component["type"] for component in result["components"]]
        )
        self.assertEqual(result["name"], "Template Name")
        self.assertEqual(result["language"], "en")

    def test_extract_template_data_with_invalid_header_example(self):
        header_mock = MagicMock()
        header_mock.header_type = "IMAGE"
        header_mock.example = "not a list"
        header_mock.text = "Header Text"
        self.translation.headers.all.return_value = [header_mock]

        result = extract_template_data(self.translation)

        self.assertIn("not a list", result["components"][0]["example"]["header_handle"])

    def test_header_with_text_type(self):
        header_mock = MagicMock()
        header_mock.header_type = "TEXT"
        header_mock.text = "Header Text"
        header_mock.example = None
        self.translation.headers.all.return_value = [header_mock]

        result = extract_template_data(self.translation)
        self.assertEqual(result["components"][0]["text"], "Header Text")

    def test_header_with_example(self):
        header_mock = MagicMock()
        header_mock.header_type = "TEXT"
        header_mock.text = "Header Text"
        header_mock.example = "Example Text"
        self.translation.headers.all.return_value = [header_mock]

        result = extract_template_data(self.translation)
        self.assertIn("Example Text", result["components"][0]["example"]["header_text"])

    def test_button_with_phone_number(self):
        button_mock = MagicMock()
        button_mock.button_type = "CALL"
        button_mock.text = "Call Us"
        button_mock.url = None
        button_mock.phone_number = "1234567890"
        button_mock.country_code = "1"
        self.translation.buttons.all.return_value = [button_mock]

        result = extract_template_data(self.translation)

        buttons_index = next(
            i
            for i, comp in enumerate(result["components"])
            if comp["type"] == "BUTTONS"
        )
        self.assertEqual(
            result["components"][buttons_index]["buttons"][0]["phone_number"],
            "+1 1234567890",
        )

    def test_header_example_not_list(self):
        header_mock = MagicMock()
        header_mock.header_type = "IMAGE"
        header_mock.example = "'single element'"
        self.translation.headers.all.return_value = [header_mock]

        result = extract_template_data(self.translation)

        self.assertIn(
            "'single element'", result["components"][0]["example"]["header_handle"]
        )


class TestHandleErrorAndUpdateConfig(TestCase):
    @patch("marketplace.wpp_templates.utils.logger")
    def setUp(self, mock_logger):
        self.app = MagicMock(spec=App)
        self.app.config = {}
        self.app.uuid = "123-abc"

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
        iso_date = mock_datetime.now.return_value.isoformat()

        handle_error_and_update_config(self.app, self.error_data)

        expected_config = {
            "ignores_meta_sync": {
                "last_error_date": iso_date,
                "last_error_message": "Error occurred",
                "code": 100,
                "error_subcode": 33,
            }
        }

        self.assertEqual(self.app.config, expected_config)

    @patch("marketplace.applications.models.App.save")
    def test_handle_error_and_update_config_incorrect_condition(self, mock_save):
        self.error_data["code"] = 101

        handle_error_and_update_config(self.app, self.error_data)

        self.assertEqual(self.app.config, {})
        mock_save.assert_not_called()
