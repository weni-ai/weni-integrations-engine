import logging
from typing import Optional

from django.conf import settings
from django_redis import get_redis_connection

from marketplace.celery import app as celery_app


logger = logging.getLogger(__name__)


class TemplateSyncScheduler:
    """Coalesces Meta template-sync requests so a burst of status webhooks
    for the same App results in a single sync."""

    def __init__(self, redis_conn=None, debounce_seconds: Optional[int] = None):
        self.redis_conn = redis_conn or get_redis_connection()
        self.debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.TEMPLATE_SYNC_DEBOUNCE_SECONDS
        )

    def schedule(self, app_uuid: str) -> bool:
        key = f"template_sync_scheduled:{app_uuid}"
        if not self.redis_conn.set(key, "1", nx=True, ex=self.debounce_seconds):
            logger.info(
                f"Template sync already scheduled for app {app_uuid}, skipping."
            )
            return False

        celery_app.send_task(
            name="task_sync_templates_from_meta",
            kwargs={"app_uuid": app_uuid},
            countdown=self.debounce_seconds,
        )
        return True
