"""
Service for interacting with VTEX private APIs that require authentication.

This service is responsible for validating domain and credentials against VTEX private APIs.
It encapsulates the logic for domain validation and credentials checking, ensuring that only
valid and authenticated requests are processed for private VTEX operations.

Attributes:
    client: A configured client instance that is capable of communicating with VTEX private APIs.

Public Methods:
    check_is_valid_domain(domain): Validates the provided domain to ensure it is recognized by VTEX.
        Raises a CredentialsValidationError if the domain is not valid.

    validate_private_credentials(domain): Validates the credentials stored in the client for the given domain.
        Returns True if the credentials are valid, False otherwise.

Private Methods:
    _is_domain_valid(domain): Performs a check against the VTEX API to determine if the provided domain is valid.

Exceptions:
    CredentialsValidationError: Raised when the provided domain
    or credentials are not valid according to VTEX's standards.

Usage:
    To use this service, instantiate it with a client that has the necessary API credentials (app_key and app_token).
    The client should implement methods for checking domain validity and credentials.

Example:
    client = VtexPrivateClient(app_key="your-app-key", app_token="your-app-token")
    service = PrivateProductsService(client)
    is_valid = service.validate_private_credentials("your-domain.vtex.com")
    if is_valid:
        # Proceed with operations that require valid credentials
"""
from marketplace.services.vtex.exceptions import CredentialsValidationError


class PrivateProductsService:
    def __init__(self, client):
        self.client = client

    # ================================
    # Public Methods
    # ================================

    def check_is_valid_domain(self, domain):
        if not self._is_domain_valid(domain):
            raise CredentialsValidationError()

        return True

    def validate_private_credentials(self, domain):
        self.check_is_valid_domain(domain)
        return self.client.is_valid_credentials(domain)

    # ================================
    # Private Methods
    # ================================

    def _is_domain_valid(self, domain):
        return self.client.check_domain(domain)
