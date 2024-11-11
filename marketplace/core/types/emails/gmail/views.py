from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action

from marketplace.core.types.emails.gmail.serializers import GmailSerializer
from marketplace.core.types.emails.base_serializer import EmailSerializer
from marketplace.core.types import views
from marketplace.core.types.emails.gmail import type as type_
from marketplace.core.types.emails.utils import EmailAppUtils
from marketplace.services.flows.service import FlowsService
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.google.service import GoogleAuthService


class GmailViewSet(views.BaseAppTypeViewSet):
    serializer_class = EmailSerializer
    flows_service_class = FlowsService
    flows_client_class = FlowsClient

    _flows_service = None  # Cache the service to avoid re-creating it

    @property
    def flows_service(self):  # pragma: no cover
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

        app = EmailAppUtils.create_and_configure_gmail_app(
            project_uuid=project_uuid,
            config_data=channel_data,
            type_class=self.type_class,
            created_by=request.user,
            flows_response=response,
        )
        # Serialize the app data
        app_serializer = self.serializer_class(app)

        return Response(app_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="authenticate-google")
    def authenticate_google(self, request):
        """
        Authenticates Google using the authorization code
        and returns the access_token and refresh_token.
        """
        code = request.data.get("code")

        if not code:
            return Response(
                {"error": "Authorization code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Use the service to exchange the code for tokens
            tokens = GoogleAuthService.exchange_code_for_token(code)
            return Response(tokens, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
