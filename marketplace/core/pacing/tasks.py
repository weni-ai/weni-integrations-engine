import logging

from celery import current_app, shared_task
from django.conf import settings

from marketplace.core.pacing.queue import RedisQueue


logger = logging.getLogger(__name__)


@shared_task(name="task_drain_paced_queue")
def task_drain_paced_queue(queue_key: str, item_task_name: str, budget: int):
    if budget <= 0:
        logger.warning(
            f"Drain budget is {budget} for queue {queue_key}, skipping drain."
        )
        return

    items = RedisQueue(queue_key).get_batch(budget)
    if not items:
        logger.debug(f"Paced queue {queue_key} is empty.")
        return

    queue_name = getattr(settings, "META_SYNC_CELERY_QUEUE", "meta-sync")
    for item in items:
        current_app.send_task(
            item_task_name,
            args=[item],
            queue=queue_name,
            ignore_result=True,
        )

    logger.info(
        f"Drained {len(items)} items from {queue_key} to {item_task_name} "
        f"(budget={budget}, queue={queue_name})."
    )
