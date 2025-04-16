import threading
import re
import concurrent.futures

import logging
from django.db import close_old_connections
from tqdm import tqdm
from typing import List, Optional

from queue import Queue


from marketplace.interfaces.redis.interfaces import AbstractQueue
from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.services.vtex.utils.redis_queue_manager import TempRedisQueueManager
from marketplace.services.vtex.utils.sku_validator import SKUValidator
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.zeroshot.client import MockZeroShotClient
from marketplace.wpp_products.utils import UploadManager

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Responsibility: Text Cleaning
# --------------------------------------------------
class TextCleaner:
    """
    Utility class for cleaning and normalizing text.
    """

    @staticmethod
    def clean(text: str) -> str:
        """
        Clean and normalize text by removing HTML tags, control characters, and other problematic unicode.

        Args:
            text: The text to clean.

        Returns:
            Cleaned text.
        """
        # Remove HTML tags.
        text = re.sub(r"<[^>]*>", "", text)
        # Replace non-breaking spaces with regular spaces.
        text = text.replace("\xa0", " ")
        # Remove zero-width spaces (e.g., \u200b) and similar invisible characters.
        text = text.replace("\u200b", "")
        # Remove control characters (except newline) - characters with codepoints 0-9 (except newline 10),
        # 11-31, and 127.
        text = re.sub(r"[\x00-\x09\x0B-\x1F\x7F]", "", text)
        # Replace double and single quotes with an empty space.
        text = text.replace('"', "").replace("'", " ")
        # Normalize newlines and carriage returns to a single newline.
        text = re.sub(r"\r\n|\r|\n", "\n", text)
        # Replace multiple spaces or tabs with a single space.
        text = re.sub(r"[ \t]+", " ", text.strip())
        # Remove bullet points.
        text = text.replace("•", "")
        # Ensure there is a space after a period if not followed by whitespace or newline.
        text = re.sub(r"\.(?=[^\s\n])", ". ", text)
        return text


# --------------------------------------------------
# Responsibility: Product Data Extraction
# --------------------------------------------------
class ProductExtractor:
    """
    Extracts and formats product data from raw API responses
    """

    def __init__(self, store_domain: str):
        """
        Initialize the product extractor

        Args:
            store_domain: The store domain for building product URLs
        """
        self.store_domain = store_domain

    def extract(
        self, product_details: dict, availability_details: dict
    ) -> FacebookProductDTO:
        """
        Extract product data and create a FacebookProductDTO

        Args:
            product_details: Raw product details from API
            availability_details: Availability information from API

        Returns:
            FacebookProductDTO with formatted product data
        """
        # Ensure price and list_price are always numbers, even when None
        price = availability_details.get("price", 0) or 0
        list_price = availability_details.get("list_price", 0) or 0

        # Check if 'Images' exists and is a non-empty list; if not, fallback to 'ImageUrl'
        images = product_details.get("Images")
        if images and isinstance(images, list) and len(images) > 0:
            image_url = images[0].get("ImageUrl")
        else:
            image_url = product_details.get("ImageUrl", "")
            if not image_url:
                # Log a warning if no image URL is found
                logger.warning(f"No image found for SKU {product_details.get('Id')}")

        sku_id = product_details["Id"]
        product_url = f"https://{self.store_domain}{product_details.get('DetailUrl')}?idsku={sku_id}"

        # Use ProductDescription if available, otherwise fallback to SkuName.
        description = product_details.get("ProductDescription") or product_details.get(
            "SkuName", ""
        )
        title = product_details.get("SkuName", "").title()[:200]
        description = description[:9999].title()
        title = TextCleaner.clean(title)
        description = TextCleaner.clean(description)

        availability = (
            "in stock" if availability_details.get("is_available") else "out of stock"
        )
        status = "Active" if availability == "in stock" else "archived"

        return FacebookProductDTO(
            id=sku_id,
            title=title,
            description=description,
            availability=availability,
            status=status,
            condition="new",
            price=list_price,
            link=product_url,
            image_link=image_url,
            brand=product_details.get("BrandName", "N/A"),
            sale_price=price,
            product_details=product_details,
        )


# --------------------------------------------------
# Responsibility: Validation and Rule Application
# --------------------------------------------------
class ProductValidator:
    """
    Validates products and applies business rules
    """

    def __init__(self, rules: List):
        """
        Initialize the product validator

        Args:
            rules: List of business rules to apply
        """
        self.rules = rules

    def is_valid(self, product_dto: FacebookProductDTO) -> bool:
        """
        Check if a product is valid by validating required fields

        Args:
            product_dto: The product to validate

        Returns:
            True if the product is valid, False otherwise
        """
        # Validation of required fields
        required_fields = [
            "id",
            "title",
            "description",
            "availability",
            "status",
            "condition",
            "link",
            "image_link",
            "brand",
        ]
        if product_dto.availability == "in stock" and not product_dto.price:
            return False
        for field in required_fields:
            if not getattr(product_dto, field, None):
                return False
        return True

    def apply_rules(
        self, product_dto: FacebookProductDTO, seller_id: str, service, domain
    ) -> bool:
        """
        Apply business rules to a product.

        Args:
            product_dto: The product to apply rules to.
            seller_id: The seller ID.
            service: The service to use for rule application.
            domain: The domain to use for rule application.

        Returns:
            True if the product passes all rules, False otherwise.
        """
        # Build a parameters dictionary to be passed to each rule.
        params = {"seller_id": seller_id, "service": service, "domain": domain}
        for rule in self.rules:
            if not rule.apply(product_dto, **params):
                return False
        return True


# --------------------------------------------------
# Responsibility: Persistence (batch saving)
# --------------------------------------------------
class ProductSaver:
    """
    Handles batch saving of products to the database
    """

    def __init__(self, batch_size: int = 5000):
        """
        Initialize the product saver

        Args:
            batch_size: Number of products to save in each batch
        """
        self.batch_size = batch_size
        self.sent_to_db = 0

    def save_batch(
        self, products: List[FacebookProductDTO], catalog
    ) -> List[FacebookProductDTO]:
        """
        Save a batch of products to the database and trigger the upload process if successful.

        This method attempts to save a batch of products to the database using the
        ProductFacebookManager. If the save operation is successful, it increments the counter
        of products sent to the database and triggers the upload process via UploadManager.
        Regardless of the outcome, the current batch is discarded to prevent repeated retries
        of the same products, even in case of failure.

        Args:
            products: List of products to save.
            catalog: The catalog to which the products belong.

        Returns:
            List of remaining products that were not processed in this batch.
        """

        if not products:
            return products
        batch = products[: self.batch_size]
        try:
            product_manager = ProductFacebookManager()
            if product_manager.bulk_save_initial_product_data(batch, catalog):
                self.sent_to_db += len(batch)
                UploadManager.check_and_start_upload(catalog.vtex_app.uuid)

            else:
                logger.warning(
                    "Failed to save batch to database. Will retry in next cycle."
                )
        except Exception as e:
            logger.error(f"Error saving batch: {str(e)}")

        # Regardless of the outcome, discard the current batch to avoid repeated retries.
        return products[self.batch_size :]  # noqa: E203


# --------------------------------------------------
# Responsibility: Product Processing (business logic)
# --------------------------------------------------
class ProductProcessor:
    """
    Processes products according to business logic
    """

    def __init__(
        self,
        catalog,
        domain,
        service,
        extractor: ProductExtractor,
        validator: ProductValidator,
        update_product: bool = False,
        sync_specific_sellers: bool = False,
    ):
        """
        Initialize the product processor

        Args:
            catalog: The catalog to process for
            domain: The domain to process for
            service: The service to use for processing
            extractor: ProductExtractor to use for data extraction
            validator: ProductValidator to use for validation
            update_product: Whether to update existing products
            sync_specific_sellers: Whether this is a seller-specific sync
        """
        self.catalog = catalog
        self.domain = domain
        self.service = service
        self.extractor = extractor
        self.validator = validator
        self.update_product = update_product
        self.sync_specific_sellers = sync_specific_sellers
        # Injection of SKUValidator (can also be injected)
        self.validator_service = SKUValidator(service, domain, MockZeroShotClient())
        self.use_sku_sellers = getattr(catalog.vtex_app, "config", {}).get(
            "use_sku_sellers", False
        )

    def process_seller_sku(
        self, seller_id: str, sku_id: str
    ) -> List[FacebookProductDTO]:
        """
        Process a single SKU for a specific seller

        Args:
            seller_id: The seller ID to process for
            sku_id: The SKU ID to process

        Returns:
            List of processed products (0 or 1)
        """
        try:
            product_details = self.validator_service.validate_product_details(
                sku_id, self.catalog
            )
            if not product_details or (
                not product_details.get("IsActive") and not self.update_product
            ):
                return []

            availability = self.service.simulate_cart_for_seller(
                sku_id, seller_id, self.domain
            )
            if not availability.get("is_available") and not self.update_product:
                return []

            dto = self.extractor.extract(product_details, availability)
            if not self.validator.is_valid(dto):
                return []
            if not self.validator.apply_rules(
                dto, seller_id, self.service, self.domain
            ):
                return []
            return [dto]
        except CustomAPIException as e:
            logger.error(
                f"Error processing SKU {sku_id} (seller {seller_id}): {str(e)}"
            )
            return []

    def process_single_sku(
        self, sku_id: str, sellers: List[str]
    ) -> List[FacebookProductDTO]:
        """
        Process a single SKU for multiple sellers.

        Args:
            sku_id: The SKU ID to process.
            sellers: List of seller IDs to process for.

        Returns:
            List of processed products (0 or more).
        """
        try:
            product_details = self.validator_service.validate_product_details(
                sku_id, self.catalog
            )
            # If product details are not found, or if the product is inactive and we're not in update mode,
            # return empty.
            if not product_details or (
                not product_details.get("IsActive") and not self.update_product
            ):
                return []

            # If using SKU sellers and not in update mode, override sellers from product details.
            if self.use_sku_sellers and not self.update_product:
                sellers = [
                    s.get("SellerId")
                    for s in product_details.get("SkuSellers", [])
                    if s.get("SellerId")
                ]

            if not sellers:
                return []

            # If update_product is True and the product is inactive, mock the availability results
            # without calling the external simulation.
            if not product_details.get("IsActive") and self.update_product:
                availability_results = {
                    seller: {
                        "is_available": False,
                        "price": 0,
                        "list_price": 0,
                        "data": {},
                    }
                    for seller in sellers
                }
            else:
                # Otherwise, simulate cart for multiple sellers normally.
                availability_results = self.service.simulate_cart_for_multiple_sellers(
                    sku_id, sellers, self.domain
                )

            results = []
            # Iterate over availability results for each seller.
            for seller_id, availability in availability_results.items():
                # Skip if product is unavailable and not in update mode.
                if not availability.get("is_available") and not self.update_product:
                    continue
                # Extract product DTO based on product details and availability.
                dto = self.extractor.extract(product_details, availability)
                # If the DTO is valid and passes all business rules, add it to results.
                if self.validator.is_valid(dto) and self.validator.apply_rules(
                    dto, seller_id, self.service, self.domain
                ):
                    results.append(dto)

            return results
        except CustomAPIException as e:
            logger.error(f"Error processing SKU {sku_id}: {str(e)}")
            return []


# --------------------------------------------------
# Responsibility: Batch Processing and Parallelism Control
# --------------------------------------------------
class BatchProcessor:
    """
    Handles batch processing of items with multi-threading support
    """

    def __init__(
        self,
        queue: AbstractQueue,
        temp_queue: Optional[TempRedisQueueManager] = None,
        use_threads: bool = True,
        max_workers: int = 100,
    ):
        """
        Initialize the batch processor

        Args:
            queue: Queue to use for processing
            use_threads: Whether to use multi-threading for processing
            max_workers: Maximum number of worker threads to use
        """
        self.queue = queue
        self.temp_queue = temp_queue
        self.use_threads = use_threads
        self.max_workers = max_workers
        self.results = []
        self.valid = 0
        self.invalid = 0
        self.progress_lock = threading.Lock()

    def run(
        self,
        items: List[str],
        processor: ProductProcessor,
        mode: str = "single",
        sellers: List[str] = None,
        saver: ProductSaver = None,
    ):
        """
        Run the batch processor on a list of items

        Args:
            items: List of items to process
            processor: ProductProcessor to use for processing
            mode: Processing mode ("single" or "seller_sku")
            sellers: List of seller IDs to process (for "single" mode)
            saver: ProductSaver to use for saving results

        Returns:
            List of processed products
        """
        for item in items:
            self.queue.put(item)

        """
        Determine the total number of items to process:
        - If 'items' is non-empty, it means the in-memory queue is being used,
        so we use the length of the provided items list.
        - If 'items' is empty, it indicates that an external queue (e.g., Redis)
        is used and pre-populated, so we use the current queue size.

        Note: The qsize() method might not be fully reliable across all queue
        implementations, but here it serves to estimate the workload for the progress bar.
        """
        total_items = len(items) if items else self.queue.qsize()

        progress_bar = tqdm(total=total_items, desc="[✓:0 | ✗:0]", ncols=0)

        def worker_job():
            while not self.queue.empty():
                item = self.queue.get()
                try:
                    if mode == "seller_sku":
                        seller_id, sku_id = item.split("#")
                        result = processor.process_seller_sku(seller_id, sku_id)
                    else:  # mode "single"
                        result = processor.process_single_sku(item, sellers)
                        if self.temp_queue:
                            self.temp_queue.put(item)
                    with self.progress_lock:
                        if result:
                            self.valid += 1
                            self.results.extend(result)
                            if saver and len(self.results) >= saver.batch_size:
                                # If batch reaches size, try to save
                                self.results = saver.save_batch(
                                    self.results, processor.catalog
                                )
                                if self.temp_queue:
                                    self.temp_queue.clear()
                        else:
                            self.invalid += 1
                        progress_bar.set_description(
                            f"[✓:{self.valid} | LC:{len(self.results)} | "
                            f"DB:{saver.sent_to_db if saver else 0} | ✗:{self.invalid}]"
                        )
                        progress_bar.update(1)
                except Exception as e:
                    logger.error(f"Failed to process {item}: {str(e)}")
                    with self.progress_lock:
                        self.invalid += 1
                        progress_bar.update(1)
                finally:
                    close_old_connections()

        try:
            # If threading is enabled, process items concurrently
            if self.use_threads:
                # Create a ThreadPoolExecutor with the specified maximum number of worker threads
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers
                ) as executor:
                    # Submit the worker_job function for execution in each thread
                    futures = [
                        executor.submit(worker_job) for _ in range(self.max_workers)
                    ]
                    # Wait for all threads to complete their work
                    for future in futures:
                        future.result()
            # Otherwise, process items sequentially using a single worker_job execution
            else:
                worker_job()

        finally:
            progress_bar.close()

        # Try to save remaining items
        if saver and self.results:
            self.results = saver.save_batch(self.results, processor.catalog)

        if self.temp_queue:
            self.temp_queue.clear()

        logger.info(
            f"Processing completed. Valid: {self.valid}, Invalid: {self.invalid}"
        )
        # Return True if all results were successfully processed
        # (empty list means there's nothing pending to upload)
        return len(self.results) == 0


# --------------------------------------------------
# Main Orchestrator (DataProcessor) with DI
# --------------------------------------------------
class DataProcessor:
    """
    Main orchestrator for product data processing with dependency injection
    """

    def __init__(
        self,
        queue: AbstractQueue = None,
        temp_queue: Optional[TempRedisQueueManager] = None,
        use_threads: bool = True,
        batch_size: int = 5000,
        max_workers: int = 100,
    ):
        """
        Initialize the data processor

        Args:
            queue: Queue to use for processing (if None, a new Queue will be created)
            use_threads: Whether to use multi-threading for processing
            batch_size: Number of items to process in each batch before saving
            max_workers: Maximum number of worker threads to use
        """
        self.queue = queue or Queue()
        self.temp_queue = temp_queue
        self.use_threads = use_threads
        self.batch_size = batch_size
        self.max_workers = max_workers

    def process(
        self,
        items: List[str],
        catalog,
        domain,
        service,
        rules: List = None,
        store_domain: str = None,
        update_product: bool = False,
        sync_specific_sellers: bool = False,
        mode: str = "single",
        sellers: List[str] = None,
    ) -> List[FacebookProductDTO]:
        """
        Process a list of items

        Args:
            items: List of items to process
            catalog: The catalog to process for
            domain: The domain to process for
            service: The service to use for processing
            rules: List of business rules to apply
            store_domain: The store domain for building product URLs
            update_product: Whether to update existing products
            sync_specific_sellers: Whether this is a seller-specific sync
            mode: Processing mode ("single" or "seller_sku")
            sellers: List of seller IDs to process (for "single" mode)

        Returns:
            List of processed products
        """
        # Create components
        extractor = ProductExtractor(store_domain or domain)
        validator = ProductValidator(rules or [])
        saver = ProductSaver(batch_size=self.batch_size)
        processor = ProductProcessor(
            catalog=catalog,
            domain=domain,
            service=service,
            extractor=extractor,
            validator=validator,
            update_product=update_product,
            sync_specific_sellers=sync_specific_sellers,
        )
        batch_processor = BatchProcessor(
            queue=self.queue,
            temp_queue=self.temp_queue,
            use_threads=self.use_threads,
            max_workers=self.max_workers,
        )

        # Process items
        return batch_processor.run(items, processor, mode, sellers, saver)
