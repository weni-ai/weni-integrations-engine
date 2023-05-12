from django.test import TestCase
from django.core.exceptions import ValidationError

from marketplace.core.validators import validate_app_code_exists
from marketplace.core.validators import validate_generic_app_code_exists

from unittest.mock import patch
from unittest.mock import Mock


class ValidateAppCodeExistsTestCase(TestCase):
    @patch("marketplace.connect.client.ConnectProjectClient.detail_channel_type")
    def test_invalid_app_code(self, mock_list_detail_channel_type):
        response_data = None
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 404
        mock_list_detail_channel_type.return_value = mock_response

        value = "wrong"
        with self.assertRaisesMessage(
            ValidationError, f"AppType ({value}) not exists!"
        ):
            validate_app_code_exists(value)

    def test_valid_app_code(self):
        value = "wwc"
        validate_app_code_exists(value)

    @patch("marketplace.connect.client.ConnectProjectClient.detail_channel_type")
    def test_valid_generic_app_code(self, mock_list_detail_channel_type):
        response_data = {
            "attributes": {
                "code": "TWT",
                "category": {"name": "SOCIAL_MEDIA", "value": 2},
                "teste": "true",
            }
        }
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_detail_channel_type.return_value = mock_response

        value = "TWT"
        result = validate_generic_app_code_exists(value)
        self.assertTrue(result)
