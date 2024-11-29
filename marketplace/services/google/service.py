import logging
import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class GoogleAuthService:
    """
    Service for handling Google authentication, exchanging authorization code for access token,
    and refreshing the access token when necessary.
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"

    @staticmethod
    def exchange_code_for_token(code):
        """
        Exchanges the provided authorization code for an access token and refresh token.
        """
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(GoogleAuthService.TOKEN_URL, data=payload)
            response.raise_for_status()  # Raise an error for bad HTTP status codes
            tokens = response.json()
            logger.info("Successfully exchanged authorization code for tokens.")
            return {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to exchange code for token: {str(e)}")
            raise

    @staticmethod
    def refresh_access_token(refresh_token):
        """
        Refreshes the access token using the provided refresh token.
        """
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            response = requests.post(GoogleAuthService.TOKEN_URL, data=payload)
            response.raise_for_status()
            tokens = response.json()
            logger.info("Successfully refreshed access token.")
            return tokens.get("access_token")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {str(e)}")
            raise
