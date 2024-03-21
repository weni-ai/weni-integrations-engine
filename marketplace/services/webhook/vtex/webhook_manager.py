from django.core.cache import cache

from django_redis import get_redis_connection


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
        cache.set(processing_key, webhooks_in_processing, timeout=3600)

    def dequeue_webhook_data(self):
        processing_key = self.get_app_processing_key()
        webhooks_in_processing = cache.get(processing_key) or {}

        if not webhooks_in_processing:
            return None

        # Process the first SKU in the queue and remove it from the list
        sku_id, webhook_data = webhooks_in_processing.popitem()
        cache.set(processing_key, webhooks_in_processing)
        return sku_id, webhook_data

    def is_processing_locked(self):
        return bool(self.redis_client.get(self.get_lock_key()))
