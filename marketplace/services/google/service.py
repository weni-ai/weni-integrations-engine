import logging
import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class GoogleAuthService:  # pragma: no cover
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
        except requests.exceptions.HTTPError as e:
            error_message = f"Failed to exchange code for token: {str(e)}"
            try:
                # Attempt to parse the error response JSON if available
                error_details = e.response.json()
                logger.error(f"{error_message}. Details: {error_details}")
                raise Exception(
                    {"error": error_message, "details": error_details}
                ) from e
            except ValueError:
                # If the response isn't JSON, log and raise the basic error message
                logger.error(error_message)
                raise Exception(error_message) from e

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
        except requests.exceptions.HTTPError as e:
            error_message = f"Failed to refresh access token: {str(e)}"
            try:
                # Attempt to parse the error response JSON if available
                error_details = e.response.json()
                logger.error(f"{error_message}. Details: {error_details}")
                raise Exception(
                    {"error": error_message, "details": error_details}
                ) from e
            except ValueError:
                # If the response isn't JSON, log and raise the basic error message
                logger.error(error_message)
                raise Exception(error_message) from e
