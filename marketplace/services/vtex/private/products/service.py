"""
Service for managing product operations with VTEX private APIs.

This service interacts with VTEX's private APIs for product-related operations. It handles
domain validation, credentials verification, product listing, and updates from webhook notifications.

Attributes:
    client: A client instance for VTEX private APIs communication.
    data_processor: DataProcessor instance for processing product data.

Public Methods:
    check_is_valid_domain(domain): Validates if a domain is recognized by VTEX.
    validate_private_credentials(domain): Checks if stored credentials for a domain are valid.
    list_all_products(domain): Lists all products from a domain. Returns processed product data.
    get_product_details(sku_id, domain): Retrieves details for a specific SKU.
    simulate_cart_for_seller(sku_id, seller_id, domain): Simulates a cart for a seller and SKU.
    update_product_info(domain, webhook_payload): Updates product info based on webhook payload.

Exceptions:
    CredentialsValidationError: Raised for invalid domain or credentials.

Usage:
    Instantiate with a client having API credentials. Use methods for product operations with VTEX.

Example:
    client = VtexPrivateClient(app_key="key", app_token="token")
    service = PrivateProductsService(client)
    is_valid = service.validate_private_credentials("domain.vtex.com")
    if is_valid:
        products = service.list_all_products("domain.vtex.com")
        # Use products data as needed
"""

from typing import List

from marketplace.services.vtex.exceptions import CredentialsValidationError
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.business.rules.rule_mappings import RULE_MAPPINGS
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class PrivateProductsService:
    def __init__(self, client, data_processor_class=DataProcessor):
        self.client = client
        self.data_processor = data_processor_class()
        # TODO: Check if it makes sense to leave the domain instantiated
        # so that the domain parameter is removed from the methods

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

    def list_all_products(self, domain, catalog) -> List[FacebookProductDTO]:
        config = catalog.vtex_app.config
        active_sellers = self.client.list_active_sellers(domain)
        skus_ids = self.client.list_all_products_sku_ids(domain)
        rules = self._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")
        products_dto = self.data_processor.process_product_data(
            skus_ids, active_sellers, self, domain, store_domain, rules, catalog
        )
        return products_dto

    def get_product_details(self, sku_id, domain):
        return self.client.get_product_details(sku_id, domain)

    def simulate_cart_for_seller(self, sku_id, seller_id, domain):
        return self.client.pub_simulate_cart_for_seller(
            sku_id, seller_id, domain
        )  # TODO: Change to pvt_simulate_cart_for_seller

    def update_webhook_product_info(
        self, domain: str, skus_ids: list, catalog
    ) -> List[FacebookProductDTO]:
        config = catalog.vtex_app.config
        seller_ids = self.client.list_active_sellers(domain)
        rules = self._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")
        updated_products_dto = self.data_processor.process_product_data(
            skus_ids,
            seller_ids,
            self,
            domain,
            store_domain,
            rules,
            catalog,
            update_product=True,
        )

        return updated_products_dto

    # ================================
    # Private Methods
    # ================================

    def _is_domain_valid(self, domain):
        return self.client.check_domain(domain)

    def _load_rules(self, rule_names):
        rules = []
        for rule_name in rule_names:
            rule_class = RULE_MAPPINGS.get(rule_name)
            if rule_class:
                rules.append(rule_class())
            else:
                print(f"Rule {rule_name} not found or not mapped.")
        return rules
