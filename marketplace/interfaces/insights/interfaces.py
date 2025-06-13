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

    def get_template_insights(self, params: dict, payload: dict) -> dict:
        """
        Fetches insights metrics for the given templates within the specified period.

        Args:
            params (dict): Query parameters to send to the Insights API.
                Expected keys:
                    - "waba_id" (str): WhatsApp Business Account ID.
                    - "start_date" (str): Start datetime in ISO 8601 UTC format (e.g., "2025-06-12T00:00:00+00:00").
                    - "end_date" (str): End datetime in ISO 8601 UTC format (e.g., "2025-06-13T23:59:59+00:00").

            payload (dict): JSON body for the POST request.
                Expected keys:
                    - "template_ids" (List[str]): List of message_template_id strings.

        Returns:
            dict: Parsed JSON response from the Insights API.
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
