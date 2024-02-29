import json

from django_redis import get_redis_connection


class WebhookQueueManager:
    def __init__(self, app_uuid, sku_id):
        self.app_uuid = app_uuid
        self.sku_id = sku_id
        self.redis_conn = get_redis_connection()

    def get_processing_key(self):
        return f"vtex:webhook_processing_product:{self.app_uuid}:{self.sku_id}"

    def enqueue_webhook_data(self, data):
        queue_key = f"vtex:webhook_queue:{self.app_uuid}:{self.sku_id}"
        self.redis_conn.set(queue_key, json.dumps(data))

    def dequeue_webhook_data(self):
        queue_key = f"vtex:webhook_queue:{self.app_uuid}:{self.sku_id}"
        data = self.redis_conn.get(queue_key)
        if data:
            self.redis_conn.delete(queue_key)
            return json.loads(data)
        return None

    def have_processing_product(self):
        return self.redis_conn.get(self.get_processing_key())
