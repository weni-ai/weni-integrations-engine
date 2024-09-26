from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.core.types.emails.generic_email.serializers import (
    EmailConfigureSerializer,
)
from marketplace.core.types.emails.base_serializer import (
    BaseEmailSerializer,
    EmailSerializer,
)

from marketplace.core.types import views
from marketplace.core.types.emails.generic_email import type as type_
from marketplace.core.types.emails.generic_email.utils import EmailAppUtils
from marketplace.services.flows.service import FlowsService
from marketplace.clients.flows.client import FlowsClient


class GenericEmailViewSet(views.BaseAppTypeViewSet):
    serializer_class = EmailSerializer
    flows_service_class = FlowsService
    flows_client_class = FlowsClient

    _flows_service = None  # Cache the service to avoid re-creating it

    @property
    def flows_service(self):
        if not self._flows_service:
            self._flows_service = self.flows_service_class(self.flows_client_class())
        return self._flows_service

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.GenericEmailType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.GenericEmailType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config to the specified App and creates a channel on Weni Flows.
        """
        app = self.get_object()
        self.serializer_class = EmailConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        config_data = serializer.validated_data["config"]
        config_serializer = BaseEmailSerializer(data=config_data)
        config_serializer.is_valid(raise_exception=True)

        channel_data = config_serializer.to_channel_data()

        # Create channel on flows
        response = self.flows_service.create_channel(
            user_email=request.user.email,
            project_uuid=app.project_uuid,
            data=channel_data,
            channeltype_code=app.flows_type_code,
        )

        EmailAppUtils.configure_app(app, response)

        return Response(serializer.data)
