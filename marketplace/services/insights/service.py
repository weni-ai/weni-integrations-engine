"""
Service module for handling insights operations.
This module provides services to interact with the insights API.
"""

from typing import Dict, Any
from marketplace.interfaces.insights.interfaces import InsightsClientInterface
from marketplace.clients.insights.client import InsightsClient


class InsightsService:  # pragma: no cover
    """
    Service class for handling insights operations.

    This class provides methods to interact with the insights API,
    such as creating WhatsApp integrations.
    """

    def __init__(self, client: InsightsClientInterface = None):
        """
        Initialize the InsightsService with a client.

        Args:
            client: The client instance used to make API requests. If not provided,
            a default InsightsClient will be instantiated.
        """
        self.client = client or InsightsClient()

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
        return self.client.create_whatsapp_integration(whatsapp_data)

    def delete_whatsapp_integration(self, project_uuid: str, waba_id: str) -> None:
        """
        Delete a WhatsApp integration.

        Args:
            project_uuid (UUID): The UUID of the project.
            waba_id (str): The Waba's id.
        """
        return self.client.delete_whatsapp_integration(project_uuid, waba_id)

    def get_template_insights(self, params: dict, payload: dict) -> dict:
        """
        Sends a request to the Insights API to retrieve template metrics.

        Args:
            params (dict): Query parameters to send in the request.
                Example:
                    {
                        "waba_id": "123456789012345",
                        "start_date": "2025-06-12T00:00:00+00:00",
                        "end_date": "2025-06-13T23:59:59+00:00"
                    }

            payload (dict): JSON body for the POST request.
                Example:
                    {
                        "template_ids": ["23873358355610585"]
                    }

        Returns:
            dict: JSON response from the Insights API.
        """
        return self.client.get_template_insights(params, payload)
