"""
Service for interacting with the public VTEX API.

This service provides methods for interacting with the public-facing features of the VTEX platform,
such as product listing and domain validation. It facilitates the integration of VTEX functionalities
into the marketplace without requiring private API credentials.

Attributes:
    client: An instance of a client equipped to make requests to the public VTEX API endpoints.

Public Methods:
    list_all_products(domain): Retrieves a list of all products from the VTEX store for the specified domain.
        The domain is first validated to ensure it corresponds to an active VTEX store.

    check_is_valid_domain(domain): Validates the provided domain by performing a
    check against VTEX public API endpoints.
        Raises a ValidationError if the domain does not correspond to a valid VTEX store.

Raises:
    ValidationError: If the domain provided is not recognized by VTEX as a valid
    store domain during the domain verification process.

Usage:
    This service is intended to be used where public information about a VTEX store is needed.
    It does not require API keys or tokens
    for authentication, as it interacts with endpoints that are publicly accessible.

Example:
    client = VtexPublicClient()
    service = PublicProductsService(client)
    if service.check_is_valid_domain("example.vtex.com"):
        products = service.list_all_products("example.vtex.com")
        # Process the list of products
"""
from rest_framework.exceptions import ValidationError


class PublicProductsService:
    def __init__(self, client):
        self.client = client

    # ================================
    # Public Methods
    # ================================

    def list_all_products(self, domain):
        self._check_is_valid_domain(domain)
        return self.client.list_products(domain)

    def check_is_valid_domain(self, domain):
        if not self._is_domain_valid(domain):
            raise ValidationError("The domain provided is invalid.")

    # ================================
    # Private Methods
    # ================================

    def _is_domain_valid(self, domain):
        return self.client.check_domain(domain)
