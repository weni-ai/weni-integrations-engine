import io

from datetime import datetime

from django.db.models import QuerySet

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog, UploadProduct
from marketplace.services.facebook.service import (
    FacebookService,
)


class ProductUploadManager:
    def fetch_pending_products(self, catalog, batch_size) -> QuerySet:
        """Fetches pending products for the specified catalog, ordered by creation date."""
        return UploadProduct.objects.filter(catalog=catalog, status="pending").order_by(
            "modified_on"
        )[:batch_size]

    def convert_to_csv(self, products: QuerySet, include_header=True) -> io.BytesIO:
        """Converts products to CSV format in a buffer, optionally including header."""
        header = "id,title,description,availability,status,condition,price,link,image_link,brand,sale_price"
        csv_lines = []

        if include_header:
            csv_lines.append(header)

        csv_lines.extend([product.data for product in products])
        csv_content = "\n".join(csv_lines)

        buffer = io.BytesIO()
        buffer.write(csv_content.encode("utf-8"))
        buffer.seek(0)

        print("CSV buffer successfully generated")
        return buffer

    def mark_products_as_sent(self, products: QuerySet):
        """Marks products as 'success' after successful upload."""
        product_ids = products.values_list("id", flat=True)
        UploadProduct.objects.filter(id__in=product_ids).update(status="success")
        print(f"{products.count()} products successfully marked as sent.")


class ProductUploader:
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, catalog: Catalog, update_products=True):
        self._fb_service = None
        self.catalog = catalog
        self.update_products = update_products
        self.batch_size = 30000  # Defines the maximum batch size for processing.
        self.fb_service = self.initialize_fb_service()
        self.product_manager = ProductUploadManager()
        self.feed_id = (
            catalog.feeds.first().facebook_feed_id
            if catalog.feeds.first().facebook_feed_id
            else None
        )

    def initialize_fb_service(self) -> FacebookService:
        app = self.catalog.app  # Wpp-cloud App
        access_token = app.apptype.get_access_token(app)
        fb_client = self.fb_client_class(access_token)
        return FacebookService(fb_client)

    def process_and_upload(self, redis_client, lock_key, lock_expiration_time):
        """Processes products in batches and uploads them to Meta, renewing the lock."""
        while True:
            products = self.product_manager.fetch_pending_products(
                self.catalog, self.batch_size
            )
            if not products.exists():
                print(f"No more pending products for catalog {self.catalog.name}.")
                break

            csv_content = self.product_manager.convert_to_csv(products)
            if self.send_to_meta(csv_content):
                self.product_manager.mark_products_as_sent(products)

            # Renew the lock
            redis_client.expire(lock_key, lock_expiration_time)
            print(f"Lock renewed for key: '{lock_key}'")

    def send_to_meta(self, csv_content: io.BytesIO) -> bool:
        """Sends the CSV content to Meta and returns the upload status."""
        try:
            upload_id_in_process = self.fb_service.uploads_in_progress(self.feed_id)
            if upload_id_in_process:
                print(
                    "There is already a feed upload in progress, waiting for completion."
                )
                self.fb_service._wait_for_upload_completion(
                    self.feed_id, upload_id_in_process
                )

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
            file_name = f"update_{current_time}_{self.catalog.name}"
            upload_id = self.fb_service.update_product_feed(
                self.feed_id, csv_content, file_name
            )
            upload_complete = self.fb_service._wait_for_upload_completion(
                self.feed_id, upload_id
            )
            if not upload_complete:
                print("Upload did not complete within the expected time frame.")
                return False

            print("Finished updating products to Facebook")
            return True
        except Exception as e:
            print(f"Error sending data to Meta: {e}")
            return False
