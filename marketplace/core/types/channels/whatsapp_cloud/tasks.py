import logging

from django_redis import get_redis_connection
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from marketplace.celery import app as celery_app
from marketplace.connect.client import ConnectProjectClient
from marketplace.applications.models import App


logger = logging.getLogger(__name__)

User = get_user_model()


SYNC_WHATSAPP_CLOUD_LOCK_KEY = "sync-whatsapp-cloud-lock"


@celery_app.task(name="sync_whatsapp_cloud_apps")
def sync_whatsapp_cloud_apps():
    apptype = APPTYPES.get("wpp-cloud")
    client = ConnectProjectClient()
    channels = client.list_channels(apptype.channeltype_code)

    redis = get_redis_connection()

    if redis.get(SYNC_WHATSAPP_CLOUD_LOCK_KEY):
        logger.info("The apps are already syncing by another task!")
        return None

    for channel in channels:

        project_uuid = channel.get("project_uuid")

        uuid = channel.get("uuid")
        address = channel.get("address")
        user = User.objects.get_admin_user()

        config = channel.get("config")
        config["title"] = config.get("wa_number")
        config["wa_phone_number_id"] = address

        apps = App.objects.filter(flow_object_uuid=uuid)

        if apps.exists():
            app = apps.first()

            if app.code != apptype.code:
                logger.info(f"Migrating an {app.code} to WhatsApp Cloud Type. App: {app.uuid}")
                app.code = apptype.code
                config["config_before_migration"] = app.config
                app.config = config
            else:
                app.config.update(config)

            app.modified_by = user
            app.save()

        else:
            logger.info(f"Creating a new WhatsApp Cloud app for the flow_object_uuid: {uuid}")
            apptype.create_app(
                created_by=user,
                project_uuid=project_uuid,
                flow_object_uuid=uuid,
                config=config,
            )
