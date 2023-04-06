from django.contrib.auth import get_user_model
from django.conf import settings

from sentry_sdk import capture_exception

from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_base.exceptions import FacebookApiException

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
    
    '''def update(self, request, *args, **kwargs):
        instance = self.get_object()

        translation = instance.translation
        header = translation.header
        body = translation.body
        footer = translation.footer'''

        
    
    
    def perform_destroy(self, instance):
        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        response = template_request.delete_template_message(waba_id=instance.app.config.get("wa_waba_id"),
                                                            name=instance.name)

        if response.status_code != status.HTTP_200_OK:
            capture_exception(FacebookApiException(response.json()))
            if response.json().get("error", {}).get("error_subcode", 0) == 2388094:
                return Response(data=dict(error="WhatsApp.templates.error.delete_sample"),
                                status=status.HTTP_400_BAD_REQUEST)

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
    
    
    #incluir URL
    @action(detail=True, methods=["PATCH"])
    def update_template(self, request, app_uuid=None, uuid=None):

        app = App.objects.get(uuid=app_uuid)
        template = TemplateMessage.objects.get(uuid=uuid)

        template.name = request.data.get("name")
        template.app = app

        template.save()

        translation =  TemplateTranslation.objects.get(template=template)

        translation.template = template
        translation.body = request.data.get("body", [])
        translation.header = request.data.get("header", {})
        translation.footer = request.data.get("footer", [])
        translation.language = request.data.get("language", {})
        
        translation.save()

        header = TemplateHeader.objects.get(template=template)

        header.text = translation.header

        header.save()
        #Deveria salvar o TemplateHeader tambem?

        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        #try
        response = template_request.update_template_message(
                    waba_id=app.config.get("wa_waba_id"),
                    name=request.data.get("name"),
                    language=request.data.get("language"),
                    components=translation.header + translation.body + translation.footer,
                    )
        print( 'HA')
        print(response)
        response.raise_for_status()
        #except Exception as e:
        #    capture_exception(FacebookApiException(e.response.json()))
        #    raise e

        return Response(template)
