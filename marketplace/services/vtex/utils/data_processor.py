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
    ) -> List[FacebookProductDTO]:
        """
        Processes product data and saves batches to the database if upload_on_sync is True.
        """
        self.queue = Queue()
        self.results = []
        self.active_sellers = active_sellers
        self.service = service
        self.domain = domain
        self.store_domain = store_domain
        self.rules = rules
        self.update_product = update_product
        self.invalid_products_count = 0
        self.catalog = catalog
        self.sku_validator = SKUValidator(service, domain, MockZeroShotClient())
        self.upload_on_sync = upload_on_sync
        self.sent_to_db_count = 0  # Tracks the number of items sent to the database.
        self.vtex_app = self.catalog.vtex_app

        # Preparing the tqdm progress bar
        print("Initiated process of product treatment:")
        self.progress_bar = tqdm(total=len(skus_ids), desc="[✓:0, ✗:0]", ncols=0)

        # Initializing the queue with SKUs
        for sku_id in skus_ids:
            self.queue.put(sku_id)

        if self.use_threads:
            # Using threads for processing
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = [
                    executor.submit(self.worker) for _ in range(self.max_workers)
                ]

            # Waiting for all the workers to finish
            for future in futures:
                future.result()
        else:
            # Processing without using threads
            while not self.queue.empty():
                self.worker()

        self.progress_bar.close()

        # Upload remaining items in the buffer
        if self.upload_on_sync and self.results:
            print(f"Uploading the last {len(self.results)} items to the database.")
            self._save_batch_to_database()

        print(f"Processing completed. Total valid products: {len(self.results)}")
        return self.results

    def worker(self):
        while not self.queue.empty():
            sku_id = self.queue.get()
            result = self.process_single_sku(sku_id)

            with self.progress_lock:
                if result:
                    self.results.extend(result)
                    self.progress_bar.set_description(
                        f"[✓:{len(self.results)} | DB:{self.sent_to_db_count} | ✗:{self.invalid_products_count}]"
                    )

                    # Save batch to the database when reaching batch_size
                    if self.upload_on_sync and len(self.results) >= self.batch_size:
                        with self.save_lock:  # Ensure that only one thread executes
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

    def process_single_sku(self, sku_id):
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

        use_sku_sellers = self.vtex_app.config.get("use_sku_sellers", False)
        sellers_to_sync = []
        if use_sku_sellers:
            sku_sellers = product_details.get("SkuSellers")
            for seller in sku_sellers:
                seller_id = seller.get("SellerId")
                if seller_id:
                    sellers_to_sync.append(seller_id)
        else:
            sellers_to_sync = self.active_sellers

        for seller_id in sellers_to_sync:
            if seller_id not in self.active_sellers:
                continue

            try:
                availability_details = self.service.simulate_cart_for_seller(
                    sku_id, seller_id, self.domain
                )
            except CustomAPIException as e:
                if e.status_code == 500:
                    print(
                        f"An error {e.status_code} occurred when simulating cart. SKU {sku_id}, "
                        f"Seller {seller_id}. Skipping..."
                    )
                continue

            if (
                self.update_product is False
                and not availability_details["is_available"]
            ):
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
