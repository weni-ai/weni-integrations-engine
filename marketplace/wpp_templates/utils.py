import logging

from datetime import datetime

from marketplace.applications.models import App
from .models import TemplateMessage


logger = logging.getLogger(__name__)


class WebhookEventProcessor:
    @staticmethod
    def get_apps_by_waba_id(whatsapp_business_account_id):
        return App.objects.filter(config__wa_waba_id=whatsapp_business_account_id)

    @staticmethod
    def process_template_status_update(whatsapp_business_account_id, value):
        apps = WebhookEventProcessor.get_apps_by_waba_id(whatsapp_business_account_id)
        if not apps.exists():
            logger.info(
                f"There are no applications linked to waba: {whatsapp_business_account_id}"
            )
            return

        event = value.get("event")
        template_name = value.get("message_template_name")
        template_language = value.get("message_template_language")
        message_template_id = value.get("message_template_id")

        for app in apps:
            try:
                template = TemplateMessage.objects.filter(
                    app=app, name=template_name
                ).first()

                if template:
                    # Process template status update
                    translations = template.translations.filter(
                        language=template_language,
                        message_template_id=message_template_id,
                    )
                    for trans in translations:
                        # Update translation status based on event
                        if trans.status == event:
                            logger.info(
                                f"The template status: {event} is already updated for this App: {str(app.uuid)}"
                            )
                            continue

                        before_status = trans.status
                        trans.status = event
                        trans.save()
                        logger.info(
                            f"The template: {template.name}, translation: {trans.language}-{trans.message_template_id}"
                            f", was changed from {before_status} to {event} successfully"
                        )
                else:
                    logger.info(
                        f"Template {template_name}, id:{message_template_id}, not found for app {str(app.uuid)}."
                    )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing template status update by webhook for App {str(app.uuid)}: {e}"
                )

    @staticmethod
    def process_event(whatsapp_business_account_id, value, event_type):
        if event_type == "message_template_status_update":
            WebhookEventProcessor.process_template_status_update(
                whatsapp_business_account_id, value
            )
        elif event_type == "template_category_update":
            pass
        elif event_type == "message_template_quality_update":
            pass


def handle_error_and_update_config(app: App, error_data):
    error_code = error_data.get("code")
    error_subcode = error_data.get("error_subcode")

    if error_code == 100 and error_subcode == 33:
        app.config["ignores_meta_sync"] = {
            "last_error_date": datetime.now().isoformat(),
            "last_error_message": error_data.get("message"),
            "code": error_code,
            "error_subcode": error_subcode,
        }
        app.save()

        logger.info(
            f"Config updated to ignore future syncs for app {app.uuid} due to persistent errors."
        )
