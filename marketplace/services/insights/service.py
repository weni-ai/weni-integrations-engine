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

    def __init__(self, client: InsightsClientInterface):
        """
        Initialize the InsightsService with a client.

        Args:
            client: The client instance used to make API requests.
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
