import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection

from marketplace.celery import app as celery_app
from marketplace.grpc.client import ConnectGRPCClient
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App
from .apis import FacebookWABAApi
from .exceptions import FacebookApiException


User = get_user_model()
logger = logging.getLogger(__name__)


SYNC_WHATSAPP_LOCK_KEY = "sync-whatsapp-lock"
SYNC_WHATSAPP_WABA_LOCK_KEY = "sync-whatsapp-waba-lock-app:{app_uuid}"


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
                    flow_object_uuid=channel.uuid,
                    defaults=dict(config=config, created_by=User.objects.get_admin_user()),
                )

                if created:
                    logger.info(f"A new whatsapp app was created automatically. UUID: {app.uuid}")

                if app.config.get("auth_token") != config.get("auth_token"):
                    app.config["auth_token"] = config.get("auth_token")
                    app.updated_by = User.objects.get_admin_user()
                    app.save()


@celery_app.task(name="sync_whatsapp_wabas")
def sync_whatsapp_wabas():
    apptype = APPTYPES.get("wpp")
    redis = get_redis_connection()

    for app in apptype.apps:
        key = SYNC_WHATSAPP_WABA_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            config = app.config
            access_token = config.get("fb_access_token", None)
            business_id = config.get("fb_business_id", None)

            if access_token is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_access_token`. UUID: {app.uuid}")
                continue

            if business_id is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_business_id`. UUID: {app.uuid}")
                continue

            logger.info(f"Syncing app WABA. UUID: {app.uuid}")

            api = FacebookWABAApi(access_token)

            try:
                waba = api.get_waba(business_id)
                app.config["waba"] = waba
                app.modified_by = User.objects.get_admin_user()
                app.save()

                redis.set(key, "synced", settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS)
            except FacebookApiException as error:
                logger.error(f"An error occurred while trying to sync the app. UUID: {app.uuid}. Error: {error}")
                continue

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )
