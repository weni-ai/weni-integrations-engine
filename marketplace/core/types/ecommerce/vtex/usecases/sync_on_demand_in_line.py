import logging

from typing import List, Optional, Set

from marketplace.wpp_products.tasks import task_update_webhook_batch_products


from .base_on_demand import BaseSyncUseCase


logger = logging.getLogger(__name__)


class SyncOnDemandInlineUseCase(BaseSyncUseCase):
    """
    Inline-priority (2) sync – runs synchronously and returns the outcome.
    """

    def __init__(self) -> None:
        super().__init__(priority=2)

    def _dispatch_skus(
        self,
        *,
        app_uuid: str,
        celery_queue: str,  # Not used, but kept for compatibility
        skus_batch: List[str],
        sales_channel: Optional[list[str]],
        invalid_skus: Set[str],
    ) -> dict:
        """
        Process the batch synchronously, returning the outcome.
        """
        kwargs = {
            "app_uuid": app_uuid,
            "batch": skus_batch,
            "priority": self.priority,
        }
        if sales_channel:
            kwargs["sales_channel"] = sales_channel

        logger.info(
            f"Processing inline sync for {skus_batch} (priority {self.priority}) – no Celery queue involved"
        )

        result = task_update_webhook_batch_products(**kwargs)
        return {
            "products": result,
            "invalid_skus": list(invalid_skus),
        }
