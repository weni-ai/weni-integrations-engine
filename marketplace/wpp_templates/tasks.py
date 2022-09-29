from celery import shared_task

from django.conf import settings

from .models import TemplateMessage
from .requests import TemplateMessageRequest

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation, TemplateHeader, TemplateButton


@shared_task(track_started=True, name="refresh_whatsapp_templates_from_facebook")
def refresh_whatsapp_templates_from_facebook():

    for app in App.objects.all():

        if not app.config.get("wa_waba_id"):
            continue

        template_message_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        templates = template_message_request.list_template_messages(app.config.get("wa_waba_id"))

        namespace = template_message_request.get_template_namespace(app.config.get("wa_waba_id"))


        for template in templates.get("data", []):

            found_template, created = TemplateMessage.objects.get_or_create(
                app=app,
                name=template.get("name"),
                category=template.get("category"),
            )

            print(created)

            body = ""
            footer = ""
            variable_count = 0
            country = ""
            namespace = ""

            for translation in template.get("components"):
                if translation.get("type") == "BODY":
                    body = translation.get("text", "")

                if translation.get("type") == "FOOTER":
                    footer = translation.get("text", "")

            returned_translation, created = TemplateTranslation.objects.get_or_create(
                template=found_template,
                #status=template.get("status"),
                language=template.get("language"),
                #external_id=template.get("id"),
                #body=body,
                #footer=footer,
                #variable_count=variable_count,
                #country=country,
                #namespace=namespace,
            )
            returned_translation.body = body
            returned_translation.footer = footer
            returned_translation.status = template.get("status")
            returned_translation.variable_count = 0
            returned_translation.save()

            for translation in template.get("components"):
                if translation.get("type") == "HEADER":
                    returned_header, created = TemplateHeader.objects.get_or_create(
                        translation=returned_translation,
                        header_type=translation.get("format"),
                        #example=translation.get("example", {}).get("header_handle"),
                    )
                    returned_header.text=translation.get("text", {})
                    returned_header.example=translation.get("example", {}).get("header_handle")
                    returned_header.save()

                if translation.get("type") == "BUTTONS":
                    for button in translation.get("buttons"):
                        returned_button, created = TemplateButton.objects.get_or_create(
                            translation=returned_translation,
                            button_type=button.get("type"),
                            text=button.get("text"),
                            url=button.get("url"),
                            phone_number=button.get("phone_number"),
                        )
