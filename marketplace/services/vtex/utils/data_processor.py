import concurrent.futures

import threading
import re

from typing import List

from tqdm import tqdm
from queue import Queue

from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.services.vtex.utils.sku_validator import SKUValidator
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.zeroshot.client import MockZeroShotClient
from marketplace.wpp_products.utils import UploadManager


class DataProcessor:
    def __init__(self, use_threads=True):
        self.max_workers = 100
        self.progress_lock = threading.Lock()
        self.use_threads = use_threads
        self.batch_size = 5000
        self.save_lock = threading.Lock()  # Exclusive lock for _save_batch_to_database

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans up text by removing HTML tags, replacing quotes with empty space,
        replacing commas with semicolons, and normalizing whitespace but keeping new lines.
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]*>", "", text)
        # Replace double and single quotes with empty space
        text = text.replace('"', "").replace("'", " ")
        # Normalize new lines and carriage returns to a single newline
        text = re.sub(r"\r\n|\r|\n", "\n", text)
        # Remove excessive whitespace but keep new lines
        text = re.sub(r"[ \t]+", " ", text.strip())
        # Remove bullet points
        text = text.replace("•", "")
        # Ensure there's a space after a period, unless followed by a new line
        text = re.sub(r"\.(?=[^\s\n])", ". ", text)
        return text

    @staticmethod
    def extract_fields(
        store_domain, product_details, availability_details
    ) -> FacebookProductDTO:
        price = (
            availability_details["price"]
            if availability_details["price"] is not None
            else 0
        )
        list_price = (
            availability_details["list_price"]
            if availability_details["list_price"] is not None
            else 0
        )
        image_url = (
            product_details.get("Images", [])[0].get("ImageUrl")
            if product_details.get("Images")
            else product_details.get("ImageUrl")
        )
        sku_id = product_details["Id"]
        product_url = (
            f"https://{store_domain}{product_details.get('DetailUrl')}?idsku={sku_id}"
        )
        description = (
            product_details["ProductDescription"]
            if product_details["ProductDescription"] != ""
            else product_details["SkuName"]
        )
        title = product_details["SkuName"].title()
        # Applies the .title() before clearing the text
        title = title[:200].title()
        description = description[:9999].title()
        # Clean title and description
        title = DataProcessor.clean_text(title)
        description = DataProcessor.clean_text(description)

        availability = (
            "in stock" if availability_details["is_available"] else "out of stock"
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

    def process_product_data(
        self,
        skus_ids,
        active_sellers,
        service,
        domain,
        store_domain,
        rules,
        catalog,
        update_product=False,
        upload_on_sync=False,
        sync_specific_sellers=False,
    ) -> List[FacebookProductDTO]:
        """
        Process a batch of SKU IDs with optional active sellers using threads if the batch size is large
        """
        # Initialize configuration
        self.queue = Queue()
        self.results = []
        self.active_sellers = active_sellers
        self.service = service
        self.domain = domain
        self.store_domain = store_domain
        self.rules = rules
        self.update_product = update_product
        self.invalid_products_count = 0
        self.valid_products_count = 0
        self.catalog = catalog
        self.sku_validator = SKUValidator(service, domain, MockZeroShotClient())
        self.upload_on_sync = upload_on_sync
        self.sent_to_db_count = 0  # Tracks the number of items sent to the database.
        self.vtex_app = self.catalog.vtex_app
        self.use_sku_sellers = self.catalog.vtex_app.config.get(
            "use_sku_sellers", False
        )
        self.sync_specific_sellers = sync_specific_sellers

        print("Initiated process of product treatment.")
        self.progress_bar = tqdm(total=len(skus_ids), desc="[✓:0, ✗:0]", ncols=0)
        for sku_id in skus_ids:
            self.queue.put(sku_id)

        try:
            # Process items in queue
            if self.use_threads:
                self._process_queue_with_threads()
            else:
                self._process_queue_without_threads()
        finally:
            # Close the progress bar after processing, even in case of errors
            self.progress_bar.close()

        # Upload remaining items in the buffer
        if self.upload_on_sync and self.results:
            print(f"Uploading the last {len(self.results)} items to the database.")
            self._save_batch_to_database()

        print(
            f"Processing completed. Total valid products: {self.valid_products_count}"
        )
        return self.results

    def _process_queue_with_threads(self):
        """Helper method to process queue items with threads."""
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = [executor.submit(self.worker) for _ in range(self.max_workers)]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in thread execution: {str(e)}")

    def _process_queue_without_threads(self):
        """Helper method to process queue items without threads."""
        while not self.queue.empty():
            self.worker()

    def worker(self):
        """
        Processes items from the queue.

        This worker handles two processing scenarios:
        - For batch uploads (update_product=True) without specific sellers: processes items as
          seller_id and sku_id pairs extracted from the queue item.
        - For initial sync (update_product=False) or when sync_specific_sellers=True:
          processes each queue item as a single sku_id.

        The method dynamically determines the appropriate processing logic based on
        the update_product and sync_specific_sellers flags.
        """
        while not self.queue.empty():
            try:
                # Extract item from the queue
                item = self.queue.get()

                # Determine conditions for processing

                if self.update_product and not self.sync_specific_sellers:
                    # Parse and process `seller_id` and `sku_id` for v2 batch uploads
                    seller_id, sku_id = self._parse_seller_sku(item)
                    processing_result = self.process_seller_sku(
                        seller_id=seller_id, sku_id=sku_id
                    )
                else:
                    # Process `sku_id` for first sync
                    processing_result = self.process_single_sku(sku_id=item)

                # Handle the processing result (e.g., add to results, update progress bar)
                self._handle_processing_result(processing_result)

            except Exception as e:
                # Log any processing errors and continue
                self._handle_worker_error(item, str(e))

    def _parse_seller_sku(self, seller_sku):
        """
        Parses a seller#sku string into seller_id and sku_id.
        """
        try:
            seller_id, sku_id = seller_sku.split("#")
            return seller_id, sku_id
        except ValueError:
            raise ValueError(f"Invalid format for seller_sku: {seller_sku}")

    def _handle_processing_result(self, processing_result):
        """
        Handles the processing result: updates results, progress, and performs batch saving if necessary.
        """
        with self.progress_lock:
            if processing_result:
                self.valid_products_count += 1
                self.results.extend(processing_result)
                self.progress_bar.set_description(
                    f"[✓:{len(self.results)} | DB:{self.sent_to_db_count} | ✗:{self.invalid_products_count}]"
                )
                if self.upload_on_sync and len(self.results) >= self.batch_size:
                    with self.save_lock:
                        print(
                            f"Batch size of {self.batch_size} reached. Saving to the database."
                        )
                        self._save_batch_to_database()
            else:
                self.invalid_products_count += 1
                self.progress_bar.set_description(
                    f"[✓:{len(self.results)} | DB:{self.sent_to_db_count} | ✗:{self.invalid_products_count}]"
                )
            self.progress_bar.update(1)

    def _handle_worker_error(self, item, error_message: str):
        """
        Handles errors during worker processing by logging and updating progress.
        """
        print(f"Error processing item {item}: {error_message}")
        with self.progress_lock:
            self.invalid_products_count += 1
            self.progress_bar.set_description(
                f"[✓:{len(self.results)} | DB:{self.sent_to_db_count} | ✗:{self.invalid_products_count}]"
            )
            self.progress_bar.update(1)

    def process_single_sku(self, sku_id):
        """
        Process a single SKU by validating its details and simulating availability across multiple sellers.
        """
        facebook_products = []
        try:
            product_details = self.sku_validator.validate_product_details(
                sku_id, self.catalog
            )
            if not product_details:
                return facebook_products
        except CustomAPIException as e:
            if e.status_code == 404:
                print(f"SKU {sku_id} not found. Skipping...")
            elif e.status_code == 500:
                print(f"SKU {sku_id} returned status: {e.status_code}. Skipping...")

            print(f"An error {e} occurred on get_product_details. SKU: {sku_id}")
            return []

        is_active = product_details.get("IsActive")
        if not is_active and not self.update_product:
            return facebook_products

        # Define the sellers to be synchronized
        sellers_to_sync = []
        if self.use_sku_sellers and not self.update_product:
            sku_sellers = product_details.get("SkuSellers")
            for seller in sku_sellers:
                seller_id = seller.get("SellerId")
                if seller_id:
                    sellers_to_sync.append(seller_id)
        else:
            sellers_to_sync = self.active_sellers

        if not sellers_to_sync:
            print(f"No sellers to sync for SKU {sku_id}. Skipping...")
            return facebook_products

        # Perform the simulation for multiple sellers
        try:
            availability_results = self.service.simulate_cart_for_multiple_sellers(
                sku_id, sellers_to_sync, self.domain
            )
        except CustomAPIException as e:
            print(f"Failed to simulate cart for SKU {sku_id} with sellers: {e}")
            return facebook_products

        # Process simulation results
        for seller_id, availability_details in availability_results.items():
            if not availability_details["is_available"] and not self.update_product:
                continue

            product_dto = DataProcessor.extract_fields(
                self.store_domain, product_details, availability_details
            )
            if not self._validate_product_dto(product_dto):
                continue

            params = {
                "seller_id": seller_id,
                "service": self.service,
                "domain": self.domain,
            }
            all_rules_applied = True
            for rule in self.rules:
                if not rule.apply(product_dto, **params):
                    all_rules_applied = False
                    break

            if all_rules_applied:
                facebook_products.append(product_dto)

        return facebook_products

    def _validate_product_dto(self, product_dto: FacebookProductDTO) -> bool:
        """Verifies that all required fields in the FacebookProductDTO are filled in.
        Returns True if the product is valid, False otherwise.
        """
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

        if (
            product_dto.availability == "in stock" and not product_dto.price
        ):  # None or 0
            print(
                f"Product {product_dto.id} in stock without a valid price, ignoring the product."
            )
            return False

        for field in required_fields:
            if not getattr(product_dto, field, None):
                print(
                    f"Product {product_dto.id} without the field: {field}, ignoring the product."
                )
                return False

        return True

    def _save_batch_to_database(self):
        """
        Saves processed products to the database in batches.
        """
        batch = self.results[: self.batch_size]
        if not batch:
            return

        try:
            product_manager = ProductFacebookManager()  # Manages database interactions.
            # Use the bulk save method for initial insertion.
            all_success = product_manager.bulk_save_initial_product_data(
                batch, self.catalog
            )
            if all_success:
                print(
                    f"Successfully saved a batch of {len(batch)} items to the database."
                )
                # Increment the saved item counter
                self.sent_to_db_count += len(batch)

                # Remove saved items from the buffer.
                self.results = self.results[self.batch_size :]  # noqa: E203

                # Start upload task
                UploadManager.check_and_start_upload(self.vtex_app.uuid)
            else:
                print(
                    "Failed to save batch to the database. Will retry in the next cycle."
                )
        except Exception as e:
            print(f"Error while saving batch to the database: {e}")

    def process_sellers_skus_batch(
        self,
        service,
        domain,
        store_domain,
        rules,
        catalog,
        seller_sku_pairs,
        upload_on_sync=True,
        sync_specific_sellers=False,
    ):
        """
        Process a batch of seller and SKU pairs using threads if the batch size is large.
        """
        # Initialize configuration
        self.queue = Queue()
        self.results = []
        self.invalid_products_count = 0
        self.valid_products_count = 0
        self.service = service
        self.domain = domain
        self.store_domain = store_domain
        self.rules = rules
        self.catalog = catalog
        self.vtex_app = self.catalog.vtex_app
        self.upload_on_sync = upload_on_sync
        self.sku_validator = SKUValidator(service, domain, MockZeroShotClient())
        self.sent_to_db_count = 0  # Tracks the number of items sent to the database.
        self.update_product = True
        self.sync_specific_sellers = sync_specific_sellers

        # Populate the queue
        initial_batch_count = len(seller_sku_pairs)
        print("Initiated process of product treatment.")
        self.progress_bar = tqdm(total=initial_batch_count, desc="[✓:0, ✗:0]", ncols=0)
        for seller_sku in seller_sku_pairs:
            self.queue.put(seller_sku)

        # Determine whether to use threads
        use_threads = len(seller_sku_pairs) > 10

        try:
            # Process items in queue
            if use_threads:
                self._process_queue_with_threads()
            else:
                self._process_queue_without_threads()
        finally:
            # Close the progress bar after processing, even in case of errors
            self.progress_bar.close()

        # Save remaining items in buffer
        if self.results:
            print(f"Uploading the last {len(self.results)} items to the database.")
            self._save_batch_to_database()

        # Final log and return
        print(
            f"Processing completed. Total valid products: {self.valid_products_count}"
        )
        if initial_batch_count > 0 and len(self.results) == 0:
            print("All items processed successfully.")
            return True

        print("Some errors occurred during processing.")
        return self.results

    def process_seller_sku(self, seller_id, sku_id):
        facebook_products = []
        try:
            product_details = self.sku_validator.validate_product_details(
                sku_id, self.catalog
            )
            if not product_details:
                return facebook_products
        except CustomAPIException as e:
            if e.status_code == 404:
                print(f"SKU {sku_id} not found. Skipping...")
            elif e.status_code == 500:
                print(f"SKU {sku_id} returned status: {e.status_code}. Skipping...")

            print(f"An error {e} occurred on get_product_details. SKU: {sku_id}")
            return []

        is_active = product_details.get("IsActive")
        if not is_active and not self.update_product:
            return facebook_products

        if not seller_id:
            print(f"No seller to sync for SKU {sku_id}. Skipping...")
            return facebook_products

        # Perform the simulation for seller
        try:
            availability_result = self.service.simulate_cart_for_seller(
                sku_id, seller_id, self.domain
            )
        except CustomAPIException as e:
            print(
                f"Failed to simulate cart for SKU {sku_id} with seller {seller_id}: {e}"
            )
            return facebook_products

        # Process simulation results

        if not availability_result["is_available"] and not self.update_product:
            return facebook_products

        product_dto = DataProcessor.extract_fields(
            self.store_domain, product_details, availability_result
        )
        if not self._validate_product_dto(product_dto):
            return facebook_products

        params = {
            "seller_id": seller_id,
            "service": self.service,
            "domain": self.domain,
        }
        all_rules_applied = True
        for rule in self.rules:
            if not rule.apply(product_dto, **params):
                all_rules_applied = False
                break

        if all_rules_applied:
            facebook_products.append(product_dto)

        return facebook_products
