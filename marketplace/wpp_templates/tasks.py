import logging

from celery import shared_task

from sentry_sdk import capture_exception

from marketplace.wpp_templates.usecases.template_library_creation import (
    TemplateCreationUseCase,
)
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)

from .models import TemplateMessage

from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    TemplateTranslation,
    TemplateHeader,
    TemplateButton,
)
from marketplace.clients.flows.client import FlowsClient
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import TemplateService

from .utils import WebhookEventProcessor, handle_error_and_update_config


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

            service = FacebookTemplateSyncService(app)
            service.sync_templates()

        except Exception as e:
            logger.error(f"Error processing app {app.uuid}: {str(e)}")


class FacebookTemplateSyncService:
    def __init__(self, app):
        self.app = app
        try:
            access_token = app.apptype.get_access_token(app)
            self.template_service = TemplateService(client=FacebookClient(access_token))
        except ValueError as e:
            logger.error(f"Access token error for app {app.uuid}: {str(e)}")
            raise

        self.flows_client = FlowsClient()

    def sync_templates(self):
        waba_id = (
            self.app.config.get("waba").get("id")
            if self.app.config.get("waba")
            else self.app.config.get("wa_waba_id")
        )

        templates = self.template_service.list_template_messages(waba_id)

        if templates.get("error"):
            template_error = templates["error"]
            logger.error(
                f"A error occurred with waba_id: {waba_id}. \nThe error was:  {template_error}\n"
            )
            handle_error_and_update_config(self.app, template_error)
            return

        templates = templates.get("data", [])
        try:
            self.flows_client.update_facebook_templates(
                str(self.app.flow_object_uuid), templates
            )
        except Exception as error:
            logger.error(
                f"An error occurred when sending facebook templates to flows: "
                f"App-{str(self.app.uuid)}, flows_object_uuid: {str(self.app.flow_object_uuid)} "
                f"Error: {error}"
            )

        if waba_id:
            delete_unexistent_translations(self.app, templates)

        for template in templates:
            try:
                translation = TemplateTranslation.objects.filter(
                    message_template_id=template.get("id"), template__app=self.app
                )
                if translation:
                    translation = translation.last()
                    found_template = translation.template
                else:
                    found_template, _created = TemplateMessage.objects.get_or_create(
                        app=self.app,
                        name=template.get("name"),
                    )

                found_template.category = template.get("category")
                found_template.save()

                body = ""
                footer = ""
                for translation in template.get("components"):
                    if translation.get("type") == "BODY":
                        body = translation.get("text", "")

                    if translation.get("type") == "FOOTER":
                        footer = translation.get("text", "")

                (
                    returned_translation,
                    _created,
                ) = TemplateTranslation.objects.get_or_create(
                    template=found_template,
                    language=template.get("language"),
                )
                returned_translation.body = body
                returned_translation.footer = footer
                returned_translation.status = template.get("status")
                returned_translation.variable_count = 0
                returned_translation.message_template_id = template.get("id")
                returned_translation.save()

                for translation in template.get("components"):
                    if translation.get("type") == "HEADER":
                        (
                            returned_header,
                            _created,
                        ) = TemplateHeader.objects.get_or_create(
                            translation=returned_translation,
                            header_type=translation.get("format"),
                        )
                        returned_header.text = translation.get("text", {})
                        returned_header.example = translation.get("example", {}).get(
                            "header_handle"
                        )
                        returned_header.save()

                    if translation.get("type") == "BUTTONS":
                        for button in translation.get("buttons"):
                            (
                                _returned_button,
                                _created,
                            ) = TemplateButton.objects.get_or_create(
                                translation=returned_translation,
                                button_type=button.get("type"),
                                text=button.get("text"),
                                url=button.get("url"),
                                phone_number=button.get("phone_number"),
                            )

            except Exception as error:
                capture_exception(error)
                continue

        print(f"Completed template update for app {str(self.app.uuid)}")


def delete_unexistent_translations(app, templates):
    templates_message = app.template.all()
    templates_ids = [item["id"] for item in templates]

    for template in templates_message:
        try:
            template_translation = TemplateTranslation.objects.filter(template=template)
            if not template_translation:
                print(f"Removing template without translation: {template}")
                template.delete()
                continue

            for translation in template_translation:
                if translation.message_template_id not in templates_ids:
                    translation_language = (
                        translation.language if translation.language else "No language"
                    )
                    print(
                        f"Removing translation {translation.message_template_id}: {translation_language}"
                    )
                    translation.delete()

            if template.translations.all().count() == 0:
                temaplte_name = template.name if template.name else "No name"
                print(f"Removing template:{temaplte_name} after removing translations")
                template.delete()

        except Exception as e:
            logger.error(
                f"An error occurred 'on delete_unexistent_translations()': {e}"
            )
            continue


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
        logger.info(f"Initializing TemplateLibraryStatusUseCase for app {app_uuid}")
        use_case = TemplateLibraryStatusUseCase(app=app)

        stored_status = use_case._get_template_statuses_from_redis()
        if not stored_status:
            logger.info(f"No pending templates found for app {app_uuid}")
            return

        logger.info(f"Found {len(stored_status)} templates to check for app {app_uuid}")
        has_pending = False  # Flag to check if there are still pending templates

        # Forcing sync templates to get the latest status
        logger.info(
            f"Forcing template synchronization with Facebook for app {app_uuid}"
        )
        service = FacebookTemplateSyncService(app)
        service.sync_templates()

        for template_name, status in stored_status.items():
            logger.info(
                f"Checking template '{template_name}' with status '{status}' for app {app_uuid}"
            )
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
