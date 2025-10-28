import logging

from typing import List, Optional

from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.redis_queue_manager import (
    RedisQueueManager,
    TempRedisQueueManager,
)
from marketplace.wpp_products.models import Catalog


logger = logging.getLogger(__name__)


class SyncAllProductsUseCase:
    """
    Use case for synchronizing all products for a given catalog.

    This use case is responsible for:
      - Filtering active sellers.
      - Setting up the main and temporary Redis queues.
      - Reinserting pending items from the temporary queue into the main queue.
      - Loading SKUs from cache if necessary.
      - Building and triggering the DataProcessor to process the items.

    The use case delegates business rules and queue management to the underlying service,
    ensuring that only the essential data is passed to the processing layer.
    """

    def __init__(self, products_service: PrivateProductsService):
        """
        Initialize the use case with the products service.

        Args:
            products_service: An instance of PrivateProductsService that handles product synchronization.
        """
        self.products_service = products_service

    def execute(
        self,
        domain: str,
        catalog: Catalog,
        sellers: Optional[List[str]] = None,
        update_product: bool = False,
        sync_specific_sellers: bool = False,
        sync_all_sellers: bool = False,
        sales_channel: Optional[list[str]] = None,
    ) -> bool:
        """
        Execute the sync process for all products.

        Args:
            domain: The domain for which to process products.
            catalog: The catalog to process.
            sellers: Optional list of seller IDs to filter active sellers.
            update_product: Whether this is an update process.
            sync_specific_sellers: Whether this is a seller-specific sync.
            sync_all_sellers: Whether to sync all active sellers regardless of sellers parameter.
            sales_channel: The sales channel to be linked with the VTEX app.
        Returns:
            True if the sync completed successfully, False otherwise.
        """
        # Step 1: Filter active sellers for the given domain.
        seller_ids = self._filter_active_sellers(
            domain, sellers, sync_all_sellers, sales_channel
        )
        if not seller_ids:
            return False

        # Step 2: Set up the main and temporary Redis queues.
        main_queue, temp_queue = self._setup_queues(domain)

        # Step 3: Populate the main queue by reinserting pending items from the temporary queue;
        # if the main queue is empty, load SKUs from cache.
        self._populate_main_queue(main_queue, temp_queue, domain, sales_channel)

        # Step 4: Load business rules and store domain configuration
        config = catalog.vtex_app.config
        rules = self.products_service._load_rules(config.get("rules", []))
        store_domain = config.get("store_domain")

        # Step 5: Build the DataProcessor using the configured queues.
        data_processor = self._build_data_processor(main_queue, temp_queue)

        # Step 6: Trigger the processing of items.
        data_processor.process(
            items=[],  # Items are already in the main queue.
            catalog=catalog,
            domain=domain,
            service=self.products_service,
            rules=rules,
            store_domain=store_domain,
            update_product=update_product,
            sync_specific_sellers=sync_specific_sellers,
            mode="single",
            sellers=seller_ids,
            sales_channel=sales_channel,
        )

        # Step 7: Clear the main queue after processing is complete.
        main_queue.clear()
        return True

    def _filter_active_sellers(
        self,
        domain: str,
        sellers: Optional[List[str]] = None,
        sync_all_sellers: bool = False,
        sales_channel: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Retrieve and filter active sellers for the given domain.

        Args:
            domain: The domain for which to retrieve active sellers.
            sellers: Optional list of seller IDs to filter.
            sync_all_sellers: Whether to return all active sellers regardless of sellers parameter.
            sales_channel: Optional sales channel to filter sellers.

        Returns:
            A list of valid seller IDs, or empty list if none are valid.
        """
        logger.info(f"Getting active sellers for domain: {domain}")
        # Use the first sales channel if multiple are provided, or None if not provided
        sales_channel_param = (
            sales_channel[0] if sales_channel and len(sales_channel) > 0 else None
        )
        active_sellers = set(
            self.products_service.list_active_sellers(domain, sales_channel_param)
        )

        if sync_all_sellers:
            logger.info(
                f"Syncing all active sellers: {len(active_sellers)} sellers found"
            )
            return list(active_sellers)

        if sellers is not None:
            valid_sellers = [seller for seller in sellers if seller in active_sellers]
            invalid_sellers = set(sellers) - active_sellers
            if invalid_sellers:
                logger.info(
                    f"Warning: Sellers IDs {invalid_sellers} are not active and will be ignored."
                )
            if not valid_sellers:
                logger.info("No valid sellers available. Process will be stopped.")
                return []
            return valid_sellers
        return list(active_sellers)

    def _setup_queues(self, domain: str):
        """
        Set up and return the main and temporary Redis queues for the specified domain.

        Args:
            domain: The domain to base the queue keys on.

        Returns:
            A tuple (main_queue, temp_queue) where:
              - main_queue is an instance of RedisQueueManager.
              - temp_queue is an instance of TempRedisQueueManager.
        """
        redis_key = f"sku_queue_{domain}"
        main_queue = RedisQueueManager(redis_key=redis_key, timeout=7 * 24 * 3600)
        temp_queue = TempRedisQueueManager(redis_key=redis_key, timeout=7 * 24 * 3600)
        return main_queue, temp_queue

    def _populate_main_queue(
        self,
        main_queue,
        temp_queue,
        domain: str,
        sales_channel: Optional[List[str]] = None,
    ) -> None:
        """
        Populate the main Redis queue by reinserting pending items from the temporary queue;
        if the main queue is empty, load SKUs from cache.

        Args:
            main_queue: The main Redis queue.
            temp_queue: The temporary Redis queue.
            domain: The domain for which to load SKUs.
            sales_channel: Optional sales channel to filter SKUs.
        """
        # Reinsert pending items from the temporary queue, if any.
        temp_items = temp_queue.get_all()
        if temp_items:
            logger.info(
                f"Reinserting {len(temp_items)} pending items from temporary queue into the main queue."
            )
            main_queue.put_many(temp_items)
            temp_queue.clear()
        # If the main queue is empty, load SKUs from cache.
        if main_queue.qsize() == 0:
            # Use the first sales channel if multiple are provided, or None if not provided
            sales_channel_param = (
                sales_channel[0] if sales_channel and len(sales_channel) > 0 else None
            )
            skus_ids = self.products_service.list_all_skus_ids(
                domain, sales_channel_param
            )
            main_queue.put_many(skus_ids)
            logger.info(f"Loaded {len(skus_ids)} SKUs into main Redis queue.")
        else:
            logger.info(
                "Using existing main Redis queue for SKUs (resuming processing)."
            )

    def _build_data_processor(self, main_queue, temp_queue) -> DataProcessor:
        """
        Instantiate and return a DataProcessor with the given parameters.

        Args:
            main_queue: The main Redis queue.
            temp_queue: The temporary Redis queue.

        Returns:
            An instance of DataProcessor.
        """
        return DataProcessor(queue=main_queue, temp_queue=temp_queue, use_threads=True)
