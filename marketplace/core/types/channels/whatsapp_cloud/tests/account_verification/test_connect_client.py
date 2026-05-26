"""Tests for the ConnectClient and ConnectService."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from marketplace.clients.connect.client import ConnectClient
from marketplace.services.connect.service import ConnectService


@override_settings(CONNECT_REST_ENDPOINT="https://connect.example.com")
class ConnectClientTestCase(TestCase):
    def setUp(self):
        with patch("marketplace.clients.connect.client.InternalAuthentication") as auth:
            auth.return_value.headers = {"Authorization": "Bearer fake"}
            self.client = ConnectClient()

    def test_notify_business_verification_posts_expected_payload(self):
        with patch.object(self.client, "make_request") as mock_request:
            mock_request.return_value.json.return_value = {"sent": True}

            result = self.client.notify_business_verification(
                user_email="customer@example.com",
                status="APPROVED",
                rejection_reasons=["NONE"],
                verification_attempts=1,
                language="pt-br",
            )

        self.assertEqual(result, {"sent": True})
        args, kwargs = mock_request.call_args
        self.assertEqual(
            args[0],
            "https://connect.example.com/v2/internals/business-verification/notify/",
        )
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(
            kwargs["json"],
            {
                "user_email": "customer@example.com",
                "status": "APPROVED",
                "rejection_reasons": ["NONE"],
                "verification_attempts": 1,
                "language": "pt-br",
            },
        )

    def test_omits_language_when_not_provided(self):
        with patch.object(self.client, "make_request") as mock_request:
            mock_request.return_value.json.return_value = {"sent": True}

            self.client.notify_business_verification(
                user_email="customer@example.com",
                status="FAILED",
            )

        payload = mock_request.call_args.kwargs["json"]
        self.assertNotIn("language", payload)
        self.assertEqual(payload["rejection_reasons"], [])
        self.assertEqual(payload["verification_attempts"], 0)

    def test_strips_trailing_slash_from_base_url(self):
        with override_settings(CONNECT_REST_ENDPOINT="https://connect.example.com/"):
            with patch(
                "marketplace.clients.connect.client.InternalAuthentication"
            ) as auth:
                auth.return_value.headers = {}
                client = ConnectClient()
        self.assertEqual(client.base_url, "https://connect.example.com")


class ConnectServiceTestCase(TestCase):
    def test_service_delegates_to_client(self):
        client = MagicMock()
        client.notify_business_verification.return_value = {"sent": True}

        service = ConnectService(client=client)
        service.notify_business_verification(
            user_email="customer@example.com",
            status="APPROVED",
            rejection_reasons=[],
            verification_attempts=1,
            language=None,
        )

        client.notify_business_verification.assert_called_once_with(
            user_email="customer@example.com",
            status="APPROVED",
            rejection_reasons=[],
            verification_attempts=1,
            language=None,
        )
