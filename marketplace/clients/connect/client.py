"""HTTP client for the Connect (weni-engine) internal REST API."""

from typing import Any, Dict, Iterable, Optional

from django.conf import settings

from marketplace.clients.base import InternalAuthentication, RequestClient
from marketplace.interfaces.connect.interfaces import ConnectClientInterface


class ConnectClient(RequestClient, ConnectClientInterface):
    """Client for service-to-service calls against Connect's `/v2/internals/`."""

    def __init__(self):
        self.base_url = settings.CONNECT_REST_ENDPOINT.rstrip("/")
        self.authentication_instance = InternalAuthentication()

    def notify_business_verification(
        self,
        user_email: str,
        status: str,
        rejection_reasons: Optional[Iterable[str]] = None,
        verification_attempts: int = 0,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/v2/internals/business-verification/notify/"
        payload: Dict[str, Any] = {
            "user_email": user_email,
            "status": status,
            "rejection_reasons": list(rejection_reasons or []),
            "verification_attempts": verification_attempts,
        }
        if language:
            payload["language"] = language

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=payload,
        )
        return response.json()
