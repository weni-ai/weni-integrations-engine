from celery import shared_task

from .models import TemplateMessage

from temba.channels.models import Channel
from temba.templates.models import TemplateTranslation


@shared_task(track_started=True, name="refresh_whatsapp_templates_from_facebook")
def refresh_whatsapp_templates_from_facebook():
    for channel in Channel.objects.filter(is_active=True):

        if not channel.config.get("wa_waba_id"):
            continue

        template_message_request = TemplateMessageRequest()

        templates = template_message_request.list_template_messages(channel.config.get("wa_waba_id"))

        namespace = template_message_request.get_template_namespace(channel.config.get("wa_waba_id"))

        for translation in templates.get("data", []):
            TemplateTranslation.get_or_create(
                channel=channel,
                name=translation.get("name"),
                language=translation.get("language"),
                country="br",
                content=translation.get("components"),
                variable_count=0,
                status=translation.get("status")[:1],
                external_id=translation.get("id"),
                namespace=namespace,
            )
