"""
Interface module for insights client.
This module provides interfaces for interacting with the insights API.
"""

from typing import Dict, Any, Protocol


class InsightsClientInterface(Protocol):
    """
    Interface for the Insights client.

    This protocol defines the methods that should be implemented by any
    client that interacts with the Insights API.
    """

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
        ...
