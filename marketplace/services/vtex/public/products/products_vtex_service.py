"""
Service for interfacing with VTEX API.

This service deals with communication with the public API of the VTEX platform, enabling interaction
with various features like product list and domain verification required to
integrating VTEX into the market.

Attributes:
    client (ClientType): An instance of a client responsible for making API requests to the VTEX platform.

Methods:
    is_domain_valid(domain): Validates the VTEX domain by checking its API response.

    list_all_products(domain): Lists all products from the VTEX store of the given domain.

    update_config(app, key, value): Updates the configuration for the given App by setting a value for a specific key.

    configure(app, domain): Configures the given App with the VTEX domain if valid and marks the app as configured.

Raises:
    ValueError: If the provided domain is invalid during the configuration process.
"""


class VtexProductsService:
    def __init__(self, client):
        self.client = client

    # ================================
    # Public Methods
    # ================================

    def is_domain_valid(self, domain):
        return self.client.check_domain(domain)

    def list_all_products(self, domain):
        self._check_is_valid_domain(domain)
        return self.client.list_products(domain)

    def configure(self, app, domain):
        self._check_is_valid_domain(domain)
        updated_app = self._update_config(app, "domain", domain)
        updated_app.configured = True
        updated_app.save()
        return updated_app

    # ================================
    # Private Methods
    # ================================

    def _update_config(self, app, key, value):
        app.config[key] = value
        return app

    def _check_is_valid_domain(self, domain):
        if not self.is_domain_valid(domain):
            raise ValueError("The domain provided is invalid.")
