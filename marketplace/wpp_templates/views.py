from django.contrib.auth import get_user_model
from django.conf import settings

from sentry_sdk import capture_exception

from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)

from .models import TemplateHeader, TemplateMessage, TemplateTranslation, TemplateButton
from .serializers import TemplateMessageSerializer, TemplateTranslationSerializer
from .requests import TemplateMessageRequest
from .languages import LANGUAGES

User = get_user_model()


class CustomResultsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 500


class AppsViewSet(viewsets.ViewSet):
    lookup_field = "uuid"


class TemplateMessageViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    serializer_class = TemplateMessageSerializer
    pagination_class = CustomResultsPagination

    def get_queryset(self):
        app = App.objects.get(uuid=self.kwargs["app_uuid"])
        queryset = TemplateMessage.objects.filter(app=app).order_by("-created_on")

        return queryset

    def create(self, request, *args, **kwargs):
        request.data.update(self.kwargs)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        template_request = TemplateMessageRequest(
            settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
        )
        response = template_request.delete_template_message(
            waba_id=instance.app.config.get("wa_waba_id"), name=instance.name
        )

        if response.status_code != status.HTTP_200_OK:
            capture_exception(FacebookApiException(response.json()))
            if response.json().get("error", {}).get("error_subcode", 0) == 2388094:
                return Response(
                    data=dict(error="WhatsApp.templates.error.delete_sample"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_400_BAD_REQUEST)

        instance.delete()
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return self.perform_destroy(instance)

    @action(detail=True, methods=["POST"])
    def translations(self, request, app_uuid=None, uuid=None):
        request.data["template_uuid"] = uuid

        serializer = TemplateTranslationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def languages(self, request, app_uuid=None):
        return Response(data=LANGUAGES, status=status.HTTP_200_OK)

    def partial_update(self, request, app_uuid=None, uuid=None):
        from marketplace.wpp_templates.tasks import refresh_whatsapp_templates_from_facebook

        template = self.get_object()

        message_template_id = request.data.get("message_template_id")

        request.data.pop("message_template_id")
        data = request.data
        components = [data]

        header = data.get("header")
        body = data.get("body")
        footer = data.get("footer")
        buttons = data.get("buttons")

        list_components = []

        translation = TemplateTranslation.objects.filter(template=template).first()
        template_header = TemplateHeader.objects.get(translation=translation)

        if header:
            template_header.text = header.get("text")
            template_header.header_type = header.get("header_type")
            if header.get("example"):
                template_header.example = header.get("example")
            template_header.save()

            type_header = {"type": "HEADER"}
            type_header.update(header)
            type_header["format"] = type_header["header_type"]
            del type_header["header_type"]
            list_components.append(type_header)

        if body:
            list_components.append(data.get("body"))

            translation.body = body.get("text")

        if footer:
            list_components.append(data.get("footer"))

            translation.footer = footer.get("text")
        translation.save()

        if buttons:
            for button in buttons:
                TemplateButton.objects.update_or_create(
                                translation=translation,
                                button_type=button.get("type"),
                                text=button.get("text"),
                                url=button.get("url"),
                                phone_number=button.get("phone_number"),
                            )

                button["type"] = button["button_type"]
                del button["button_type"]

            type_button = {"type": "BUTTON", "buttons": buttons}
            type_button.update(buttons)
            list_components.append(type_button)

            type_button = {"type": "BUTTON", "buttons": buttons}
            type_button.update(buttons)
            list_components.append(type_button)
        
        components = list_components

        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        response = template_request.update_template_message(
                    message_template_id= message_template_id,
                    name=template.name,
                    components=components,
                    )

        return Response(response)
