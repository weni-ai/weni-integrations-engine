from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime

from marketplace.wpp_templates.utils import (
    TemplateWebhookEventProcessor,
    extract_template_data,
)
from marketplace.wpp_templates.template_helpers import extract_body_example
from marketplace.wpp_templates.error_handlers import handle_error_and_update_config
from marketplace.applications.models import App


class TestTemplateWebhookEventProcessor(TestCase):
    def setUp(self):
        self.mock_app_filter = patch(
            "marketplace.wpp_templates.utils.App.objects.filter"
        ).start()
        self.mock_template_filter = patch(
            "marketplace.wpp_templates.utils.TemplateMessage.objects.filter"
        ).start()
        self.handler = MagicMock()
        self.processor = TemplateWebhookEventProcessor(handler=self.handler)
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
