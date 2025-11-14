"""
Service for managing product operations with VTEX private APIs.

This service interacts with VTEX's private APIs for product-related operations. It handles
domain validation, credentials verification, product listing, and retrieval of product details.

Attributes:
    client: A client instance for VTEX private APIs communication.

Public Methods:
    check_is_valid_domain(domain): Validates if a domain is recognized by VTEX.
    validate_private_credentials(domain): Checks if stored credentials for a domain are valid.
    list_active_sellers(domain): Lists all active sellers for a domain.
    list_all_skus_ids(domain): Lists all SKU IDs from a domain with caching.
    get_product_specification(product_id, domain): Retrieves specifications for a product.
    get_product_details(sku_id, domain): Retrieves details for a specific SKU.
    simulate_cart_for_seller(sku_id, seller_id, domain): Simulates a cart for a seller and SKU.
    simulate_cart_for_multiple_sellers(sku_id, sellers, domain): Simulates cart for multiple sellers.

Exceptions:
    CredentialsValidationError: Raised for invalid domain or credentials.

Usage:
    Instantiate with a client having API credentials. Use methods for product operations with VTEX.

Example:
    client = VtexPrivateClient(app_key="key", app_token="token")
    service = PrivateProductsService(client)
    is_valid = service.validate_private_credentials("domain.vtex.com")
    if is_valid:
        skus = service.list_all_skus_ids("domain.vtex.com")
        # Use SKU IDs as needed
"""
import logging

from typing import Any, Dict, List, Optional

from django.core.cache import cache

from marketplace.services.vtex.exceptions import CredentialsValidationError
from marketplace.services.vtex.business.rules.rule_mappings import RULE_MAPPINGS


logger = logging.getLogger(__name__)


class PrivateProductsService:
    def __init__(self, client: Any) -> None:
        self.client = client

    def check_is_valid_domain(self, domain: str) -> bool:
        if not self._is_domain_valid(domain):
            raise CredentialsValidationError()
        return True

    def validate_private_credentials(self, domain: str) -> bool:
        self.check_is_valid_domain(domain)
        return self.client.is_valid_credentials(domain)

    def list_active_sellers(
        self, domain: str, sales_channel: Optional[str] = None
    ) -> List[str]:
        return self.client.list_active_sellers(domain, sales_channel)

    def list_all_skus_ids(
        self, domain: str, sales_channel: Optional[str] = None
    ) -> List[str]:
        cache_key = f"active_products_{domain}_{sales_channel or 'all'}"
        cached_skus = cache.get(cache_key)
        if cached_skus:
            logger.info(
                f"Returning cached SKUs for domain {domain} and sales_channel {sales_channel}."
            )
            return cached_skus

        logger.info(
            f"Fetching SKUs for domain {domain} and sales_channel {sales_channel}."
        )
        skus = self.client.list_all_products_sku_ids(
            domain, sales_channel=sales_channel
        )
        cache.set(cache_key, skus, timeout=36000)  # Cache for 10 hours
        return skus

    def get_product_specification(self, product_id: str, domain: str) -> Dict[str, Any]:
        return self.client.get_product_specification(product_id, domain)

    def get_product_details(self, sku_id: str, domain: str) -> Dict[str, Any]:
        return self.client.get_product_details(sku_id, domain)

    def simulate_cart_for_seller(
        self,
        sku_id: str,
        seller_id: str,
        domain: str,
        sales_channel: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Simulate cart for a seller with optional multiple sales channels.

        Args:
            sku_id: The SKU ID to simulate
            seller_id: The seller ID
            domain: The VTEX domain
            sales_channel: Optional sales channel

        Returns:
            List of availability results (one for each sales channel, or one if no sales channel)
        """
        return self.client.pub_simulate_cart_for_seller(
            sku_id, seller_id, domain, sales_channel
        )

    def simulate_cart_for_multiple_sellers(
        self,
        sku_id: str,
        sellers: List[str],
        domain: str,
        sales_channel: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Simulates cart for a SKU across multiple sellers, in blocks of 200.

        Args:
            sku_id: The ID of the SKU to simulate the cart for
            sellers: List of seller IDs to simulate the cart with
            domain: The VTEX domain to use for the simulation
            sales_channel: Optional list of sales channels

        Returns:
            Dictionary mapping seller IDs to their cart simulation results
        """
        results: Dict[str, Dict[str, Any]] = {}

        # Split the sellers list into chunks of 200
        for i in range(0, len(sellers), 200):
            seller_chunk = sellers[i : i + 200]  # noqa: E203
            # Call the client method for each chunk of sellers
            chunk_results = self.client.simulate_cart_for_multiple_sellers(
                sku_id, seller_chunk, domain, sales_channel
            )
            # Merge the results from the client into the overall results
            results.update(chunk_results)

        return results

    # ================================
    # Private Methods
    # ================================
    def _is_domain_valid(self, domain: str) -> bool:
        return self.client.check_domain(domain)

    def _load_rules(self, rule_names: List[str]) -> List[Any]:
        rules = []
        for rule_name in rule_names:
            rule_class = RULE_MAPPINGS.get(rule_name)
            if rule_class:
                rules.append(rule_class())
            else:
                logger.info(f"Rule {rule_name} not found or not mapped.")
        return rules
