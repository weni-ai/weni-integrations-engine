import logging
from typing import List, Optional
from django.conf import settings

from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.wpp_products.models import Catalog

logger = logging.getLogger(__name__)


class SyncProductByWebhookUseCase:
    """
    Use case for synchronizing products received via webhook.

    This use case is responsible for:
        - Processing product updates received through webhooks.
        - Using threading configuration from Django settings.
        - Delegating the actual processing to the DataProcessor.

    Priority levels:
        0: Legacy synchronization (default).
        1: On-demand sync via Celery (asynchronous).
        2: On-demand inline sync (synchronous, returns processed products).
    """

    def __init__(
        self,
        products_service: PrivateProductsService,
        data_processor: Optional[DataProcessor] = None,
    ):
        """
        Initialize the use case with the required dependencies.

        Args:
            products_service: An instance of PrivateProductsService that handles product synchronization.
            data_processor: An instance of DataProcessor for processing product data.
                If None, creates a processor with threading configuration from Django settings.
        """
        self.products_service = products_service
        self.data_processor = data_processor or DataProcessor(
            use_threads=settings.VTEX_WEBHOOK_USE_THREADS
        )

    def execute(
        self,
        domain: str,
        sellers_skus: list,
        catalog: Catalog,
        priority: int = 0,
        salles_channel: Optional[str] = None,
    ) -> List[FacebookProductDTO]:
        """
        Executes the synchronization process for products received via webhook.

        Args:
            domain (str): The domain for which the products are being processed.
            sellers_skus (list): A list of strings in the format "seller#sku".
            catalog (Catalog): The catalog associated with the products to be processed.
            priority (int, optional): The priority level for processing. Defaults to 0.
            salles_channel (str, optional): The sales channel identifier.

        Returns:
            List[FacebookProductDTO]: List of processed products.
                For priority 2 (inline sync), this list should be returned to the caller.
                For priority 0 and 1, it is usually ignored.
        """
        config = catalog.vtex_app.config
        rules = self.products_service._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")

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
            priority=priority,
            salles_channel=salles_channel,
        )

        return result
