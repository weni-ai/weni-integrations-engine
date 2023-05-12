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

from .models import TemplateHeader, TemplateMessage, TemplateTranslation
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
    
    '''def perform_update(self, serializer):
        print(serializer.validated_data)
        instance = serializer.save()
        print('INSTANCE', instance)
        #instance = self.get_object()
        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        response = template_request.update_template_message(waba_id=instance.app.config.get("wa_waba_id"), name=instance.name, language=instance.language, body=instance.body)
        if response.status_code != status.HTTP_200_OK:
            capture_exception(FacebookApiException(response.json()))
            if response.json().get("error", {}).get("error_subcode", 0) == 2388094:
                return Response(data=dict(error="WhatsApp.templates.error.update_sample"),
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_400_BAD_REQUEST)

    #incluir aqui o update
    def partial_update(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        print('olllllllar')
        serializer.is_valid()
        print(serializer  )
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)'''
    
    
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

        app = template.app
        try:
            #incluir message-template-id
            waba_id = app.config.get("waba")["id"]

        except KeyError:
            raise 'Waba_id não encontrado'        

        name = request.data.get("name")
        header = request.data.get("header")
        body = request.data.get("body")
        footer = request.data.get("footer")

        translation = TemplateTranslation.objects.get(template=template)
        list_components = []

        if not name:
            returned_name = TemplateMessage.objects.get(uuid=template.uuid)
            name = returned_name.name

        if header:
            list_components.append({"type": "HEADER",
                                        "format": "TEXT",
                                        "text":header})

        else:
            returned_header = TemplateHeader.objects.get(translation=translation)
            if returned_header:
                returned_header.text = header
                list_components.append({"type": "HEADER",
                                        "format": "TEXT",
                                        "text":header})

        if body:
            list_components.append({"type":"BODY",
                                    "text": body})

        else:
            translation.body = body
            list_components.append({"type":"BODY",
                                    "text": body})

        if footer:
            list_components.append({"type": "FOOTER",
                                    "text": footer})

        else:
            translation.footer = footer
            list_components.append({"type": "FOOTER",
                                    "text": footer})

        components = list_components

        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        response = template_request.update_template_message(
                    message_template_id= "message-template-id",
                    name=name,
                    components=components,
                    )

        refresh_whatsapp_templates_from_facebook()

        return Response(response)
