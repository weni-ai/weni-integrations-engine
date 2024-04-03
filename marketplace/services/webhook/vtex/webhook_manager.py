import logging

from django.core.cache import cache
from django.conf import settings

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


class WebhookQueueManager:
    def __init__(self, app_uuid):
        self.app_uuid = app_uuid
        self.redis_client = get_redis_connection()

    def get_webhooks_key(self):
        return f"vtex:product-uploading:{self.app_uuid}"

    def get_sku_list_key(self):
        return f"vtex:skus-list:{self.app_uuid}"

    def get_lock_key(self):
        return f"vtex:processing-lock:{self.app_uuid}"

    def enqueue_webhook_data(self, sku_id, webhook):
        webhooks_key = self.get_webhooks_key()
        skus_list_key = self.get_sku_list_key()

        skus_in_processing = cache.get(skus_list_key) or []
        if sku_id not in skus_in_processing:
            skus_in_processing.append(sku_id)
            cache.set(skus_list_key, skus_in_processing, timeout=7200)

        # Update webhooks log
        webhooks_log = cache.get(webhooks_key) or {}
        if not webhooks_log:
            # Sets the log lifetime to 24 hours if it is the first entry
            cache.set(webhooks_key, {sku_id: webhook}, timeout=86400)
        else:
            webhooks_log[sku_id] = webhook
            cache.set(webhooks_key, webhooks_log)

    def dequeue_webhook_data(self):
        batch_size = settings.VTEX_UPDATE_BATCH_SIZE
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

    def is_processing_locked(self):
        return bool(self.redis_client.get(self.get_lock_key()))
