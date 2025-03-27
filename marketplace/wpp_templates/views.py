import datetime
import re
import base64
import pytz
from dataclasses import asdict

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError

from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import get_object_or_404

from marketplace.applications.models import App
from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp_base.mixins import QueryParamsParser
from marketplace.services.facebook.service import TemplateService, PhotoAPIService
from marketplace.clients.facebook.client import FacebookClient
from marketplace.accounts.permissions import ProjectManagePermission
from marketplace.celery import app as celery_app

from .models import TemplateHeader, TemplateMessage, TemplateTranslation, TemplateButton
from .serializers import TemplateMessageSerializer, TemplateTranslationSerializer
from .languages import LANGUAGES
from .usecases import TemplatesUseCase


WHATSAPP_VERSION = settings.WHATSAPP_VERSION

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
    permission_classes = [ProjectManagePermission]

    def filter_queryset(self, queryset):
        params = self.request.query_params
        name = params.get("name")
        category = params.get("category")
        order_by = params.get("sort")
        date_params = params.get("start")
        filters = {}

        if category:
            filters["category"] = category

        if date_params:
            date_params = QueryParamsParser(params)
            start_str = str(date_params._get_start())
            end_str = str(date_params._get_end())
            start = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=pytz.UTC
            )
            end = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=pytz.UTC
            )

            filters["created_on__range"] = (start, end)

        if name:
            queryset = queryset.filter(name__icontains=name)

        if filters:
            for field, value in filters.items():
                queryset = queryset.filter(**{field: value})
        if order_by:
            queryset = queryset.order_by(order_by)

        return queryset

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
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_destroy(self, instance):
        if instance.app.code == "wpp":
            access_token = instance.app.config.get("fb_access_token", None)
            if instance.app.config.get("waba") is None:
                raise ValidationError(
                    f"This app: {instance.app.uuid} does not have waba in config"
                )
            waba_id = instance.app.config.get("waba").get("id")

            if access_token is None:
                raise ValidationError(
                    f"This app: {instance.app.uuid} does not have fb_access_token in config"
                )
        else:
            access_token = APPTYPES.get("wpp-cloud").get_access_token(instance.app)
            waba_id = instance.app.config.get("wa_waba_id")

        if waba_id is None:
            raise ValidationError(
                f"This app: {instance.app.uuid} does not have waba id in config"
            )

        template_service = TemplateService(client=FacebookClient(access_token))
        template_service.delete_template_message(waba_id=waba_id, name=instance.name)
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
        template = self.get_object()
        if template.app.code == "wpp":
            access_token = template.app.config.get("fb_access_token", None)

            if access_token is None:
                raise ValidationError(
                    f"This app: {template.app.uuid} does not have fb_access_token in config"
                )
        else:
            access_token = APPTYPES.get("wpp-cloud").get_access_token(template.app)

        message_template_id = request.data.get("message_template_id")

        request.data.pop("message_template_id")
        data = request.data
        components = [data]

        header = data.get("header")
        body = data.get("body")
        footer = data.get("footer")
        buttons = data.get("buttons")

        list_components = []

        translation = TemplateTranslation.objects.get(template=template)

        if header:
            header = dict(header)
            header["type"] = "HEADER"
            header["format"] = header.get("header_type", "TEXT")
            header.pop("header_type")

            if (
                header.get("format") == "IMAGE"
                or header.get("format") == "DOCUMENT"
                or header.get("format") == "VIDEO"
            ):
                photo_api_request = PhotoAPIService(client=FacebookClient(access_token))
                photo = header.get("example")
                file_type = re.search("(?<=data:)(.*)(?=;base64)", photo).group(0)
                photo = photo.split(";base64,")[1]
                upload_session_id = photo_api_request.create_upload_session(
                    len(base64.b64decode(photo)),
                    file_type=file_type,
                )
                dict_response = photo_api_request.upload_session(
                    upload_session_id=upload_session_id,
                    file_type=file_type,
                    data=base64.b64decode(photo),
                )
                upload_handle = dict_response.get("h", "")
                header.pop("example")
                header["example"] = dict(header_handle=upload_handle)

            template_header, _created = TemplateHeader.objects.get_or_create(
                translation=translation,
                header_type=header.get("format"),
            )
            template_header.text = header.get("text", {})
            template_header.header_type = header.get("format")

            if header.get("example"):
                template_header.example = header.get("example")

            template_header.save()
            list_components.append(header)

        if body:
            list_components.append(data.get("body"))
            translation.body = body.get("text")

        if footer:
            list_components.append(data.get("footer"))
            translation.body = body.get("text")

        translation.status = "PENDING"
        translation.save()

        if buttons:
            for button in buttons:
                template_button, _created = TemplateButton.objects.get_or_create(
                    translation=translation,
                    button_type=button.get("button_type"),
                    text=button.get("text"),
                    url=button.get("url"),
                    phone_number=button.get("phone_number"),
                )

                template_button.button_type = button.get("button_type")
                template_button.text = button.get("text")
                template_button.country_code = button.get("country_code")
                template_button.url = button.get("url")
                template_button.phone_number = button.get("phone_number")
                template_button.save()

                button["type"] = button["button_type"]
                del button["button_type"]

            type_button = {"type": "BUTTONS", "buttons": buttons}
            list_components.append(type_button)

        components = list_components

        template_service = TemplateService(client=FacebookClient(access_token))

        response = template_service.update_template_message(
            message_template_id=message_template_id,
            name=template.name,
            components=components,
        )

        return Response(response)

    @action(detail=False, methods=["POST"], url_path="create-library-templates")
    def create_library_templates(self, request, app_uuid=None, uuid=None):
        """
        Creates a library template message for the given app by scheduling an asynchronous task.

        This endpoint queues a background task that will handle the template creation process
        without blocking the request. The actual template creation happens asynchronously.

        Args:
            request (Request): The request object containing the template data to be created.
            app_uuid (str): UUID of the app for which the template will be created.
            uuid (str, optional): Not used in this function.

        Returns:
            Response: API response with HTTP 200 status indicating the task was successfully queued.
        """
        app = get_object_or_404(App, uuid=app_uuid)

        celery_app.send_task(
            name="task_create_library_templates_batch",
            kwargs={"app_uuid": str(app.uuid), "template_data": request.data},
        )

        return Response(
            {"message": "Library template task created."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["GET"])
    def template_detail(self, request, app_uuid=None, uuid=None):
        try:
            project_uuid = request.query_params["project_uuid"]
            template_id = request.query_params["template_id"]
            data = TemplatesUseCase.get_whatsapp_cloud_data_from_integrations(
                project_uuid=project_uuid, template_id=template_id
            )
            serialized_data = list(map(lambda data: asdict(data), data))
            return Response(serialized_data, status=status.HTTP_200_OK)
        except KeyError as ke:
            stripped_key = str(ke).strip("'")
            raise CustomAPIException(
                detail=f"Missing required parameter: {stripped_key}",
                code="missing_parameter",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
