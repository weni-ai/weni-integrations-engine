import io
import logging
import json
import time

from typing import List, Dict, Any

from datetime import datetime, timezone

from django.db.models import QuerySet

from django_redis import get_redis_connection

from redis import exceptions

from sentry_sdk import configure_scope

from marketplace.clients.facebook.client import FacebookClient
from marketplace.clients.rapidpro.client import RapidproClient
from marketplace.services.rapidpro.service import RapidproService
from marketplace.wpp_products.models import (
    Catalog,
    ProductUploadLog,
    ProductValidation,
    UploadProduct,
)
from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.celery import app as celery_app


logger = logging.getLogger(__name__)


class ProductUploadManager:
    def mark_products_as_sent(self, product_ids: List[str]):
        updated_count = UploadProduct.objects.filter(
            facebook_product_id__in=product_ids, status="processing"
        ).update(status="success")

        print(f"{updated_count} products successfully marked as sent.")

    def mark_products_as_error(self, product_ids: List[str]):
        updated_count = UploadProduct.objects.filter(
            facebook_product_id__in=product_ids, status="processing"
        ).update(status="error")

        print(f"{updated_count} products marked as error.")


class ProductBatchFetcher(ProductUploadManager):
    def __init__(self, catalog, batch_size):
        self.catalog = catalog
        self.batch_size = batch_size

    def __iter__(self):
        return self

    def __next__(self):
        latest_products = UploadProduct.get_latest_products(
            catalog=self.catalog, status="pending", batch_size=self.batch_size
        )

        if not latest_products.exists():
            print(f"No more pending products for catalog {self.catalog.name}.")
            raise StopIteration

        product_ids = list(latest_products.values_list("id", flat=True))

        # Update status to "processing"
        UploadProduct.objects.filter(id__in=product_ids).update(status="processing")

        print(f"Products marked as processing: {len(product_ids)}")

        # Prepare the result as (products, facebook_product_ids)
        facebook_product_ids = list(
            latest_products.values_list("facebook_product_id", flat=True)
        )
        return latest_products, facebook_product_ids


def generate_log_with_file(csv_content: io.BytesIO, data, exception: Exception):
    """Generates a detailed log entry with the file content for debugging."""
    with configure_scope() as scope:
        scope.add_attachment(
            bytes=csv_content.getvalue(),
            filename=data.get("file_name", "upload.csv"),
            content_type="text/csv",
        )
        # Log the error with details
        logger.error(
            f"Error on upload feed to Meta: {exception}",
            exc_info=True,
            stack_info=True,
            extra=data,
        )


class SellerSyncUtils:
    @staticmethod
    def create_lock(app_uuid, sellers, expiration_time=86_400):
        redis_client = get_redis_connection()
        lock_key = f"sync-sellers:{app_uuid}"
        lock_value = json.dumps(
            {
                "app_uuid": app_uuid,
                "sellers": sellers,
                "start_time": datetime.now(timezone.utc).isoformat(),
            }
        )

        if redis_client.set(lock_key, lock_value, nx=True, ex=expiration_time):
            return lock_key
        else:
            return None

    @staticmethod
    def release_lock(app_uuid):
        redis_client = get_redis_connection()
        lock_key = f"sync-sellers:{app_uuid}"
        redis_client.delete(lock_key)

    @staticmethod
    def get_lock_data(lock_key):
        redis_client = get_redis_connection()
        lock_value = redis_client.get(lock_key)
        if lock_value:
            return json.loads(lock_value)
        else:
            return None


class UploadManager:
    @staticmethod
    def check_and_start_upload(app_uuid):
        redis_client = get_redis_connection()
        lock_upload_key = f"upload_lock:{app_uuid}"
        if not redis_client.exists(lock_upload_key):
            print(f"No active upload task for App: {app_uuid}, starting upload.")
            celery_app.send_task(
                "task_upload_vtex_products",
                kwargs={"app_vtex_uuid": app_uuid},
                queue="vtex-product-upload",
            )
        else:
            print(f"An upload task is already in progress for App: {app_uuid}.")


class ProductSyncMetaPolices:
    SYNC_META_POLICES_LOCK_KEY = "sync-meta-polices-lock"

    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self.app = catalog.app
        self.client = FacebookClient(self.app.apptype.get_system_access_token(self.app))
        self.redis = get_redis_connection()

    def sync_products_polices(self) -> None:
        if self.redis.get(self.SYNC_META_POLICES_LOCK_KEY):
            logger.error(
                "The catalogs are already syncing products polices by another task!"
            )
            return

        try:
            with self.redis.lock(self.SYNC_META_POLICES_LOCK_KEY, timeout=1200):
                wa_business_id = self.app.config.get("wa_business_id")
                wa_waba_id = self.app.config.get("wa_waba_id")

                if not (wa_business_id and wa_waba_id):
                    logger.warning(
                        f"Business ID or WABA ID missing for app: {self.app.uuid}"
                    )
                    return

                all_products = self._list_unapproved_products()
                try:
                    if all_products:
                        self._sync_local_products(all_products)
                except Exception as e:
                    logger.error(
                        f"Error during sync process for App {self.app.name}: {e}",
                        exc_info=True,
                        stack_info=True,
                    )
        except exceptions.LockError as e:
            logger.error(f"Failed to acquire or release lock: {e}")

    def _list_unapproved_products(self) -> List[Dict[str, Any]]:
        return self.client.list_unapproved_products(self.catalog.facebook_catalog_id)

    def _sync_local_products(self, all_products: List[Dict[str, Any]]) -> None:
        products_to_delete = []
        products_invalid = []
        for product in all_products:
            formated_product = self._product_data_info(product)
            try:
                retailer_id = formated_product["retailer_id"]
                if retailer_id:
                    products_to_delete.append(
                        {
                            "method": "DELETE",
                            "retailer_id": retailer_id,
                        }
                    )
                    products_invalid.append(formated_product)

            except Exception as e:
                logger.error(
                    f"Error creating catalog {self.catalog.facebook_catalog_id} for App: {str(e)}"
                )

        if products_to_delete:
            self._delete_products_in_batch(products_to_delete)
            self._save_invalid_products(products_invalid)

        logger.info(
            f"Success in synchronizing product polices for catalog: {self.catalog.name}"
        )

    def _delete_products_in_batch(
        self, products_to_delete: List[Dict[str, Any]]
    ) -> None:
        self.client.delete_products_in_batch(
            catalog_id=self.catalog.facebook_catalog_id,
            products_to_delete=products_to_delete,
        )

    def _save_invalid_products(self, products_invalid: List[Dict[str, Any]]) -> None:
        for product in products_invalid:
            sku_id = product.get("sku_id")
            catalog = self.catalog

            is_valid = (
                ProductValidation.objects.filter(sku_id=sku_id, catalog=catalog)
                .values_list("is_valid", flat=True)
                .first()
            )
            if is_valid is not None and not is_valid:
                logger.info(
                    f"SKU:{sku_id} is already invalid in the database for catalog: {catalog.name}"
                )
                continue

            rejection_reason = product.get("rejection_reason", "No reason")
            reason_str = f"{rejection_reason} - sync-tsk"

            # Use get_or_create to avoid duplication
            _, created = ProductValidation.objects.get_or_create(
                catalog=catalog,
                sku_id=sku_id,
                defaults={
                    "is_valid": False,
                    "classification": reason_str,
                    "description": f"Product rejected due to: {reason_str}",
                },
            )

            if created:
                logger.info(
                    f"SKU:{sku_id} has been saved as invalid for the first time in catalog: {catalog.name}"
                )
            else:
                logger.info(
                    f"SKU:{sku_id} already exists in the database "
                    f"for catalog: {catalog.name} and was not created again."
                )

    def _product_data_info(self, product: Dict[str, Any]) -> Dict[str, Any]:
        retailer_id = product.get("retailer_id")
        formated_product = {
            "id": product.get("id"),
            "rejection_reason": product.get("review_rejection_reasons"),
            "retailer_id": retailer_id,
            "sku_id": extract_sku_id(retailer_id),
        }
        return formated_product


def extract_sku_id(product_id: str) -> int:
    """Extract sku_id from facebook_product_id."""
    sku_part = product_id.split("#")[0]
    if sku_part.isdigit():
        return int(sku_part)
    else:
        raise ValueError(f"Invalid SKU ID, error: {sku_part} is not a number")


class ProductBatchUploader:
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, catalog: Catalog, batch_size=5000):
        self.catalog = catalog
        self.batch_size = batch_size
        self.fb_service = self.initialize_fb_service()
        self.product_manager = ProductBatchFetcher(catalog, batch_size)
        self.rapidpro_service = RapidproService(RapidproClient())

    def initialize_fb_service(self) -> FacebookService:
        app = self.catalog.app
        access_token = app.apptype.get_system_access_token(app)
        fb_client = self.fb_client_class(access_token)
        return FacebookService(fb_client)

    def process_and_upload(
        self, redis_client, lock_key: str, lock_expiration_time: int
    ):
        """
        Processes products in batches and uploads them to Meta, renewing the lock.
        """
        try:
            for products, product_ids in self.product_manager:
                # Creates the payload in the format required by the Meta
                payload = self.create_batch_payload(products)
                # Sends data to Meta and processes the results
                if self.send_to_meta(payload):
                    self.product_manager.mark_products_as_sent(product_ids)
                    self.log_sent_products(product_ids)
                else:
                    self.product_manager.mark_products_as_error(product_ids)

                # Renew the lock
                redis_client.expire(lock_key, lock_expiration_time)
        except Exception as e:
            logger.error(
                f"Error during 'process_and_upload' for {self.catalog.name}: {e}",
                exc_info=True,
                stack_info=True,
            )
            self.product_manager.mark_products_as_error(product_ids)
            try:
                # Send notification error to Rapidpro
                self.rapidpro_service.create_notification(
                    catalog=self.catalog,
                    incident_name=f"Error sending data to Meta to {self.catalog.name}",
                    exception=e,
                )
            except Exception as error:
                logger.error(
                    f"Error sending notification to Rapidpro for {self.catalog.name}: {error}",
                    exc_info=True,
                    stack_info=False,
                )

    def create_batch_payload(self, products: QuerySet) -> dict:
        """
        Creates a payload for the Meta Batch API from a list of products.
        """
        batch_requests = [
            {
                "method": "UPDATE",
                "data": product.data,
            }
            for product in products
        ]
        return {
            "item_type": "PRODUCT_ITEM",
            "requests": batch_requests,
        }

    def send_to_meta(self, products: List) -> bool:
        """
        Sends the payload to Meta and handles the response.
        """
        try:
            response = self.fb_service.upload_batch(
                self.catalog.facebook_catalog_id, products
            )

            if response.get("handles"):
                print(f"Batch upload successful for catalog {self.catalog.name}.")
                return True
            else:
                print(f"Batch upload failed for catalog {self.catalog.name}.")
                return False
        except Exception as e:
            logger.error(
                f"Error sending batch to Meta for catalog {self.catalog.name}: {e}",
                exc_info=True,
                stack_info=True,
            )
            return False

    def log_sent_products(self, product_ids: List[str]):
        """
        Logs the successfully sent products to the log table.
        """
        for product_id in product_ids:
            sku_id = extract_sku_id(product_id)
            ProductUploadLog.objects.create(
                sku_id=sku_id, vtex_app=self.catalog.vtex_app
            )
        print(f"Logged {len(product_ids)} products as sent.")


class RedisQueue:
    def __init__(self, queue_key):
        self.queue_key = queue_key
        self.redis = get_redis_connection()

    def insert(self, value):
        """Add an item to the ZSET queue with a timestamp score."""
        # Check if the item already exists
        if self.redis.zscore(self.queue_key, value) is not None:
            print(value, "already exists")
            return False  # Skip insertion if it exists

        # Add the item with the current timestamp as the score
        score = time.time()
        self.redis.zadd(self.queue_key, {value: score})
        self.redis.expire(self.queue_key, 3600 * 24)  # TTL of 24 hours
        return True

    def remove(self):
        """Remove and return the first item from the queue (FIFO)."""
        items = self.redis.zrange(
            self.queue_key, 0, 0, withscores=False
        )  # Get the first item
        if not items:
            return None
        self.redis.zrem(self.queue_key, items[0])  # Remove the first item
        return items[0].decode("utf-8")

    def order(self):
        """List all items in the queue in order."""
        items = self.redis.zrange(self.queue_key, 0, -1, withscores=False)
        return [item.decode("utf-8") for item in items]

    def length(self):
        """Returns the total number of items in the queue."""
        return self.redis.zcard(self.queue_key)

    def get_batch(self, batch_size):
        items = self.redis.zrange(self.queue_key, 0, batch_size - 1, withscores=False)
        if items:
            self.redis.zrem(self.queue_key, *items)
        return [item.decode("utf-8") for item in items]
