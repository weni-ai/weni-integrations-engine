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

    def delete_whatsapp_integration(self, project_uuid: str, waba_id: str) -> None:
        """
        Delete a WhatsApp integration.

        Args:
            project_uuid (UUID): The UUID of the project.
            waba_id (str): The Waba's id.
        """


class InsightsUseCaseSyncInterface(Protocol):
    """
    Interface for the Insights sync.

    This protocol defines that UseCases that integrates with insights must sync.
    """

    def sync(self) -> None:
        """
        Sync with insights.

        Returns:
            None.
        """
