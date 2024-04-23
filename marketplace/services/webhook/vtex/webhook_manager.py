import logging

from django.core.cache import cache
from django.conf import settings

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


class WebhookQueueManager:
    def __init__(self, app_uuid):
        self.app_uuid = app_uuid
        self.redis_client = get_redis_connection()

    def get_sku_list_key(self):
        return f"vtex:skus-list:{self.app_uuid}"

    def get_seller_list_key(self):
        return f"vtex:seller-list:{self.app_uuid}"

    def get_lock_key(self):
        return f"vtex:processing-lock:{self.app_uuid}"

    def get_lock_seller_key(self):
        return f"vtex:seller-processing-lock:{self.app_uuid}"

    def enqueue_webhook_data(self, sku_id, seller_id=None):
        if seller_id:
            seller_list_key = self.get_seller_list_key()
            seller_in_processing = cache.get(seller_list_key) or {}
            seller_skus = seller_in_processing.get(seller_id, [])

            if sku_id not in seller_skus:
                seller_skus.append(sku_id)
                seller_in_processing[seller_id] = seller_skus
                cache.set(seller_list_key, seller_in_processing, timeout=7200)
        else:
            skus_list_key = self.get_sku_list_key()
            skus_in_processing = cache.get(skus_list_key) or []

            if sku_id not in skus_in_processing:
                skus_in_processing.append(sku_id)
                cache.set(skus_list_key, skus_in_processing, timeout=7200)

    def dequeue_webhook_data(self, seller_id=None):
        batch_size = settings.VTEX_UPDATE_BATCH_SIZE
        if seller_id:
            self.dequeue_seller_list(batch_size, seller_id)
        else:
            self.dequeue_sku_list(batch_size)

    def dequeue_seller_list(self, batch_size, seller_id):
        seller_list_key = self.get_seller_list_key()
        seller_in_processing = cache.get(seller_list_key) or {}
        skus_in_processing = seller_in_processing.get(seller_id, [])

        if not skus_in_processing:
            return []

        try:
            # Select a subset of the SKUs to process, based on batch_size
            skus_to_process = set(skus_in_processing[:batch_size])

            # Calculate updated SKUs by removing those processed in this batch
            updated_skus_in_processing = skus_in_processing[len(skus_to_process) :]

            # Update the seller's SKU list in the cache
            if updated_skus_in_processing:
                seller_in_processing[seller_id] = updated_skus_in_processing
                cache.set(seller_list_key, seller_in_processing, timeout=7200)
            else:
                # Remove the seller's entry if no SKUs remain
                del seller_in_processing[seller_id]
                if seller_in_processing:
                    cache.set(seller_list_key, seller_in_processing, timeout=7200)
                else:
                    cache.delete(seller_list_key)

            self.redis_client.expire(self.get_lock_key(seller_id), 7200)
            return list(skus_to_process)

        except Exception as e:
            logger.error(
                f"Error on dequeue webhook data for seller_id {seller_id}: {e}"
            )
            # In case of error, restore the original SKUs for this seller
            seller_in_processing[seller_id] = skus_in_processing
            cache.set(seller_list_key, seller_in_processing, timeout=7200)
            return []

    def dequeue_sku_list(self, batch_size):
        skus_list_key = self.get_sku_list_key()
        initial_skus_in_processing = cache.get(skus_list_key) or []

        if not initial_skus_in_processing:
            return []

        try:
            # Select a subset of the SKUs to process, based on batch_size
            skus_to_process = set(initial_skus_in_processing[:batch_size])

            # Retrieves the current state of SKUs being processed from the cache
            current_skus_in_processing = set(cache.get(skus_list_key) or [])

            # Calculate updated SKUs by removing those processed in this batch
            updated_skus_in_processing = current_skus_in_processing - skus_to_process

            # Update the cache with the remaining SKUs after the current batch has been processed
            if updated_skus_in_processing:
                cache.set(skus_list_key, list(updated_skus_in_processing), timeout=7200)
            else:
                # If all SKUs have been processed and no items remain, remove the key from the cache
                cache.delete(skus_list_key)

            # Renew the lock expiration time to ensure it remains active
            self.redis_client.expire(self.get_lock_key(), 7200)

            return list(skus_to_process)

        except Exception as e:
            logger.error(f"Error on dequeue webhook data: {e}")
            # In case of error, try to put the original SKUs back into the cache for future attempts
            cache.set(skus_list_key, list(initial_skus_in_processing), timeout=7200)

    def is_processing_locked(self, seller_id=None):
        if seller_id:
            return bool(self.redis_client.get(self.get_lock_seller_key()))

        return bool(self.redis_client.get(self.get_lock_key()))
