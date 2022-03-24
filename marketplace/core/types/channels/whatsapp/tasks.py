import json
import logging

from django.conf import settings
from django_redis import get_redis_connection

from marketplace.celery import app as celery_app
from marketplace.grpc.client import ConnectGRPCClient
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App

from django.contrib.auth import get_user_model


User = get_user_model()
logger = logging.getLogger(__name__)


SYNC_WHATSAPP_LOCK_KEY = "sync-whatsapp-lock"


@celery_app.task(name="sync_whatsapp_apps")
def sync_whatsapp_apps():
    apptype = APPTYPES.get("wpp")
    response = ConnectGRPCClient().list_channels(apptype.channeltype_code)

    redis = get_redis_connection()

    if redis.get(SYNC_WHATSAPP_LOCK_KEY):
        logger.info("The apps are already syncing by another task!")
        return None

    else:
        with redis.lock(SYNC_WHATSAPP_LOCK_KEY):
            for channel in response:
                channel_config = json.loads(channel.config)

                # Skipping WhatsApp demo channels, change to environment variable later
                if "558231420933" in channel.address:
                    continue

                config = {"title": channel.address}
                config.update(channel_config)

                app, created = App.objects.get_or_create(
                    code=apptype.code,
                    platform=apptype.platform,
                    project_uuid=channel.project_uuid,
                    flow_channel=channel.uuid,
                    defaults=dict(config=config, created_by=User.objects.get_admin_user()),
                )

                if created:
                    logger.info(f"A new whatsapp app was created automatically. UUID: {app.uuid}")
