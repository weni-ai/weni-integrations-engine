from rest_framework.response import Response
from rest_framework import status


from marketplace.core.types.emails.g_mail.serializers import GmailSerializer

from marketplace.core.types.emails.base_serializer import EmailSerializer

from marketplace.core.types import views
from marketplace.core.types.emails.generic_email import type as type_
from marketplace.core.types.emails.generic_email.utils import EmailAppUtils
from marketplace.services.flows.service import FlowsService
from marketplace.clients.flows.client import FlowsClient


class GmailViewSet(views.BaseAppTypeViewSet):
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
        return super().get_queryset().filter(code=type_.GmailType.code)

    def create(self, request, *args, **kwargs):
        """
        Custom create logic that includes configuring Gmail during creation.
        """
        serializer = GmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_uuid = request.data.get("project_uuid")

        channel_data = serializer.to_channel_data()

        # Create Channel on flows
        response = self.flows_service.create_channel(
            user_email=request.user.email,
            project_uuid=project_uuid,
            data=channel_data,
            channeltype_code=self.type_class.flows_type_code,
        )

        EmailAppUtils.create_and_configure_gmail_app(
            project_uuid=project_uuid,
            config_data=channel_data,
            type_class=self.type_class,
            created_by=request.user,
            flows_response=response,
        )

        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
