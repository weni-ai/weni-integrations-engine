from celery import shared_task

from django.conf import settings
from sentry_sdk import capture_exception

from .models import TemplateMessage
from .requests import TemplateMessageRequest

from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    TemplateTranslation,
    TemplateHeader,
    TemplateButton,
)


def delete_unexistent_translations(app, templates):
    templates_message = app.template.all()
    templates_ids = [item["id"] for item in templates["data"]]

    for template in templates_message:
        template_translation = TemplateTranslation.objects.filter(
            template=template
        )
        for translation in template_translation:
            if translation.message_template_id not in templates_ids:
                print(
                    "Removed the translation",
                    translation,
                    "with message_template_id:",
                    translation.message_template_id,
                    "\n"
                )
                translation.delete()


@shared_task(track_started=True, name="refresh_whatsapp_templates_from_facebook")
def refresh_whatsapp_templates_from_facebook():
    for app in App.objects.filter(code__in=["wpp", "wpp-cloud"]):
        if not (app.config.get("wa_waba_id") or app.config.get("waba")):
            continue

        waba_id = (
            app.config.get("waba").get("id")
            if app.config.get("waba")
            else app.config.get("wa_waba_id")
        )
        template_message_request = TemplateMessageRequest(
            settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
        )
        templates = template_message_request.list_template_messages(waba_id)
        if templates.get("error"):
            print("A error occurred with waba_id: ", waba_id, "\nThe error was: ", templates, "\n")
            continue

        if waba_id:
            delete_unexistent_translations(app, templates)

        for template in templates.get("data", []):
            try:
                translation = TemplateTranslation.objects.filter(
                    message_template_id=template.get("id")
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
