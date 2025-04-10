import logging

from typing import List

from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.wpp_products.models import Catalog


logger = logging.getLogger(__name__)


class SyncProductByWebhookUseCase:
    """
    Use case for synchronizing products received via webhook.

    This use case is responsible for:
      - Processing product updates received through webhooks
      - Using non-threaded processing for webhook updates
      - Delegating the actual processing to the DataProcessor

    The use case follows the same pattern as SyncAllProductsUseCase but is
    specifically optimized for webhook-triggered updates.
    """

    def __init__(
        self,
        products_service: PrivateProductsService,
        data_processor: DataProcessor = None,
    ):
        """
        Initialize the use case with the required dependencies.

        Args:
            products_service: An instance of PrivateProductsService that handles product synchronization.
            data_processor: An instance of DataProcessor for processing product data. If None, creates a
            non-threaded processor by default.
        """
        self.products_service = products_service
        self.data_processor = data_processor or DataProcessor(use_threads=False)

    def execute(
        self, domain: str, sellers_skus: list, catalog: Catalog
    ) -> List[FacebookProductDTO]:
        """
        Execute the sync process for products received via webhook.

        Args:
            domain: The domain for which to process products.
            sellers_skus: List of strings in "seller#sku" format to be processed.
            catalog: The catalog to process.

        Returns:
            List of FacebookProductDTO objects representing the processed products.
        """
        # Step 1: Load business rules and store domain configuration
        config = catalog.vtex_app.config
        rules = self.products_service._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")

        # Step 2: Process the items using "seller_sku" mode
        logger.info(
            f"Processing {len(sellers_skus)} items via webhook for domain: {domain}"
        )
        result = self.data_processor.process(
            items=sellers_skus,
            catalog=catalog,
            domain=domain,
            service=self.products_service,
            rules=rules,
            store_domain=store_domain,
            update_product=True,
            sync_specific_sellers=False,
            mode="seller_sku",
            sellers=None,  # Not needed in this mode, as each item already includes the seller
        )

        return result
