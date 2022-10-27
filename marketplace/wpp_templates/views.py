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

from .models import TemplateMessage
from .serializers import TemplateMessageSerializer, TemplateTranslationCreateSerializer, TemplateQuerySetSerializer, TemplateTranslationSerializer
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
        queryset = TemplateMessage.objects.filter(app=app).order_by("created_by")

        return queryset

    def create(self, request, *args, **kwargs):
        request.data.update(self.kwargs)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        response = template_request.delete_template_message(waba_id=instance.app.config.get("wa_waba_id"), name=instance.name)

        if response.status_code != status.HTTP_200_OK:
            capture_exception(FacebookApiException(response.json()))

            if response.json().get("error", {}).get("error_subcode", 0) == 2388094:
                return Response(data=dict(error="WhatsApp.templates.error.delete_sample"), status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_400_BAD_REQUEST)

        instance.delete()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def translations(self, request, app_uuid = None, uuid = None):
        request.data["template_uuid"] = uuid

        serializer = TemplateTranslationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()        

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def languages(self, request, app_uuid=None):
        return Response(data=LANGUAGES, status=status.HTTP_200_OK)
