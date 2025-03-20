from abc import ABC, abstractmethod
from typing import Dict, Any


class CommerceClientInterface(ABC):
    """
    Interface for Commerce Client operations.
    Defines the contract for interacting with the Retail Commerce API.
    """

    @abstractmethod
    def send_template_library_status_update(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send template library status update to Commerce API.

        Args:
            data: Dictionary containing the template status update information

        Returns:
            Dictionary with the API response
        """
        pass
