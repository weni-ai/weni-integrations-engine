import logging

from django_redis import get_redis_connection
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from marketplace.celery import app as celery_app
from marketplace.clients.flows.client import FlowsClient
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_insights_delete_sync import (
    WhatsAppInsightsDeleteSyncUseCase,
)

logger = logging.getLogger(__name__)

User = get_user_model()


SYNC_WHATSAPP_CLOUD_LOCK_KEY = "sync-whatsapp-cloud-lock"


@celery_app.task(name="sync_whatsapp_cloud_apps")
def sync_whatsapp_cloud_apps():
    """Synchronize WhatsApp Cloud apps with Flows channels."""
    apptype = APPTYPES.get("wpp-cloud")
    client = FlowsClient()
    channels = client.list_channels(apptype.flows_type_code)
    redis = get_redis_connection()

    if redis.get(SYNC_WHATSAPP_CLOUD_LOCK_KEY):
        logger.info("The apps are already syncing by another task!")
        return None

    for channel in channels:
        try:
            _process_channel(channel, apptype)
        except Exception as e:
            logger.error(
                f"Error on processing sync_whatsapp_cloud_apps for channel {channel.get('uuid')}: {e}"
            )


def _process_channel(channel, apptype):
    """Process a single WhatsApp Cloud channel."""
    project_uuid = channel.get("project_uuid")
    uuid = channel.get("uuid")
    address = channel.get("address")
    is_active = channel.get("is_active")
    user = User.objects.get_admin_user()

    if project_uuid is None:
        logger.info(f"The channel {uuid} does not have a project_uuid.")
        return

    config = channel.get("config")
    config["title"] = config.get("wa_number")
    config["wa_phone_number_id"] = address

    apps = App.objects.filter(flow_object_uuid=uuid)

    if apps.exists():
        _handle_existing_app(apps.first(), is_active, apptype, config, user)
    else:
        _handle_new_app(is_active, uuid, project_uuid, config, apptype, user)


def _handle_existing_app(app, is_active, apptype, config, user):
    """Handle an existing app - update or delete."""
    if is_active is False:
        try:
            app.delete()
            WhatsAppInsightsDeleteSyncUseCase(app).sync()
        except Exception as e:
            logger.error(str(e))
        return

    if app.code != apptype.code:
        logger.info(f"Migrating an {app.code} to WhatsApp Cloud Type. App: {app.uuid}")
        app.code = apptype.code
        config["config_before_migration"] = app.config
        app.config = config
    else:
        app.config = config

    app.modified_by = user
    app.save()


def _handle_new_app(is_active, uuid, project_uuid, config, apptype, user):
    """Handle creation of a new app if needed."""
    if is_active is False:
        logger.info(
            f"Skipping creation of WhatsApp Cloud app for the flow_object_uuid: {uuid} (is_active=False)"
        )
        return

    logger.info(f"Creating a new WhatsApp Cloud app for the flow_object_uuid: {uuid}")
    apptype.create_app(
        created_by=user,
        project_uuid=project_uuid,
        flow_object_uuid=uuid,
        config=config,
    )


@celery_app.task(name="check_apps_uncreated_on_flow")
def check_apps_uncreated_on_flow():
    """Search all wpp-cloud channels that have the flow_object_uuid field empty,
    to create the object in flows"""
    apps = App.objects.filter(code="wpp-cloud", flow_object_uuid__isnull=True)

    for app in apps:
        if not app.config.get("wa_phone_number_id"):
            continue

        user_creation = app.created_by
        project_uuid = app.project_uuid
        # checking if the app creation user has access to the project
        if has_project_access(user_creation, app.project_uuid):
            app_config = app.config
            wa_phone_number_id = app.config.get("wa_phone_number_id")

            try:
                client = FlowsClient()
                channel = client.create_wac_channel(
                    user_creation.email, project_uuid, wa_phone_number_id, app_config
                )
                if not channel.get("uuid"):
                    logger.error(
                        f"The flow application was not created for app: {app.uuid} flows error return: {(channel)}"
                    )
                    continue

                app.flow_object_uuid = channel["uuid"]
                app.save()

            except Exception as e:
                logger.error(f"Error creating channel for app {app.uuid}: {str(e)}")
                continue

        else:
            logger.info(
                f"""ProjectAuthorization was not found for user: {str(user_creation)}
                    and project:{str(project_uuid)} on app: {str(app.uuid)}"""
            )
            continue


def has_project_access(user, project_uuid) -> bool:
    """Returns True if the creating user has access to the project"""
    user_has_access = ProjectAuthorization.objects.filter(
        user=user, project_uuid=project_uuid
    ).exists()
    return user_has_access
