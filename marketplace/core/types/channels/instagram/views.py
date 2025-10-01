from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.clients.flows.client import FlowsClient

from .serializers import InstagramSerializer, InstagramConfigureSerializer
from marketplace.core.types import views
from . import type as type_


class InstagramViewSet(views.BaseAppTypeViewSet):
    serializer_class = InstagramSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.InstagramType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.InstagramType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()
        self.serializer_class = InstagramConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        if app.flow_object_uuid is None:
            validated_config = serializer.validated_data.get("config")
            payload = {
                "user_access_token": validated_config.get("user_access_token"),
                "fb_user_id": validated_config.get("fb_user_id"),
                "page_name": validated_config.get("page_name"),
                "page_id": validated_config.get("page_id"),
            }

            user = request.user
            client = FlowsClient()

            response = client.create_channel(
                user.email, app.project_uuid, payload, app.flows_type_code
            )

            flows_config = response.get("config")
            app.flow_object_uuid = response.get("uuid")
            app.configured = True
            app.config["title"] = response.get("name")
            app.config["address"] = response.get("address")
            app.config["page_name"] = flows_config.get("page_name")
            app.config["page_id"] = flows_config.get("page_id")
            app.config["auth_token"] = flows_config.get("auth_token")
            app.save()

        return Response(serializer.data)
