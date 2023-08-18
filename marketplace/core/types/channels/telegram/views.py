from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.connect.client import ConnectProjectClient

from .serializers import TelegramSerializer, TelegramConfigureSerializer
from marketplace.core.types import views
from . import type as type_


class TelegramViewSet(views.BaseAppTypeViewSet):
    serializer_class = TelegramSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.TelegramType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.TelegramType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()
        self.serializer_class = TelegramConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        if app.flow_object_uuid is None:
            payload = {
                "auth_token": serializer.validated_data.get("config")["token"],
            }

            user = request.user
            client = ConnectProjectClient()

            response = client.create_channel(
                user.email, app.project_uuid, payload, app.flows_type_code
            )

            app.flow_object_uuid = response.get("uuid")
            app.configured = True
            app.config["title"] = response.get("name")
            app.save()

        return Response(serializer.data)
