from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, override_settings
import requests

from marketplace.services.google.service import GoogleAuthService


@override_settings(
    GOOGLE_CLIENT_ID="cid",
    GOOGLE_CLIENT_SECRET="secret",
    GOOGLE_REDIRECT_URI="https://app/callback",
)
class TestGoogleAuthService(SimpleTestCase):
    def test_exchange_code_for_token_success(self):
        with patch("marketplace.services.google.service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_post.return_value = mock_response
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
            }

            out = GoogleAuthService.exchange_code_for_token("auth-code")

            mock_post.assert_called_once()
            self.assertEqual(out["access_token"], "at")
            self.assertEqual(out["refresh_token"], "rt")

            # Validate payload keys (order not important)
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], GoogleAuthService.TOKEN_URL)
            payload = kwargs["data"]
            self.assertEqual(payload["client_id"], "cid")
            self.assertEqual(payload["client_secret"], "secret")
            self.assertEqual(payload["code"], "auth-code")
            self.assertEqual(payload["redirect_uri"], "https://app/callback")
            self.assertEqual(payload["grant_type"], "authorization_code")

    def test_exchange_code_for_token_error(self):
        with patch("marketplace.services.google.service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_post.return_value = mock_response
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "boom"
            )

            with self.assertRaises(requests.exceptions.RequestException):
                GoogleAuthService.exchange_code_for_token("auth-code")

    def test_refresh_access_token_success(self):
        with patch("marketplace.services.google.service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_post.return_value = mock_response
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"access_token": "new-at"}

            out = GoogleAuthService.refresh_access_token("ref-token")

            mock_post.assert_called_once()
            self.assertEqual(out, "new-at")

            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], GoogleAuthService.TOKEN_URL)
            payload = kwargs["data"]
            self.assertEqual(payload["client_id"], "cid")
            self.assertEqual(payload["client_secret"], "secret")
            self.assertEqual(payload["refresh_token"], "ref-token")
            self.assertEqual(payload["grant_type"], "refresh_token")

    def test_refresh_access_token_error(self):
        with patch("marketplace.services.google.service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_post.return_value = mock_response
            mock_response.raise_for_status.side_effect = requests.exceptions.Timeout(
                "timeout"
            )

            with self.assertRaises(requests.exceptions.RequestException):
                GoogleAuthService.refresh_access_token("ref-token")
