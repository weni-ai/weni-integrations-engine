import logging

from typing import Optional, List, Set
from celery import Celery

from marketplace.celery import app as _celery_app

from .base_on_demand import BaseSyncUseCase

logger = logging.getLogger(__name__)


class SyncOnDemandUseCase(BaseSyncUseCase):
    """
    High-priority (1) sync – uses Celery queue.
    """

    def __init__(self, celery_app: Optional[Celery] = None) -> None:
        super().__init__(priority=1)
        self.celery_app = celery_app or _celery_app

    def _dispatch_skus(
        self,
        *,
        app_uuid: str,
        celery_queue: str,
        skus_batch: List[str],
        salles_channel: Optional[str],
        invalid_skus: Set[str],  # Not used, but kept for compatibility
    ) -> None:
        """
        Send the task to Celery; does not return a result.
        """

        kwargs = {
            "app_uuid": app_uuid,
            "batch": skus_batch,
            "priority": self.priority,
        }
        if salles_channel:
            kwargs["salles_channel"] = salles_channel

        logger.info(
            f"Dispatching {skus_batch} to queue '{celery_queue}' "
            f"with priority {self.priority}"
        )

        self.celery_app.send_task(
            "task_update_webhook_batch_products",
            kwargs=kwargs,
            queue=celery_queue,
            ignore_result=True,
        )
