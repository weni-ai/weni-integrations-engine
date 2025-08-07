from unittest import TestCase, mock
from marketplace.core.types.channels.whatsapp_base.requests.facebook import (
    FacebookConversationAPI,
)
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)


class TestFacebookConversationAPI(TestCase):
    @mock.patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.requests.get"
    )
    def test_request_conversations(self, mock_get):
        data = {
            "data": [
                {
                    "data_points": [
                        {
                            "start": 1685847600,
                            "end": 1685934000,
                            "conversation": 5,
                            "conversation_type": "REGULAR",
                            "conversation_direction": "USER_INITIATED",
                            "conversation_category": "UNKNOWN",
                            "cost": 15.1,
                        },
                        {
                            "start": 1685847600,
                            "end": 1685934000,
                            "conversation": 1,
                            "conversation_type": "REGULAR",
                            "conversation_direction": "BUSINESS_INITIATED",
                            "conversation_category": "UNKNOWN",
                            "cost": 5.1,
                        },
                        {
                            "start": 1685847600,
                            "end": 1685934000,
                            "conversation": 2,
                            "conversation_type": "REGULAR",
                            "conversation_direction": "UNKNOWN",
                            "conversation_category": "MARKETING",
                            "cost": 253.25,
                        },
                        {
                            "start": 1685847600,
                            "end": 1685934000,
                            "conversation": 3,
                            "conversation_type": "REGULAR",
                            "conversation_direction": "UNKNOWN",
                            "conversation_category": "SERVICE",
                            "cost": 255.25,
                        },
                        {
                            "start": 1685847600,
                            "end": 1685934000,
                            "conversation": 4,
                            "conversation_type": "REGULAR",
                            "conversation_direction": "UNKNOWN",
                            "conversation_category": "SERVICE",
                            "cost": 250.25,
                        },
                    ]
                }
            ]
        }
        expected_data = {
            "user_initiated": 5,
            "business_initiated": 1,
            "total": 6,
            "templates": {"MARKETING": 2, "SERVICE": 7, "total": 9},
        }
        mock_response = mock.Mock()
        mock_response.json.return_value = {"conversation_analytics": data}

        mock_get.return_value = mock_response

        facebook_api = FacebookConversationAPI()
        conversations = facebook_api.conversations(
            access_token="test",
            end="1685934000",  # Valid timestamp
            start="1685847600",  # Valid timestamp
            waba_id="test",
        )
        self.assertEqual(conversations.__dict__(), expected_data)

    @mock.patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.requests.get"
    )
    def test_invalid_request_conversations(self, mock_get):
        mock_response = mock.Mock()
        mock_response.json.return_value = {"error": {"message": "Testing Error"}}

        mock_get.return_value = mock_response

        facebook_api = FacebookConversationAPI()
        with self.assertRaises(FacebookApiException):
            facebook_api.conversations(
                access_token="test",
                end="1685934000",  # Valid timestamp
                start="1685847600",  # Valid timestamp
                waba_id="test",
            )
