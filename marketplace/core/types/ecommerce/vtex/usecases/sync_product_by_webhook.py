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
      - Determining if threading should be used based on the number of items
      - Delegating the actual processing to the DataProcessor

    The use case follows the same pattern as SyncAllProductsUseCase but is
    specifically optimized for webhook-triggered updates.
    """

    def __init__(self, products_service: PrivateProductsService):
        """
        Initialize the use case with the products service.

        Args:
            products_service: An instance of PrivateProductsService that handles product synchronization.
        """
        self.products_service = products_service

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

        # Step 2: Determine if threads should be used based on the size of the sellers_skus list
        use_threads = len(sellers_skus) > 5

        # Step 3: Create the data processor
        data_processor = self._build_data_processor(use_threads)

        # Step 4: Process the items using "seller_sku" mode
        logger.info(
            f"Processing {len(sellers_skus)} items via webhook for domain: {domain}"
        )
        result = data_processor.process(
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

    def _build_data_processor(self, use_threads: bool) -> DataProcessor:
        """
        Instantiate and return a DataProcessor with the given parameters.

        Args:
            use_threads: Whether to use threading for processing.

        Returns:
            An instance of DataProcessor.
        """
        return DataProcessor(use_threads=use_threads)
