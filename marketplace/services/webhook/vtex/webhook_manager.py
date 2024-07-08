from django_redis import get_redis_connection

from marketplace.applications.models import App


class WebhookMultQueueManager:
    def __init__(self):
        self.redis_client = get_redis_connection()

    def reset_in_processing_keys(self):
        apps = App.objects.filter(code="vtex", config__initial_sync_completed=True)
        for app in apps:
            key = f"vtex:processing-lock:{str(app.uuid)}"
            if self.redis_client.get(key):
                self.redis_client.delete(key)
                print(f"{key} has deleted.")

    def list_in_processing_keys(self):
        apps = App.objects.filter(code="vtex", config__initial_sync_completed=True)
        for app in apps:
            key = f"vtex:processing-lock:{str(app.uuid)}"
            if self.redis_client.get(key):
                print(f"{key}")
