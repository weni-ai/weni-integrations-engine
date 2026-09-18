import uuid
from copy import deepcopy
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase

from marketplace.wpp_templates.utils import (
    TemplateCategoryChangeHandler,
    TemplateStatusUpdateHandler,
    TemplateWebhookEventProcessor,
    extract_template_data,
)
from marketplace.wpp_templates.template_helpers import extract_body_example
from marketplace.wpp_templates.error_handlers import handle_error_and_update_config
from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    PARAMETER_FORMAT_NAMED,
    PARAMETER_FORMAT_POSITIONAL,
    TemplateMessage,
    TemplateTranslation,
)


class TestTemplateWebhookEventProcessor(TestCase):
    def setUp(self):
        self.mock_app_filter = patch(
            "marketplace.wpp_templates.utils.App.objects.filter"
        ).start()
        self.mock_template_filter = patch(
            "marketplace.wpp_templates.utils.TemplateMessage.objects.filter"
        ).start()
        self.status_update_handler = MagicMock()
        self.category_change_handler = MagicMock()
        self.flows_service = MagicMock()
        self.processor = TemplateWebhookEventProcessor(
            status_update_handler=self.status_update_handler,
            category_change_handler=self.category_change_handler,
            flows_service=self.flows_service,
        )
        self.addCleanup(patch.stopall)

    def test_process_template_status_update_no_apps(self):
        self.mock_app_filter.return_value.exists.return_value = False
        self.processor.process_template_status_update("123", {}, {})
        self.status_update_handler.handle.assert_not_called()

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

        self.status_update_handler.handle.assert_called_once()

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
        self.status_update_handler.handle.assert_not_called()

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

    def test_process_template_category_change_no_apps(self):
        self.mock_app_filter.return_value.exists.return_value = False

        self.processor.process_template_category_change(
            "waba-1",
            {
                "message_template_name": "order_confirmation",
                "category": "UTILITY",
                "correct_category": "MARKETING",
            },
        )

        self.category_change_handler.handle.assert_not_called()

    def test_process_template_category_change_delegates_per_app(self):
        app_one = MagicMock()
        app_two = MagicMock()

        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [app_one, app_two]

        value = {
            "message_template_name": "order_confirmation",
            "category": "UTILITY",
            "correct_category": "MARKETING",
        }
        self.processor.process_template_category_change("waba-1", value)

        self.assertEqual(self.category_change_handler.handle.call_count, 2)
        self.category_change_handler.handle.assert_any_call(app=app_one, value=value)
        self.category_change_handler.handle.assert_any_call(app=app_two, value=value)

    def test_process_event_routes_template_correct_category_detection(self):
        self.processor.process_template_category_change = MagicMock()

        self.processor.process_event(
            "waba-1",
            {
                "message_template_name": "order_confirmation",
                "category": "UTILITY",
                "correct_category": "MARKETING",
            },
            "template_correct_category_detection",
            {},
        )

        self.processor.process_template_category_change.assert_called_once_with(
            "waba-1",
            {
                "message_template_name": "order_confirmation",
                "category": "UTILITY",
                "correct_category": "MARKETING",
            },
        )

    def test_process_event_routes_template_category_update(self):
        self.processor.process_template_category_update = MagicMock()

        value = {
            "message_template_name": "promo",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        self.processor.process_event(
            "waba-1", value, "template_category_update", {"entry": []}
        )

        self.processor.process_template_category_update.assert_called_once_with(
            "waba-1", value, {"entry": []}
        )

    def test_process_template_category_update_skips_impending(self):
        self.processor.logger = MagicMock()

        value = {
            "message_template_name": "promo",
            "correct_category": "MARKETING",
            "new_category": "UTILITY",
            "category_update_timestamp": 1746169200,
        }
        self.processor.process_template_category_update("waba-1", value, {})

        self.mock_app_filter.return_value.exists.assert_not_called()
        self.processor.logger.info.assert_called()

    def test_process_template_category_update_no_apps(self):
        self.mock_app_filter.return_value.exists.return_value = False

        value = {
            "message_template_name": "promo",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        self.processor.process_template_category_update("waba-1", value, {})

        self.mock_template_filter.assert_not_called()

    @patch("marketplace.wpp_templates.utils.extract_template_data")
    def test_process_template_category_update_updates_and_notifies(self, mock_extract):
        mock_extract.return_value = {"mocked": "data"}
        mock_app = MagicMock()
        mock_app.uuid = "app-uuid-1"
        mock_app.flow_object_uuid = "flow-uuid-1"
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]

        mock_template = MagicMock()
        mock_template.name = "promo"
        mock_translation = MagicMock()
        mock_template.translations.all.return_value = [mock_translation]
        self.mock_template_filter.return_value.first.return_value = mock_template

        value = {
            "message_template_name": "promo",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        webhook = {"entry": [{"changes": []}]}
        self.processor.process_template_category_update("waba-1", value, webhook)

        self.assertEqual(mock_template.category, "MARKETING")
        mock_template.save.assert_called_once()
        self.flows_service.update_facebook_templates_webhook.assert_called_once_with(
            flow_object_uuid="flow-uuid-1",
            template_data={"mocked": "data"},
            template_name="promo",
            webhook=webhook,
        )

    @patch("marketplace.wpp_templates.utils.extract_template_data")
    def test_process_template_category_update_logs_flows_error_on_webhook_failure(
        self, mock_extract
    ):
        mock_extract.return_value = {"mocked": "data"}
        mock_app = MagicMock()
        mock_app.uuid = "app-uuid-1"
        mock_app.flow_object_uuid = "flow-uuid-1"
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]

        mock_template = MagicMock()
        mock_template.name = "promo"
        mock_translation = MagicMock()
        mock_translation.language = "en_US"
        mock_template.translations.all.return_value = [mock_translation]
        self.mock_template_filter.return_value.first.return_value = mock_template

        self.flows_service.update_facebook_templates_webhook.side_effect = Exception(
            "flows down"
        )
        self.processor.logger = MagicMock()

        value = {
            "message_template_name": "promo",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        self.processor.process_template_category_update("waba-1", value, {"entry": []})

        self.processor.logger.error.assert_called_once_with(
            "[Flows] Failed to send category update for promo/en_US: flows down"
        )
        mock_template.save.assert_called_once()

    def test_process_template_category_update_skips_missing_template(self):
        mock_app = MagicMock()
        mock_app.uuid = "app-uuid-1"
        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [mock_app]
        self.mock_template_filter.return_value.first.return_value = None

        value = {
            "message_template_name": "missing",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        self.processor.process_template_category_update("waba-1", value, {})

        self.flows_service.update_facebook_templates_webhook.assert_not_called()

    @patch("marketplace.wpp_templates.utils.extract_template_data")
    def test_process_template_category_update_error_does_not_stop_others(
        self, mock_extract
    ):
        mock_extract.return_value = {"mocked": "data"}
        app_one = MagicMock()
        app_one.uuid = "app-1"
        app_one.flow_object_uuid = "flow-1"
        app_two = MagicMock()
        app_two.uuid = "app-2"
        app_two.flow_object_uuid = "flow-2"

        self.mock_app_filter.return_value.exists.return_value = True
        self.mock_app_filter.return_value.__iter__.return_value = [app_one, app_two]

        template_one = MagicMock()
        template_one.name = "promo"
        template_one.translations.all.side_effect = Exception("DB error")

        template_two = MagicMock()
        template_two.name = "promo"
        mock_translation = MagicMock()
        template_two.translations.all.return_value = [mock_translation]

        self.mock_template_filter.return_value.first.side_effect = [
            template_one,
            template_two,
        ]

        self.processor.logger = MagicMock()
        value = {
            "message_template_name": "promo",
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }
        self.processor.process_template_category_update("waba-1", value, {"entry": []})

        self.processor.logger.error.assert_called_once()
        self.flows_service.update_facebook_templates_webhook.assert_called_once()


class TestTemplateCategoryChangeHandler(TestCase):
    def setUp(self):
        self.commerce_service = MagicMock()
        self.handler = TemplateCategoryChangeHandler(
            commerce_service=self.commerce_service
        )
        self.app = MagicMock()
        self.app.uuid = "app-uuid-1"
        self.app.project_uuid = "proj-uuid-1"
        self.value = {
            "message_template_name": "order_confirmation",
            "category": "UTILITY",
            "correct_category": "MARKETING",
        }

    def test_handle_sends_payload_to_commerce(self):
        self.handler.handle(app=self.app, value=self.value)

        self.commerce_service.send_template_category_notification.assert_called_once_with(
            {
                "project_uuid": "proj-uuid-1",
                "app_uuid": "app-uuid-1",
                "template_name": "order_confirmation",
                "template_category": "UTILITY",
                "template_correct_category": "MARKETING",
            }
        )

    def test_handle_logs_and_does_not_raise_on_commerce_error(self):
        self.commerce_service.send_template_category_notification.side_effect = (
            Exception("commerce down")
        )
        self.handler.logger = MagicMock()

        self.handler.handle(app=self.app, value=self.value)

        self.handler.logger.error.assert_called_once()


class TestExtractTemplateData(TestCase):
    def setUp(self):
        self.translation = MagicMock()
        self.translation.template.name = "Template Name"
        self.translation.template.category = "generic"
        self.translation.language = "en"
        self.translation.status = "active"
        self.translation.message_template_id = 123
        self.translation.parameter_format = None
        self.translation.body_named_params = []
        self.translation.parameter_anomaly = None
        self.translation.body = None
        self.translation.footer = None
        self.translation.headers.all.return_value = []
        self.translation.buttons.all.return_value = []

    def _payload_keys_without_format(self):
        return {"name", "components", "language", "status", "category", "id"}

    def _body_component(self, payload):
        return next(
            component
            for component in payload["components"]
            if component["type"] == "BODY"
        )

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

    def test_clean_named_translation_emits_format_and_named_examples(self):
        named_params = [
            {"param_name": "nome", "example": "João"},
            {"param_name": "cota", "example": "3/12"},
        ]
        self.translation.parameter_format = PARAMETER_FORMAT_NAMED
        self.translation.body_named_params = named_params
        self.translation.parameter_anomaly = None
        self.translation.body = "Olá {{nome}}, sua cota {{cota}}"

        result = extract_template_data(self.translation)
        body = self._body_component(result)

        self.assertEqual(result["parameter_format"], PARAMETER_FORMAT_NAMED)
        self.assertEqual(body["text"], "Olá {{nome}}, sua cota {{cota}}")
        self.assertEqual(
            body["example"]["body_text_named_params"],
            named_params,
        )
        self.assertIs(body["example"]["body_text_named_params"], named_params)
        self.assertEqual(result["name"], "Template Name")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["category"], "generic")
        self.assertEqual(result["id"], "123")

    def test_anomalous_named_translation_omits_example_block(self):
        self.translation.parameter_format = PARAMETER_FORMAT_NAMED
        self.translation.body_named_params = [
            {"param_name": "nome", "example": "João"},
            {"param_name": "cota", "example": None},
        ]
        self.translation.parameter_anomaly = {
            "type": "BODY_EXAMPLE_NAME_MISMATCH",
            "body_param_names": ["nome", "cota"],
            "example_param_names": ["nome", "quota"],
        }
        self.translation.body = "Olá {{nome}}, sua cota {{cota}}"

        result = extract_template_data(self.translation)
        body = self._body_component(result)

        self.assertEqual(result["parameter_format"], PARAMETER_FORMAT_NAMED)
        self.assertNotIn("example", body)

    def test_positional_translation_gains_only_parameter_format(self):
        self.translation.parameter_format = PARAMETER_FORMAT_POSITIONAL
        self.translation.body_named_params = []
        self.translation.parameter_anomaly = None
        self.translation.body = "Olá {{1}}, seu pedido {{2}} foi enviado."
        self.translation.body_example = ["João", "12345"]

        result = extract_template_data(self.translation)
        body = self._body_component(result)

        self.assertEqual(result["parameter_format"], PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(body, {"type": "BODY", "text": self.translation.body})
        self.assertNotIn("example", body)
        self.assertEqual(
            self._payload_keys_without_format() | {"parameter_format"},
            set(result),
        )

    def test_null_format_omits_parameter_format_key(self):
        self.translation.parameter_format = None
        self.translation.body = "Olá, tudo bem?"

        result = extract_template_data(self.translation)

        self.assertNotIn("parameter_format", result)
        self.assertEqual(set(result), self._payload_keys_without_format())
        self.assertEqual(result["name"], "Template Name")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["category"], "generic")
        self.assertEqual(result["id"], "123")


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


class TestExtractBodyExample(TestCase):
    """
    Test cases for the extract_body_example utility function.

    This class tests both scenarios:
    1. Serializer scenario (user input data)
    2. Meta API scenario (API response data)
    """

    def test_serializer_scenario_single_example(self):
        """
        Test the serializer scenario with single example values.

        This simulates the data structure that comes from the serializer
        when a user creates a template with body examples.
        """
        # Simulating serializer input data
        serializer_data = {"body_text": [["12345", "#123abc", "29 08 2025"]]}

        result = extract_body_example(serializer_data)
        expected = ["12345", "#123abc", "29 08 2025"]

        self.assertEqual(result, expected)

    def test_meta_api_scenario_single_example(self):
        """
        Test the Meta API scenario with single example values.

        This simulates the data structure that comes from Meta's API
        when fetching templates.
        """
        # Simulating Meta API response data
        meta_api_data = {"body_text": [["sarah", "123456798", "Herman miller"]]}

        result = extract_body_example(meta_api_data)
        expected = ["sarah", "123456798", "Herman miller"]

        self.assertEqual(result, expected)

    def test_multiple_example_groups(self):
        """
        Test scenario with multiple example groups.

        When there are multiple example groups, the function should
        take the first inner list.
        """
        data_with_multiple_groups = {
            "body_text": [["first", "group", "values"], ["second", "group", "values"]]
        }

        result = extract_body_example(data_with_multiple_groups)
        expected = ["first", "group", "values"]

        self.assertEqual(result, expected)

    def test_simple_list_values(self):
        """
        Test scenario where values are not nested lists.

        When the values are a simple list (not list of lists),
        the function should extend the entire list.
        """
        simple_list_data = {"body_text": ["simple", "list", "values"]}

        result = extract_body_example(simple_list_data)
        expected = ["simple", "list", "values"]

        self.assertEqual(result, expected)

    def test_non_list_values(self):
        """
        Test scenario where values are not lists.

        When the values are not lists (strings, numbers, etc.),
        the function should append them individually.
        """
        non_list_data = {"body_text": "single_string_value"}

        result = extract_body_example(non_list_data)
        expected = ["single_string_value"]

        self.assertEqual(result, expected)

    def test_empty_data(self):
        """
        Test scenario with empty or None data.

        When the input data is empty or None, the function should
        return an empty list.
        """
        # Test with empty dict
        result_empty = extract_body_example({})
        self.assertEqual(result_empty, [])

        # Test with None
        result_none = extract_body_example(None)
        self.assertEqual(result_none, [])

    def test_mixed_data_types(self):
        """
        Test scenario with mixed data types in the same structure.

        This tests the robustness of the function with various
        data type combinations.
        """
        mixed_data = {"body_text": [["string_value", 12345, "another_string"]]}

        result = extract_body_example(mixed_data)
        expected = ["string_value", 12345, "another_string"]

        self.assertEqual(result, expected)

    def test_real_world_example_from_user(self):
        """
        Test with the exact example provided by the user.

        This test uses the exact data structure from the user's example
        to ensure the function works correctly in real scenarios.
        """
        # This simulates the data that would produce the user's expected result
        user_example_data = {"body_text": [["12345", "#123abc", "29 08 2025"]]}

        result = extract_body_example(user_example_data)
        expected = ["12345", "#123abc", "29 08 2025"]

        self.assertEqual(result, expected)

        # Verify the result matches the user's expected output format
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIn("12345", result)
        self.assertIn("#123abc", result)
        self.assertIn("29 08 2025", result)

    def test_consistency_between_scenarios(self):
        """
        Test that both serializer and Meta API scenarios produce consistent results.

        This test ensures that regardless of the data source, the function
        produces the same output format.
        """
        # Serializer scenario data
        serializer_data = {"body_text": [["test", "values", "here"]]}

        # Meta API scenario data (same structure, different source)
        meta_api_data = {"body_text": [["test", "values", "here"]]}

        serializer_result = extract_body_example(serializer_data)
        meta_api_result = extract_body_example(meta_api_data)

        # Both should produce identical results
        self.assertEqual(serializer_result, meta_api_result)
        self.assertEqual(serializer_result, ["test", "values", "here"])
        self.assertEqual(meta_api_result, ["test", "values", "here"])

    def test_parameter_order_preservation(self):
        """
        Test that parameter order is preserved exactly as received.

        This is critical for WhatsApp templates since parameters are replaced
        by position ({{1}}, {{2}}, {{3}}, etc.). The order must be maintained
        to ensure correct template rendering.
        """
        # Test with specific order that matches WhatsApp template parameters
        ordered_data = {"body_text": [["12345", "#123abc", "29 08 2025"]]}

        result = extract_body_example(ordered_data)
        expected = ["12345", "#123abc", "29 08 2025"]

        # Verify exact order preservation
        self.assertEqual(result, expected)

        # Verify each position individually
        self.assertEqual(result[0], "12345")  # {{1}} should be "12345"
        self.assertEqual(result[1], "#123abc")  # {{2}} should be "#123abc"
        self.assertEqual(result[2], "29 08 2025")  # {{3}} should be "29 08 2025"

        # Test with different order to ensure it's preserved
        different_order_data = {"body_text": [["last", "first", "middle"]]}

        different_result = extract_body_example(different_order_data)
        expected_different = ["last", "first", "middle"]

        self.assertEqual(different_result, expected_different)
        self.assertEqual(different_result[0], "last")  # {{1}} should be "last"
        self.assertEqual(different_result[1], "first")  # {{2}} should be "first"
        self.assertEqual(different_result[2], "middle")  # {{3}} should be "middle"

    def test_parameter_order_with_meta_api_response(self):
        """
        Test parameter order preservation with Meta API response format.

        This ensures that when Meta returns template data, the parameter order
        is maintained exactly as it appears in the API response.
        """
        # Simulating Meta API response with specific parameter order
        meta_response_data = {"body_text": [["sarah", "123456798", "Herman miller"]]}

        result = extract_body_example(meta_response_data)
        expected = ["sarah", "123456798", "Herman miller"]

        # Verify exact order preservation from Meta API
        self.assertEqual(result, expected)

        # Verify each parameter position matches template variables
        self.assertEqual(result[0], "sarah")  # {{1}} should be "sarah"
        self.assertEqual(result[1], "123456798")  # {{2}} should be "123456798"
        self.assertEqual(result[2], "Herman miller")  # {{3}} should be "Herman miller"

        # Test that the order is not accidentally reversed or shuffled
        self.assertNotEqual(result, ["Herman miller", "123456798", "sarah"])
        self.assertNotEqual(result, ["123456798", "sarah", "Herman miller"])

    def test_parameter_order_with_multiple_groups(self):
        """
        Test parameter order preservation when multiple example groups exist.

        When there are multiple example groups, the function should preserve
        the order of the first group exactly as received.
        """
        # Multiple groups - should take first group and preserve its order
        multiple_groups_data = {
            "body_text": [
                ["first_param", "second_param", "third_param"],
                ["different", "order", "here"],
            ]
        }

        result = extract_body_example(multiple_groups_data)
        expected = ["first_param", "second_param", "third_param"]

        # Verify exact order preservation from first group
        self.assertEqual(result, expected)

        # Verify each position individually
        self.assertEqual(result[0], "first_param")  # {{1}} should be "first_param"
        self.assertEqual(result[1], "second_param")  # {{2}} should be "second_param"
        self.assertEqual(result[2], "third_param")  # {{3}} should be "third_param"

        # Ensure it didn't take from the second group
        self.assertNotEqual(result, ["different", "order", "here"])

    def test_named_example_keys_are_skipped(self):
        result = extract_body_example(
            {
                "body_text_named_params": [
                    {"param_name": "nome", "example": "João"},
                    {"param_name": "cota", "example": "3/12"},
                ]
            }
        )
        self.assertEqual(result, [])

    def test_header_text_named_params_are_skipped(self):
        result = extract_body_example(
            {"header_text_named_params": [{"param_name": "titulo", "example": "Promo"}]}
        )
        self.assertEqual(result, [])

    def test_positional_examples_kept_when_named_keys_are_present(self):
        result = extract_body_example(
            {
                "body_text": [["João", "12345"]],
                "body_text_named_params": [
                    {"param_name": "nome", "example": "João"},
                ],
                "header_text_named_params": [
                    {"param_name": "titulo", "example": "Promo"}
                ],
            }
        )
        self.assertEqual(result, ["João", "12345"])

    def test_unknown_keys_are_still_extracted(self):
        result = extract_body_example({"custom_examples": ["alpha", "beta"]})
        self.assertEqual(result, ["alpha", "beta"])

    def test_existing_positional_payloads_are_unchanged(self):
        cases = (
            (
                {"body_text": [["12345", "#123abc", "29 08 2025"]]},
                ["12345", "#123abc", "29 08 2025"],
            ),
            (
                {"body_text": [["sarah", "123456798", "Herman miller"]]},
                ["sarah", "123456798", "Herman miller"],
            ),
            ({"body_text": ["simple", "list", "values"]}, ["simple", "list", "values"]),
            ({"body_text": "single_string_value"}, ["single_string_value"]),
        )
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(extract_body_example(payload), expected)


User = get_user_model()

WABA_ID = "waba-shared"
NAMED_TEMPLATE_NAME = "cota_aviso"
NAMED_BODY = "Olá {{nome}}, sua cota {{cota}}"
NAMED_LANGUAGE = "pt_BR"
NAMED_MESSAGE_TEMPLATE_ID = "1001"
NAMED_PARAMS = [
    {"param_name": "nome", "example": "João"},
    {"param_name": "cota", "example": "3/12"},
]


class TemplateWebhookParameterPreservationTestCase(DjangoTestCase):
    def setUp(self):
        self.flows_service = MagicMock()
        self.commerce_service = MagicMock()
        self.status_use_case = MagicMock()
        self.status_update_handler = TemplateStatusUpdateHandler(
            flows_service=self.flows_service,
            commerce_service=self.commerce_service,
            status_use_case_factory=lambda app: self.status_use_case,
        )
        self.processor = TemplateWebhookEventProcessor(
            status_update_handler=self.status_update_handler,
            category_change_handler=TemplateCategoryChangeHandler(
                commerce_service=self.commerce_service
            ),
            flows_service=self.flows_service,
        )

    def _create_app(self, config, code="wpp-cloud"):
        return App.objects.create(
            config=config,
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code=code,
            created_by=User.objects.get_admin_user(),
            flow_object_uuid=uuid.uuid4(),
        )

    def _create_named_translation(
        self,
        app,
        name=NAMED_TEMPLATE_NAME,
        anomaly=None,
        parameter_format=PARAMETER_FORMAT_NAMED,
        body=NAMED_BODY,
        body_named_params=None,
        variable_count=2,
        message_template_id=NAMED_MESSAGE_TEMPLATE_ID,
    ):
        template = TemplateMessage.objects.create(
            name=name,
            app=app,
            category="UTILITY",
            template_type="TEXT",
            created_by=User.objects.get_admin_user(),
        )
        translation = TemplateTranslation.objects.create(
            template=template,
            status="PENDING",
            body=body,
            language=NAMED_LANGUAGE,
            country="BR",
            variable_count=variable_count,
            message_template_id=message_template_id,
            parameter_format=parameter_format,
            body_named_params=list(
                NAMED_PARAMS if body_named_params is None else body_named_params
            ),
            parameter_anomaly=deepcopy(anomaly),
        )
        return template, translation

    def _snapshot(self, translation):
        translation.refresh_from_db()
        return (
            translation.parameter_format,
            deepcopy(translation.body_named_params),
            deepcopy(translation.parameter_anomaly),
        )

    def _status_value(self, event="APPROVED"):
        return {
            "event": event,
            "message_template_name": NAMED_TEMPLATE_NAME,
            "message_template_language": NAMED_LANGUAGE,
            "message_template_id": NAMED_MESSAGE_TEMPLATE_ID,
        }

    def _category_update_value(self):
        return {
            "message_template_name": NAMED_TEMPLATE_NAME,
            "previous_category": "UTILITY",
            "new_category": "MARKETING",
        }

    def _assert_named_template_data(self, template_data, translation):
        self.assertEqual(template_data["parameter_format"], PARAMETER_FORMAT_NAMED)
        body = next(
            component
            for component in template_data["components"]
            if component["type"] == "BODY"
        )
        self.assertEqual(
            body["example"]["body_text_named_params"],
            translation.body_named_params,
        )

    def test_status_update_preserves_named_params_and_posts_template_data(self):
        app = self._create_app({"wa_waba_id": WABA_ID})
        _, translation = self._create_named_translation(app)
        before = self._snapshot(translation)

        self.processor.process_event(
            WABA_ID, self._status_value(), "message_template_status_update", {}
        )

        self.assertEqual(self._snapshot(translation), before)
        self.flows_service.update_facebook_templates_webhook.assert_called_once()
        template_data = (
            self.flows_service.update_facebook_templates_webhook.call_args.kwargs[
                "template_data"
            ]
        )
        translation.refresh_from_db()
        self._assert_named_template_data(template_data, translation)

    def test_category_update_preserves_named_params_and_posts_template_data(self):
        app = self._create_app({"wa_waba_id": WABA_ID})
        _, translation = self._create_named_translation(app)
        before = self._snapshot(translation)

        self.processor.process_event(
            WABA_ID, self._category_update_value(), "template_category_update", {}
        )

        self.assertEqual(self._snapshot(translation), before)
        self.flows_service.update_facebook_templates_webhook.assert_called_once()
        template_data = (
            self.flows_service.update_facebook_templates_webhook.call_args.kwargs[
                "template_data"
            ]
        )
        translation.refresh_from_db()
        self._assert_named_template_data(template_data, translation)

    def test_correct_category_detection_does_not_call_flows(self):
        app = self._create_app({"wa_waba_id": WABA_ID})
        _, translation = self._create_named_translation(app)
        before = self._snapshot(translation)

        self.processor.process_event(
            WABA_ID,
            {
                "message_template_name": NAMED_TEMPLATE_NAME,
                "category": "UTILITY",
                "correct_category": "MARKETING",
            },
            "template_correct_category_detection",
            {},
        )

        self.assertEqual(self._snapshot(translation), before)
        self.flows_service.update_facebook_templates_webhook.assert_not_called()
        self.commerce_service.send_template_category_notification.assert_called_once()

    def test_status_update_posts_positional_format_without_body_example(self):
        app = self._create_app({"wa_waba_id": WABA_ID})
        _, translation = self._create_named_translation(
            app,
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
            body="Olá {{1}}, seu pedido {{2}} foi enviado.",
            body_named_params=[],
            variable_count=0,
        )
        translation.body_example = ["João", "12345"]
        translation.save(update_fields=["body_example"])
        before = self._snapshot(translation)

        self.processor.process_event(
            WABA_ID, self._status_value(), "message_template_status_update", {}
        )

        self.assertEqual(self._snapshot(translation), before)
        template_data = (
            self.flows_service.update_facebook_templates_webhook.call_args.kwargs[
                "template_data"
            ]
        )
        body = next(
            component
            for component in template_data["components"]
            if component["type"] == "BODY"
        )
        self.assertEqual(template_data["parameter_format"], PARAMETER_FORMAT_POSITIONAL)
        self.assertNotIn("example", body)

    def test_nested_waba_id_app_receives_status_update(self):
        cloud_app = self._create_app({"wa_waba_id": WABA_ID})
        onprem_app = self._create_app(
            {"waba": {"id": WABA_ID}, "fb_access_token": "token"},
            code="wpp",
        )
        self._create_named_translation(cloud_app)
        self._create_named_translation(onprem_app)

        self.processor.process_event(
            WABA_ID, self._status_value(), "message_template_status_update", {}
        )

        self.assertEqual(
            self.flows_service.update_facebook_templates_webhook.call_count, 2
        )
        posted_uuids = {
            call.kwargs["flow_object_uuid"]
            for call in self.flows_service.update_facebook_templates_webhook.call_args_list
        }
        self.assertEqual(
            posted_uuids,
            {str(cloud_app.flow_object_uuid), str(onprem_app.flow_object_uuid)},
        )
