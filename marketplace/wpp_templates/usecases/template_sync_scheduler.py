import logging
from typing import Optional

from django.conf import settings
from django_redis import get_redis_connection

from marketplace.celery import app as celery_app


logger = logging.getLogger(__name__)

# Consumes the rerun flag without releasing the reservation first. Releasing
# it and then calling schedule() lets a webhook win the NX key and mark
# another rerun, which queues a sync the follow-up task already covers.
_CLAIM_FOLLOW_UP_SCRIPT = """
local scheduled_key = KEYS[1]
local rerun_key = KEYS[2]
local ttl = tonumber(ARGV[1])

if redis.call('DEL', rerun_key) == 1 then
  redis.call('SET', scheduled_key, '1', 'EX', ttl)
  return 1
end
redis.call('DEL', scheduled_key)
return 0
"""


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
        reservation_ttl = self._reservation_ttl()
        if not self.redis_conn.set(
            self._scheduled_key(app_uuid),
            "1",
            nx=True,
            ex=reservation_ttl,
        ):
            self._mark_rerun(app_uuid, reservation_ttl)
            logger.info(
                f"Template sync already scheduled for app {app_uuid}, skipping."
            )
            return False

        self._enqueue(app_uuid)
        return True

    def finish(self, app_uuid: str) -> None:
        """Releases the reservation. When a webhook arrived while it was held,
        keeps the reservation and enqueues one follow-up sync."""
        if self._claim_follow_up(app_uuid):
            self._enqueue(app_uuid)

    def _enqueue(self, app_uuid: str) -> None:
        celery_app.send_task(
            name="task_sync_templates_from_meta",
            kwargs={"app_uuid": app_uuid},
            countdown=self.debounce_seconds,
        )

    def _claim_follow_up(self, app_uuid: str) -> bool:
        claimed = self.redis_conn.eval(
            _CLAIM_FOLLOW_UP_SCRIPT,
            2,
            self._scheduled_key(app_uuid),
            self._rerun_key(app_uuid),
            self._reservation_ttl(),
        )
        return bool(claimed)

    def _reservation_ttl(self) -> int:
        """Outlives the Celery countdown so the key is still held when the
        task becomes due. finish() releases it when the sync ends, unless
        it claims a follow-up."""
        return self.debounce_seconds * 2

    def _mark_rerun(self, app_uuid: str, reservation_ttl: int) -> None:
        self.redis_conn.set(self._rerun_key(app_uuid), "1", ex=reservation_ttl)

    def _scheduled_key(self, app_uuid: str) -> str:
        return f"template_sync_scheduled:{app_uuid}"

    def _rerun_key(self, app_uuid: str) -> str:
        return f"template_sync_rerun:{app_uuid}"
