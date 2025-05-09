import logging
import ast

from typing import Callable, Optional, TYPE_CHECKING

from marketplace.applications.models import App
from .models import TemplateMessage, TemplateTranslation


if TYPE_CHECKING:  # pragma: no cover
    from marketplace.services.flows.service import FlowsService
    from marketplace.services.commerce.service import CommerceService
    from marketplace.wpp_templates.usecases.template_library_status import (
        TemplateLibraryStatusUseCase,
    )


class TemplateStatusUpdateHandler:
    def __init__(
        self,
        flows_service: "FlowsService",
        commerce_service: "CommerceService",
        status_use_case_factory: Callable[[App], "TemplateLibraryStatusUseCase"],
        logger: Optional[logging.Logger] = None,
    ):
        self.flows_service = flows_service
        self.commerce_service = commerce_service
        self.status_use_case_factory = status_use_case_factory
        self.logger = logger or logging.getLogger(__name__)

    def handle(
        self,
        app: App,
        template: TemplateMessage,
        translation: TemplateTranslation,
        status: str,
        webhook: dict,
        raw_data: dict,
    ) -> None:
        """
        Handles the processing of a single template translation status update.

        This method:
        - Updates the status locally if needed.
        - Sends the update to external systems (Commerce and Flows).
        - Updates the internal template library use case status.
        """

        status_changed = False
        # Check if the status has changed; update locally if needed
        if translation.status != status:
            before_status = translation.status
            translation.status = status
            translation.save()
            status_changed = True

            self.logger.info(
                f"The template: {template.name}, translation: {translation.language}, "
                f"translation ID: {translation.message_template_id}, "
                f"was changed from {before_status} to {status} successfully"
            )
        else:
            self.logger.info(
                f"The template status: {status} is already updated for App: {str(app.uuid)}. "
                f"Proceeding with external notifications."
            )

        # Prepare template data for external systems
        template_data = extract_template_data(translation)

        # Always notify Commerce if gallery version is defined
        if template.gallery_version:
            try:
                self.commerce_service.send_gallery_template_version(
                    gallery_version_uuid=str(template.gallery_version), status=status
                )
                self.logger.info(
                    f"[Commerce] Gallery version {template.gallery_version} for template: {template.name}, "
                    f"translation: {translation.language}, status: {status} sent successfully."
                )
            except Exception as e:
                self.logger.error(
                    f"[Commerce] Failed to send gallery version for template: {template.name}, "
                    f"translation: {translation.language}, status: {status}, error: {e}"
                )

        # Always notify Flows
        try:
            self.flows_service.update_facebook_templates_webhook(
                flow_object_uuid=str(app.flow_object_uuid),
                template_data=template_data,
                template_name=template.name,
                webhook=webhook,
            )
            self.logger.info("[Flows] Template update sent to Flows.")
        except Exception as e:
            self.logger.error(
                f"[Flows] Failed to send template update: {template.name}, "
                f"translation: {translation.language}, error: {e}"
            )

        # Always update local use case (even if status didn't change)
        try:
            use_case = self.status_use_case_factory(app)
            use_case.update_template_status(
                template_name=template.name,
                new_status=status,
            )
            use_case.synchronize_all_stored_templates()
            self.logger.info("[StatusSync] Template library status updated.")
        except Exception as e:
            self.logger.error(
                f"[StatusSync] Failed to update template library status for: {template.name}. Error: {e}"
            )

        # Final log if status was already up to date
        if not status_changed:
            self.logger.info(
                f"The template: {template.name}, translation: {translation.language}, "
                f"translation ID: {translation.message_template_id}, "
                f"was notified again with same status: {status}."
            )


class WebhookEventProcessor:
    def __init__(
        self,
        handler: TemplateStatusUpdateHandler,
        logger: Optional[logging.Logger] = None,
    ):
        self.handler = handler
        self.logger = logger or logging.getLogger(__name__)

    def get_apps_by_waba_id(self, waba_id: str):
        return App.objects.filter(config__wa_waba_id=waba_id)

    def process_template_status_update(
        self, waba_id: str, value: dict, webhook: dict
    ) -> None:
        apps = self.get_apps_by_waba_id(waba_id)
        if not apps.exists():
            self.logger.info(f"There are no applications linked to waba: {waba_id}")
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
                if not template:
                    continue

                translations = template.translations.filter(
                    language=template_language,
                    message_template_id=message_template_id,
                )
                for translation in translations:
                    self.handler.handle(
                        app, template, translation, status, webhook, value
                    )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error processing template status update for App {str(app.uuid)}: {e}"
                )

    def process_event(
        self, waba_id: str, value: dict, event_type: str, webhook: dict
    ) -> None:
        if event_type == "message_template_status_update":
            self.process_template_status_update(waba_id, value, webhook)


def extract_template_data(translation: TemplateTranslation) -> dict:
    template = translation.template
    components = []

    headers = translation.headers.all()
    for header in headers:
        header_component = {"type": "HEADER", "format": header.header_type}
        if header.header_type != "TEXT" and header.example:
            try:
                parsed_example = ast.literal_eval(header.example)
                header_component["example"] = {
                    "header_handle": parsed_example
                    if isinstance(parsed_example, list)
                    else [header.example]
                }
            except Exception:
                header_component["example"] = {"header_handle": [header.example]}
        else:
            header_component["text"] = header.text or "No text provided"
            if header.example:
                header_component["example"] = {"header_text": [header.example]}
        components.append(header_component)

    if translation.body:
        components.append({"type": "BODY", "text": translation.body})

    if translation.footer:
        components.append({"type": "FOOTER", "text": translation.footer})

    buttons = translation.buttons.all()
    if buttons:
        button_list = []
        for button in buttons:
            b = {"type": button.button_type, "text": button.text}
            if button.url:
                b["url"] = button.url
            if button.phone_number:
                b["phone_number"] = f"+{button.country_code} {button.phone_number}"
            button_list.append(b)
        components.append({"type": "BUTTONS", "buttons": button_list})

    return {
        "name": template.name,
        "components": components,
        "language": translation.language,
        "status": translation.status,
        "category": template.category,
        "id": str(translation.message_template_id),
    }
