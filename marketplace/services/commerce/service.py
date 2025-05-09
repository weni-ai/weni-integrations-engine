from marketplace.interfaces.commerce.interfaces import CommerceClientInterface


class CommerceService:
    """
    Service for Commerce operations.
    Handles business logic related to Commerce API interactions.
    """

    def __init__(self, client: CommerceClientInterface):
        """
        Initialize the Commerce Service with a client that implements the CommerceClientInterface.

        Args:
            client: An instance implementing CommerceClientInterface
        """
        self.client = client

    def send_template_library_status_update(self, data: dict) -> dict:
        """
        Send template library status update to Commerce API.

        Args:
            data: Dictionary containing the template status update information

        Returns:
            Dictionary with the API response
        """
        return self.client.send_template_library_status_update(data)

    def send_template_version(self, template_version_uuid: str, data: dict):
        """
        Send template version to Commerce API.
        """
        return self.client.send_template_version(template_version_uuid, data)
