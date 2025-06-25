import logging
from django.contrib.auth import get_user_model
from marketplace.celery import app as celery_app
from marketplace.clients.flows.client import FlowsClient
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types.channels.whatsapp_cloud.factories import create_account_update_webhook_event_processor
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync import (
    SyncWhatsAppCloudAppsUseCase,
)

logger = logging.getLogger(__name__)

User = get_user_model()


@celery_app.task(name="sync_whatsapp_cloud_apps")
def sync_whatsapp_cloud_apps():
    """Synchronize WhatsApp Cloud apps with Flows channels."""
    use_case = SyncWhatsAppCloudAppsUseCase()
    return use_case.execute()


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


@celery_app.task(name="update_account_info_by_webhook")
def update_account_info_by_webhook(**kwargs):  # pragma: no cover
    """Update the mmlite status of the app based on the webhook data"""
    allowed_event_types = ["account_update"]
    webhook_data = kwargs.get("webhook_data")

    logger.info(f"Update mmlite status by webhook data received: {webhook_data}")

    processor = create_account_update_webhook_event_processor()

    for entry in webhook_data.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value")
            if value.get("reason", None) is None:
                value["reason"] = ""

            whatsapp_business_account_id = value.get("waba_info", {}).get("waba_id")
            if not whatsapp_business_account_id:
                logger.info(f"Whatsapp business account id not found in webhook data: {webhook_data}")
                continue

            if field in allowed_event_types:
                processor.process_event(
                    whatsapp_business_account_id, value, field, webhook_data
                )
            else:
                logger.info(f"Event: {field}, not mapped to usage")

    logger.info("-" * 50)


def has_project_access(user, project_uuid) -> bool:
    """Returns True if the creating user has access to the project"""
    user_has_access = ProjectAuthorization.objects.filter(
        user=user, project_uuid=project_uuid
    ).exists()
    return user_has_access
