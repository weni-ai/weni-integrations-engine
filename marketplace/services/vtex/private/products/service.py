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

from typing import List, Optional

from django.core.cache import cache

from marketplace.services.vtex.exceptions import CredentialsValidationError
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.business.rules.rule_mappings import RULE_MAPPINGS
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from marketplace.wpp_products.models import Catalog


class PrivateProductsService:
    def __init__(self, client, data_processor_class=DataProcessor):
        self.client = client
        self.data_processor = data_processor_class()
        self.webhook_data_processor = data_processor_class(use_threads=False)
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

    def list_active_sellers(self, domain):
        return self.client.list_active_sellers(domain)

    def list_all_active_products(self, domain):
        cache_key = f"active_products_{domain}"
        cached_skus = cache.get(cache_key)
        if cached_skus:
            print(f"Returning cached SKUs for domain {domain}.")
            return cached_skus

        skus = self.client.list_all_active_products(domain)
        cache.set(cache_key, skus, timeout=3600)  # Cache for 1 hour
        print(f"Fetched SKUs for domain {domain} and stored in cache.")
        return skus

    def list_all_products(
        self,
        domain: str,
        catalog: Catalog,
        sellers: Optional[List[str]] = None,
        update_product=False,
        upload_on_sync=False,
    ) -> List[FacebookProductDTO]:
        """
        Fetches and processes all products for the given catalog and sellers.
        """
        config = catalog.vtex_app.config
        active_sellers = set(self.list_active_sellers(domain))
        if sellers is not None:
            valid_sellers = [seller for seller in sellers if seller in active_sellers]
            invalid_sellers = set(sellers) - active_sellers
            if invalid_sellers:
                print(
                    f"Warning: Sellers IDs {invalid_sellers} are not active and will be ignored."
                )
                return
            sellers_ids = valid_sellers
        else:
            sellers_ids = list(active_sellers)

        skus_ids = self.list_all_active_products(domain)
        rules = self._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")

        products_dto = self.data_processor.process_product_data(
            skus_ids=skus_ids,
            active_sellers=sellers_ids,
            service=self,
            domain=domain,
            store_domain=store_domain,
            rules=rules,
            catalog=catalog,
            update_product=update_product,
            upload_on_sync=upload_on_sync,
        )
        return products_dto

    def get_product_details(self, sku_id, domain):
        return self.client.get_product_details(sku_id, domain)

    def simulate_cart_for_seller(self, sku_id, seller_id, domain):
        return self.client.pub_simulate_cart_for_seller(
            sku_id, seller_id, domain
        )  # TODO: Change to pvt_simulate_cart_for_seller

    def update_webhook_product_info(
        self, domain: str, skus_ids: list, seller_ids: list, catalog: Catalog
    ) -> List[FacebookProductDTO]:
        config = catalog.vtex_app.config
        rules = self._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")
        updated_products_dto = self.webhook_data_processor.process_product_data(
            skus_ids=skus_ids,
            active_sellers=seller_ids,
            service=self,
            domain=domain,
            store_domain=store_domain,
            rules=rules,
            catalog=catalog,
            update_product=True,
        )

        return updated_products_dto

    def get_product_specification(self, product_id, domain):
        return self.client.get_product_specification(product_id, domain)

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
