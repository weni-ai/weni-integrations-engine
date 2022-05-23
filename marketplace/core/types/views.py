from django.conf import settings
from rest_framework.viewsets import GenericViewSet
from rest_framework import status
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.response import Response

from marketplace.applications.models import App
from marketplace.accounts.permissions import ProjectManagePermission
from marketplace.celery import app as celery_app

from marketplace.connect.client import ConnectProjectClient


class BaseAppTypeViewSet(CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):

    queryset = App.objects
    lookup_field = "uuid"
    permission_classes = [ProjectManagePermission]

    def create(self, request, *args, **kwargs):
        project_uuid = request.data.get("project_uuid")

        if not self.type_class.can_add(project_uuid):
            data = {"error": "Exceeded the integration limit for this App"}
            return Response(data, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)

        channel_uuid = instance.config.get("channelUuid")

        if channel_uuid is not None and settings.USE_GRPC:
            client = ConnectProjectClient()
            client.release_channel(channel_uuid, self.request.user.email)