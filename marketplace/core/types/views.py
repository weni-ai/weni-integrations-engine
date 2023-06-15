from rest_framework.viewsets import GenericViewSet
from rest_framework import status
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
)
from rest_framework.response import Response

from marketplace.applications.models import App
from marketplace.accounts.permissions import ProjectManagePermission

from marketplace.connect.client import ConnectProjectClient


class BaseAppTypeViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = App.objects
    lookup_field = "uuid"
    permission_classes = [ProjectManagePermission]

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def create(self, request, *args, **kwargs):
        project_uuid = request.data.get("project_uuid")

        if not self.type_class.can_add(project_uuid):
            data = {"error": "Exceeded the integration limit for this App"}
            return Response(data, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        project_uuid = str(instance.project_uuid)
        channel_uuid = instance.flow_object_uuid
        if channel_uuid:
            client = ConnectProjectClient()
            client.release_channel(channel_uuid, project_uuid, self.request.user.email)
