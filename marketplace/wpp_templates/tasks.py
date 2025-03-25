import logging

from celery import shared_task

from marketplace.wpp_templates.usecases.template_library_creation import (
    TemplateCreationUseCase,
)
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)
from marketplace.wpp_templates.usecases.template_sync import TemplateSyncUseCase

from marketplace.applications.models import App

from .utils import WebhookEventProcessor


logger = logging.getLogger(__name__)


@shared_task(track_started=True, name="refresh_whatsapp_templates_from_facebook")
def refresh_whatsapp_templates_from_facebook():
    for app in App.objects.filter(code__in=["wpp", "wpp-cloud"]):
        try:
            if not (app.config.get("wa_waba_id") or app.config.get("waba")):
                continue

            if "ignores_meta_sync" in app.config:
                logger.info(
                    f"Skipping sync for app {app.uuid} based on previous error: {app.config['ignores_meta_sync']}"
                )
                continue

            service = TemplateSyncUseCase(app)
            service.sync_templates()

        except Exception as e:
            logger.error(f"Error processing app {app.uuid}: {str(e)}")


@shared_task(track_started=True, name="update_templates_by_webhook")
def update_templates_by_webhook(**kwargs):  # pragma: no cover
    allowed_event_types = [
        "message_template_status_update",
    ]
    webhook_data = kwargs.get("webhook_data")
    logger.info(f"Update templates by webhook data received: {webhook_data}")
    for entry in webhook_data.get("entry", []):
        whatsapp_business_account_id = entry.get("id")
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value")
            if value.get("reason", None) is None:
                value["reason"] = ""

            if field in allowed_event_types:
                WebhookEventProcessor.process_event(
                    whatsapp_business_account_id, value, field, webhook_data
                )
            else:
                logger.info(f"Event: {field}, not mapped to usage")

    logger.info("-" * 50)


@shared_task(track_started=True, name="task_create_library_templates_batch")
def task_create_library_templates_batch(app_uuid: str, template_data: dict):
    """
    Creates a library template message for the given app.

    Args:
        app_uuid (str): The UUID of the app.
        template_data (dict): The data of the template to be created.
    """
    logger.info(f"Creating library templates for app {app_uuid}")
    app = App.objects.get(uuid=app_uuid)

    use_case = TemplateCreationUseCase(app=app)
    use_case.create_library_template_messages_batch(template_data)

    logger.info(f"Library templates created for app {app_uuid}")


@shared_task(track_started=True, name="sync_pending_templates")
def sync_pending_templates(app_uuid: str):
    """
    Syncs pending templates for a specific app after batch creation.

    This task checks the approval status of templates and notifies
    the commerce module once all templates are processed.

    Args:
        app_uuid (str): UUID of the app to sync templates for.
    """
    logger.info(f"Starting sync of pending templates for app {app_uuid}")

    try:
        app = App.objects.get(uuid=app_uuid)
        use_case = TemplateLibraryStatusUseCase(app=app)

        stored_status = use_case._get_template_statuses_from_redis()
        if not stored_status:
            logger.info(f"No pending templates found for app {app_uuid}")
            return

        logger.info(f"Found {len(stored_status)} templates to check for app {app_uuid}")
        has_pending = False  # Flag to check if there are still pending templates

        # Forcing sync templates to get the latest status
        logger.info(f"Fetching templates from Facebook for app {app_uuid}")
        template_sync_use_case = TemplateSyncUseCase(app)
        template_sync_use_case.sync_templates()
        logger.info(f"Templates fetched from Facebook for app {app_uuid}")

        for template_name, status in stored_status.items():
            template = app.template.filter(name=template_name).first()
            if not template:
                logger.warning(f"Template {template_name} not found for app {app_uuid}")
                continue

            # Check if any translation is still pending
            pending_count = template.translations.filter(status="PENDING").count()
            if pending_count > 0:
                logger.info(
                    f"Template '{template_name}' still has {pending_count} pending translations for app {app_uuid}"
                )
                has_pending = True
                continue  # Don't update this template yet

            # If no pending translations, update the status
            logger.info(
                f"Updating status for template '{template_name}' to '{status}' for app {app_uuid}"
            )
            use_case.update_template_status(template_name, status)

        # If no more pending templates, trigger final synchronization
        if not has_pending:
            logger.info(
                f"No more pending templates found, triggering final synchronization for app {app_uuid}"
            )
            use_case.sync_all_templates()
        else:
            logger.info(
                f"Some templates are still pending for app {app_uuid}, skipping final synchronization"
            )

    except Exception as e:
        logger.error(f"Error syncing templates for app {app_uuid}: {str(e)}")
