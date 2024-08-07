import concurrent.futures
import csv
import pandas as pd
import io
import dataclasses
import threading
import re

from dataclasses import asdict, dataclass

from typing import List, Optional

from tqdm import tqdm
from queue import Queue

from marketplace.services.vtex.utils.sku_validator import SKUValidator
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.zeroshot.client import MockZeroShotClient


@dataclass
class FacebookProductDTO:
    id: str
    title: str
    description: str
    availability: str
    status: str
    condition: str
    price: str
    link: str
    image_link: str
    brand: str
    sale_price: str
    product_details: dict  # TODO: Implement ProductDetailsDTO
    additional_image_link: Optional[str] = ""
    rich_text_description: Optional[str] = ""


@dataclass
class VtexProductDTO:  # TODO: Implement This VtexProductDTO
    pass


class DataProcessor:
    def __init__(self, use_threads=True):
        self.max_workers = 100
        self.progress_lock = threading.Lock()
        self.use_threads = use_threads

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
    ) -> List[FacebookProductDTO]:
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

        # Preparing the tqdm progress bar
        print("Initiated process of product treatment:")
        self.progress_bar = tqdm(
            total=len(skus_ids) * len(self.active_sellers), desc="[✓:0, ✗:0]", ncols=0
        )

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

        return self.results

    def worker(self):
        while not self.queue.empty():
            sku_id = self.queue.get()
            initial_invalid_count = len(self.active_sellers)
            result = self.process_single_sku(sku_id)

            with self.progress_lock:
                if result:
                    self.results.extend(result)
                    valid_count = len(result)
                    invalid_count = initial_invalid_count - valid_count
                    self.invalid_products_count += invalid_count
                    # Updates progress for each SKU processed, valid or not.
                    self.progress_bar.update(valid_count + invalid_count)
                else:
                    self.invalid_products_count += initial_invalid_count
                    # If no valid result was found, the entire attempt is considered invalid.
                    self.progress_bar.update(initial_invalid_count)

                self.progress_bar.set_description(
                    f"[✓:{len(self.results)}, ✗:{self.invalid_products_count}]"
                )

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

        for seller_id in self.active_sellers:
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

    @staticmethod
    def products_to_csv(products: List[FacebookProductDTO]) -> io.BytesIO:
        print("Generating CSV file")
        product_dicts = [dataclasses.asdict(product) for product in products]
        df = pd.DataFrame(product_dicts)
        df = df.drop(columns=["product_details"])
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)
        print("CSV file successfully generated in memory")
        return buffer

    @staticmethod
    def product_to_csv_line(product: FacebookProductDTO) -> str:
        def escape_quotes(text: str) -> str:
            """Replaces quotes with a empty space in the provided text."""
            if isinstance(text, str):
                text = text.replace('"', "").replace("'", " ")
            return text

        product_dict = asdict(product)
        product_dict.pop(
            "product_details", None
        )  # Remove 'product_details' field if present

        cleaned_product_dict = {k: escape_quotes(v) for k, v in product_dict.items()}

        df = pd.DataFrame([cleaned_product_dict])
        csv_line = df.to_csv(
            index=False, header=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL
        ).strip()
        return csv_line

    @staticmethod
    def clear_csv_buffer(buffer: io.BytesIO):
        buffer.close()

    @staticmethod
    def convert_dtos_to_dicts_list(dtos: List[FacebookProductDTO]) -> List[dict]:
        print("Converting DTO's into dictionary.")
        dicts_list = []
        for dto in dtos:
            dto_dict = dataclasses.asdict(dto)
            dto_dict.pop("product_details", None)
            dicts_list.append(dto_dict)

        print("Products successfully converted to dictionary.")
        return dicts_list

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
