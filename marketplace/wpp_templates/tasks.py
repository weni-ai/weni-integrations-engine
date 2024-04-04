import logging

from celery import shared_task

from sentry_sdk import capture_exception

from marketplace.core.types import APPTYPES

from .models import TemplateMessage
from .requests import TemplateMessageRequest

from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    TemplateTranslation,
    TemplateHeader,
    TemplateButton,
)
from marketplace.clients.flows.client import FlowsClient

from .utils import WebhookEventProcessor


logger = logging.getLogger(__name__)


@shared_task(track_started=True, name="refresh_whatsapp_templates_from_facebook")
def refresh_whatsapp_templates_from_facebook():
    flows_client = FlowsClient()

    for app in App.objects.filter(code__in=["wpp", "wpp-cloud"]):
        if not (app.config.get("wa_waba_id") or app.config.get("waba")):
            continue

        waba_id = (
            app.config.get("waba").get("id")
            if app.config.get("waba")
            else app.config.get("wa_waba_id")
        )
        if app.code == "wpp" and app.config.get("fb_access_token"):
            access_token = app.config.get("fb_access_token")
        else:
            access_token = APPTYPES.get("wpp-cloud").get_access_token(app)

        template_message_request = TemplateMessageRequest(access_token=access_token)
        templates = template_message_request.list_template_messages(waba_id)

        if templates.get("error"):
            logger.error(
                f"A error occurred with waba_id: {waba_id}. \nThe error was:  {templates}\n"
            )
            continue

        templates = templates.get("data", [])
        try:
            flows_client.update_facebook_templates(str(app.flow_object_uuid), templates)
        except Exception as error:
            logger.error(
                f"An error occurred when sending facebook templates to flows: "
                f"App-{str(app.uuid)}, flows_object_uuid: {str(app.flow_object_uuid)} "
                f"Error: {error}"
            )

        if waba_id:
            delete_unexistent_translations(app, templates)

        for template in templates:
            try:
                translation = TemplateTranslation.objects.filter(
                    message_template_id=template.get("id"), template__app=app
                )
                if translation:
                    translation = translation.last()
                    found_template = translation.template
                else:
                    found_template, _created = TemplateMessage.objects.get_or_create(
                        app=app,
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
                    print(
                        f"Removing translation {translation.message_template_id}: {translation}"
                    )
                    translation.delete()

            if template.translations.all().count() == 0:
                print(f"Removing template after removing translations: {template}")
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
    for entry in webhook_data.get("entry", []):
        whatsapp_business_account_id = entry.get("id")
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value")
            if field in allowed_event_types:
                WebhookEventProcessor.process_event(
                    whatsapp_business_account_id, value, field
                )
            else:
                logger.info(f"Event: {field}, not mapped to usage")
