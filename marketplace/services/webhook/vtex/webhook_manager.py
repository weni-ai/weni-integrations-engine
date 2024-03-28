import logging

from django.core.cache import cache

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


class WebhookQueueManager:
    def __init__(self, app_uuid):
        self.app_uuid = app_uuid
        self.redis_client = get_redis_connection()

    def get_app_processing_key(self):
        return f"vtex:product-uploading:{self.app_uuid}"

    def get_lock_key(self):
        return f"vtex:processing-lock:{self.app_uuid}"

    def enqueue_webhook_data(self, sku_id, data):
        processing_key = self.get_app_processing_key()
        webhooks_in_processing = cache.get(processing_key) or {}

        # Update or add the webhook for the specific SKU
        webhooks_in_processing[sku_id] = data
        cache.set(processing_key, webhooks_in_processing, timeout=7200)

    def dequeue_webhook_data(self):
        processing_key = self.get_app_processing_key()
        webhooks_in_processing = cache.get(processing_key) or {}
        cache.delete(processing_key)

        if not webhooks_in_processing:
            return []

        try:
            all_skus = list(webhooks_in_processing.keys())
            self.redis_client.expire(self.get_lock_key(), 7200)
            return all_skus

        except Exception as e:
            logger.error(f"Error on dequeue webhook data: {e}")
            logger.info(f"Returning cache value to: {processing_key}")
            cache.set(processing_key, webhooks_in_processing, timeout=7200)

    def is_processing_locked(self):
        return bool(self.redis_client.get(self.get_lock_key()))
