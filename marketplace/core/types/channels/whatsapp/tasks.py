import time
import logging

from django.conf import settings
from django_redis import get_redis_connection

from marketplace.celery import app as celery_app
from .facades import InfrastructureQueueFacade, InfrastructureQueueItem

logger = logging.getLogger(__name__)


# TODO: Create a task that validates if old queue item are deployed


@celery_app.task(name="manage_queue_size")
def manage_queue_size():
    queue = InfrastructureQueueFacade()

    queue_size = len(queue.items)
    infra_amount = settings.WHATSAPP_INFRASTRUCTURE_AMOUNT

    logger.info(f"Whatsapp infrastructure queue size: {queue_size}")

    if queue_size < infra_amount:
        redis = get_redis_connection()

        if redis.get("infra-lock"):
            logger.info(f"Waiting for the last infrastructure to be fully deployed")
            return None
        else:
            with redis.lock("infra-lock"):
                queue_item = InfrastructureQueueItem()
                queue.deploy_whatsapp(queue_item)

                logger.info(f"Deploying a new infrastructure whose `uid` is {queue_item.uid}")
                time.sleep(settings.WHATSAPP_TIME_BETWEEN_DEPLOY_INFRASTRUCTURE)


@celery_app.task(name="manage_infra_queue_status")
def manage_infra_queue_status():
    queue = InfrastructureQueueFacade()

    for queue_item in queue.items.all():

        if queue_item.status == InfrastructureQueueItem.STATUS_PROPAGATING:
            logger.info(f"Validando se propagou")
