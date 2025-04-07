import logging
from django.contrib.auth import get_user_model
from marketplace.celery import app as celery_app
from marketplace.clients.flows.client import FlowsClient
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
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


def has_project_access(user, project_uuid) -> bool:
    """Returns True if the creating user has access to the project"""
    user_has_access = ProjectAuthorization.objects.filter(
        user=user, project_uuid=project_uuid
    ).exists()
    return user_has_access
