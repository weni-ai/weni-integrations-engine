from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.connect.client import ConnectProjectClient

from .serializers import FacebookSerializer, FacebookConfigureSerializer
from marketplace.core.types import views
from . import type as type_


class FacebookViewSet(views.BaseAppTypeViewSet):
    serializer_class = FacebookSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.FacebookType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.FacebookType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()
        self.serializer_class = FacebookConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        user = request.user
        client = ConnectProjectClient()

        if app.flow_object_uuid is None:
            validated_config = serializer.validated_data.get("config")
            payload = {
                "user_access_token": validated_config.get("user_access_token"),
                "fb_user_id": validated_config.get("fb_user_id"),
                "page_name": validated_config.get("page_name"),
                "page_id": validated_config.get("page_id"),
            }
            print(payload)
            response = client.create_channel(
                user.email, app.project_uuid, payload, app.flows_type_code
            )

            app.flow_object_uuid = response.get("uuid")
            app.save()

        return Response(serializer.data)
