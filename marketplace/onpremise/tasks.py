import time
import logging

import requests
from django.conf import settings
from django_redis import get_redis_connection
from requests.exceptions import ConnectionError

from marketplace.celery import app as celery_app
from .facades import OnPremiseQueueFacade, QueueItem
from .exceptions import ItemAlreadyInQueue

logger = logging.getLogger(__name__)


# TODO: Create a task that validates if old queue item are deployed
# TODO: Create a task to remove failed items


@celery_app.task(name="manage_queue_size")
def manage_queue_size():
    queue = OnPremiseQueueFacade()

    queue_size = len(queue.items)
    infra_amount = settings.WHATSAPP_INFRASTRUCTURE_AMOUNT

    logger.info(f"Whatsapp infrastructure queue size: {queue_size}")

    if queue_size < infra_amount:
        redis = get_redis_connection()

        if redis.get("infra-lock"):
            logger.info("Waiting for the last infrastructure to be fully deployed")
            return None
        else:
            with redis.lock("infra-lock"):
                try:
                    queue_item = QueueItem()
                    queue.deploy_whatsapp(queue_item)
                    logger.info(f"Deploying a new infrastructure whose `uid` is {queue_item.uid}")
                    time.sleep(settings.WHATSAPP_TIME_BETWEEN_DEPLOY_INFRASTRUCTURE)
                except ItemAlreadyInQueue:
                    pass


@celery_app.task(name="manage_infra_queue_status")
def manage_infra_queue_status():

    queue = OnPremiseQueueFacade()

    for item in queue.items.all():
        if item.status != QueueItem.STATUS_PROPAGATING:
            continue

        logger.info(f"Validating if infrastructure with uid `{item.uid}` has already propagated")
        try:
            response = requests.get(item.url)
            if response.status_code < 400:
                queue.items.update(item, status=QueueItem.STATUS_DONE)
                logger.info(f"Infrastructure with uid `{item.uid}` has been propagated and is ready to use")
        except ConnectionError:
            continue
