import logging
import ast

from datetime import datetime

from marketplace.applications.models import App
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.flows.service import FlowsService
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)

from .models import TemplateMessage


logger = logging.getLogger(__name__)


class WebhookEventProcessor:
    @staticmethod
    def get_apps_by_waba_id(whatsapp_business_account_id):
        return App.objects.filter(config__wa_waba_id=whatsapp_business_account_id)

    @staticmethod
    def process_template_status_update(whatsapp_business_account_id, value, webhook):
        apps = WebhookEventProcessor.get_apps_by_waba_id(whatsapp_business_account_id)
        if not apps.exists():
            logger.info(
                f"There are no applications linked to waba: {whatsapp_business_account_id}"
            )
            return

        status = value.get("event")
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
                    for translation in translations:
                        # Update translation status based on event
                        if translation.status == status:
                            logger.info(
                                f"The template status: {status} is already updated for this App: {str(app.uuid)}"
                            )
                            continue

                        before_status = translation.status
                        translation.status = status
                        translation.save()

                        try:
                            # Send to flows
                            flows_service = FlowsService(FlowsClient())
                            template_data = extract_template_data(translation)
                            flows_service.update_facebook_templates_webhook(
                                flow_object_uuid=str(app.flow_object_uuid),
                                template_data=template_data,
                                template_name=template_name,
                                webhook=webhook,
                            )
                            logger.info("Status update of template sent to flows.")

                            template_status_use_case = TemplateLibraryStatusUseCase(
                                app=app
                            )
                            template_status_use_case.update_template_status(
                                template_name=template_name,
                                new_status=status,
                            )
                            template_status_use_case.sync_all_templates()

                        except Exception as e:
                            logger.error(
                                f"Fail to sends template update: {template.name}, translation: {translation.language},"
                                f"translation ID: {translation.message_template_id}. Error: {e}"
                            )

                        logger.info(
                            f"The template: {template.name}, translation: {translation.language},"
                            f"translation ID: {translation.message_template_id},"
                            f"was changed from {before_status} to {status} successfully"
                        )

            except Exception as e:
                logger.error(
                    f"Unexpected error processing template status update by webhook for App {str(app.uuid)}: {e}"
                )

    @staticmethod
    def process_event(whatsapp_business_account_id, value, event_type, webhook):
        if event_type == "message_template_status_update":
            WebhookEventProcessor.process_template_status_update(
                whatsapp_business_account_id, value, webhook
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


def extract_template_data(translation):
    template = translation.template
    components = []

    # Headers
    headers = translation.headers.all()
    for header in headers:
        header_component = {"type": "HEADER", "format": header.header_type}
        if header.header_type != "TEXT" and header.example:
            try:
                # Try to convert an example string to a real list
                parsed_example = ast.literal_eval(header.example)
                if isinstance(parsed_example, list):
                    header_component["example"] = {"header_handle": parsed_example}
                else:
                    header_component["example"] = {"header_handle": [header.example]}
            except Exception:
                header_component["example"] = {"header_handle": [header.example]}
        else:
            header_component["text"] = (
                header.text if header.text else "No text provided"
            )
            if header.example:
                header_component["example"] = {"header_text": [header.example]}
        components.append(header_component)

    # Body
    if translation.body:
        body_component = {
            "type": "BODY",
            "text": translation.body,
        }
        components.append(body_component)

    # Footer
    if translation.footer:
        footer_component = {"type": "FOOTER", "text": translation.footer}
        components.append(footer_component)

    # Buttons
    buttons = translation.buttons.all()
    if buttons:
        buttons_component = {"type": "BUTTONS", "buttons": []}
        for button in buttons:
            button_component = {"type": button.button_type, "text": button.text}
            if button.url:
                button_component["url"] = button.url
            if button.phone_number:
                button_component[
                    "phone_number"
                ] = f"+{button.country_code} {button.phone_number}"

            buttons_component["buttons"].append(button_component)
        components.append(buttons_component)

    # Final result
    template_data = {
        "name": template.name,
        "components": components,
        "language": translation.language,
        "status": translation.status,
        "category": template.category,
        "id": str(translation.message_template_id),
    }

    return template_data
