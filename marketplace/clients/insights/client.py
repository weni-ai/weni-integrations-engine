"""
Client for connection with insights API.
This module provides a client to interact with the insights service.
"""

from typing import Dict, Any
from django.conf import settings

from marketplace.clients.base import RequestClient, InternalAuthentication
from marketplace.interfaces.insights.interfaces import InsightsClientInterface


class InsightsClient(RequestClient, InsightsClientInterface):
    """
    Client for interacting with the Insights API.

    This class provides methods to make requests to the Insights API,
    such as creating WhatsApp integrations.
    """

    def __init__(self) -> None:
        """
        Initialize the InsightsClient with base URL and authentication.

        Sets up the base URL from settings and creates an authentication instance.
        """
        self.base_url = settings.INSIGHTS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def create_whatsapp_integration(
        self, whatsapp_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a WhatsApp integration with the provided data.

        Args:
            whatsapp_data (Dict[str, Any]): The WhatsApp integration data.

        Returns:
            Dict[str, Any]: The response from the insights API.
        """
        url = f"{self.base_url}/v1/metrics/meta/internal/whatsapp-integration/"
        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=whatsapp_data,
        )
        return response

    def delete_whatsapp_integration(self, project_uuid: str, waba_id: str) -> None:
        """
        Delete a WhatsApp integration.

        Args:
            project_uuid (UUID): The UUID of the project.
            waba_id (str): The Waba's id.
        """
        url = f"{self.base_url}/v1/metrics/meta/internal/whatsapp-integration/"
        data = {"project_uuid": project_uuid, "waba_id": waba_id}
        response = self.make_request(
            url,
            method="DELETE",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def get_template_metrics(self, params: dict, payload: dict) -> dict:
        """
        Performs a POST request to the Insights API to retrieve metrics
        for the provided WhatsApp message templates within a time range.

        Args:
            params (dict): Query parameters sent in the URL.
                Expected keys:
                    - "waba_id" (str): WhatsApp Business Account ID.
                    - "start_date" (str): ISO 8601 datetime UTC, e.g. "2025-06-12T00:00:00+00:00".
                    - "end_date" (str): ISO 8601 datetime UTC, e.g. "2025-06-13T23:59:59+00:00".

            payload (dict): Request body sent as JSON.
                Expected keys:
                    - "template_ids" (List[str]): List of message_template_id strings.

        Returns:
            dict: Parsed JSON response from the Insights API.

        Raises:
            CustomAPIException: If the request fails (HTTP 4xx/5xx or connection error).
        """
        url = f"{self.base_url}/v1/metrics/meta/internal/whatsapp-message-templates/messages-analytics/"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            params=params,
            json=payload,
        )
        return response.json()
