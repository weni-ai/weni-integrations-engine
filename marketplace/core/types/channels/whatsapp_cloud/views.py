import string

from typing import TYPE_CHECKING

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException

from django.conf import settings
from django.utils.crypto import get_random_string

from marketplace.core.types import views
from marketplace.applications.models import App

from marketplace.clients.flows.client import FlowsClient
from marketplace.accounts.permissions import ProjectManagePermission, IsCRMUser
from marketplace.clients.facebook.client import FacebookClient
from marketplace.core.types.channels.whatsapp.usecases.phone_number_sync import (
    PhoneNumberSyncUseCase,
)
from marketplace.core.types.channels.whatsapp.usecases.waba_sync import WABASyncUseCase
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_insights_sync import (
    WhatsAppInsightsSyncUseCase,
)
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_calling import (
    WhatsAppCallingUseCase,
)
from marketplace.services.facebook.service import (
    PhoneNumbersService,
    BusinessMetaService,
    TemplateService,
)
from marketplace.services.flows.service import FlowsService
from marketplace.internal.permissions import CanCommunicateInternally

from ..whatsapp_base import mixins
from ..whatsapp_base.serializers import WhatsAppSerializer
from .serializers import WhatsAppCloudConfigureSerializer
from .facades import CloudProfileFacade, CloudProfileContactFacade

if TYPE_CHECKING:
    from rest_framework.request import Request  # pragma: no cover


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):
    serializer_class = WhatsAppSerializer
    permission_classes = [ProjectManagePermission | IsCRMUser]

    business_profile_class = CloudProfileContactFacade
    profile_class = CloudProfileFacade

    @property
    def app_waba_id(self) -> dict:
        config = self.get_object().config
        waba_id = config.get("wa_waba_id", None)

        if waba_id is None:
            raise ValidationError(
                "This app does not have WABA (Whatsapp Business Account ID) configured"
            )

        return waba_id

    @property
    def profile_config_credentials(self) -> dict:
        app = self.get_object()
        access_token = app.apptype.get_access_token(app)
        config = app.config
        phone_numbrer_id = config.get("wa_phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(access_token=access_token, phone_number_id=phone_numbrer_id)

    @property
    def get_access_token(self) -> str:
        access_token = self.get_object().apptype.get_access_token(self.get_object())
        if access_token is None:
            raise ValidationError("This app does not have fb_access_token in settings")

        return access_token

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs) -> Response:
        return Response(
            "This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN
        )

    def create(self, request, *args, **kwargs):
        serializer = WhatsAppCloudConfigureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_uuid = request.data.get("project_uuid")
        waba_id = serializer.validated_data.get("waba_id")
        phone_number_id = serializer.validated_data.get("phone_number_id")
        auth_code = serializer.validated_data.get("auth_code")
        waba_currency = "USD"

        whatsapp_system_user_access_token = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
        facebook_client = FacebookClient(whatsapp_system_user_access_token)
        business_service = BusinessMetaService(client=facebook_client)
        template_service = TemplateService(client=facebook_client)

        # Configure WhatsApp Cloud
        config_data = business_service.configure_whatsapp_cloud(
            auth_code, waba_id, phone_number_id, waba_currency
        )

        user_access_token = config_data["user_access_token"]
        business_id = config_data["business_id"]
        message_template_namespace = config_data["message_template_namespace"]
        allocation_config_id = config_data["allocation_config_id"]
        dataset_id = config_data["dataset_id"]

        # Get phone number
        phone_number_request = PhoneNumbersService(
            client=FacebookClient(whatsapp_system_user_access_token)
        )
        phone_number = phone_number_request.get_phone_number(phone_number_id)

        # Register phone number
        pin = get_random_string(6, string.digits)
        data = dict(messaging_product="whatsapp", pin=pin)
        business_service.register_phone_number(phone_number_id, user_access_token, data)

        config = dict(
            wa_number=phone_number.get("display_phone_number"),
            wa_verified_name=phone_number.get("verified_name"),
            wa_waba_id=waba_id,
            wa_currency=waba_currency,
            wa_business_id=business_id,
            wa_message_template_namespace=message_template_namespace,
            wa_pin=pin,
            wa_user_token=user_access_token,
            wa_dataset_id=dataset_id,
        )

        flows_service = FlowsService(client=FlowsClient())
        channel = flows_service.create_wac_channel(
            request.user.email, project_uuid, phone_number_id, config
        )

        config["title"] = config.get("wa_number")
        config["wa_allocation_config_id"] = allocation_config_id
        config["wa_phone_number_id"] = phone_number_id
        config["has_insights"] = template_service.setup_insights(waba_id)

        app = App.objects.create(
            code=self.type_class.code,
            config=config,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=request.user,
            flow_object_uuid=channel.get("uuid"),
            configured=True,
        )

        WABASyncUseCase(app).sync_whatsapp_cloud_waba()
        PhoneNumberSyncUseCase(app).sync_whatsapp_cloud_phone_number()
        WhatsAppInsightsSyncUseCase(app).sync()

        response_data = {
            **serializer.validated_data,
            "app_uuid": str(app.uuid),
            "flow_object_uuid": str(app.flow_object_uuid),
        }
        return Response(response_data)

    @action(detail=True, methods=["PATCH"])
    def update_webhook(self, request, uuid=None):
        """
        This method updates the flows config with the new  [webhook] information,
        if the update is successful, the webhook is updated in integrations,
        otherwise an exception will occur.
        """

        try:
            flows_client = FlowsClient()

            app = self.get_object()
            config = request.data["config"]

            detail_channel = flows_client.detail_channel(app.flow_object_uuid)

            flows_config = detail_channel["config"]
            updated_config = flows_config
            updated_config["webhook"] = config["webhook"]

            response = flows_client.update_config(
                data=updated_config, flow_object_uuid=app.flow_object_uuid
            )
            response.raise_for_status()

        except KeyError as exception:
            # Handle missing keys
            raise APIException(
                detail=f"Missing key: {str(exception)}", code=400
            ) from exception

        app.config["webhook"] = config["webhook"]
        app.save()

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=["GET"])
    def report_sent_messages(self, request: "Request", **kwargs):
        project_uuid = request.query_params.get("project_uuid", None)
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        user = request.user.email

        if project_uuid is None:
            raise ValidationError("project_uuid is a required parameter")

        if start_date is None:
            raise ValidationError("start_date is a required parameter")

        if end_date is None:
            raise ValidationError("end_date is a required parameter")

        client = FlowsClient()
        response = client.get_sent_messagers(
            end_date=end_date,
            project_uuid=project_uuid,
            start_date=start_date,
            user=user,
        )

        return Response(status=response.status_code)

    @action(detail=True, methods=["PATCH"])
    def update_mmlite_status(self, request: "Request", **kwargs):
        app = self.get_object()

        status = request.data.get("status")

        if status not in ["in_progress", "active"]:
            raise ValidationError("Invalid status")

        app.config["mmlite_status"] = request.data.get("status")
        app.save()

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=["GET"])
    def calling_status(self, request: "Request", **kwargs):
        app = self.get_object()
        try:
            data = WhatsAppCallingUseCase(app).get_settings()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        else:
            return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["PATCH"])
    def enable_calling(self, request: "Request", **kwargs):
        app = self.get_object()
        try:
            details = WhatsAppCallingUseCase(app).enable()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        else:
            serializer = self.get_serializer(app)
            return Response(
                {"app": serializer.data, "calling": details}, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["PATCH"])
    def disable_calling(self, request: "Request", **kwargs):
        app = self.get_object()
        try:
            details = WhatsAppCallingUseCase(app).disable()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        else:
            serializer = self.get_serializer(app)
            return Response(
                {"app": serializer.data, "calling": details}, status=status.HTTP_200_OK
            )


class WhatsAppCloudInsights(APIView):
    permission_classes = [CanCommunicateInternally]

    def get(self, request, project_uuid, *args, **kwargs):
        apps = App.objects.filter(project_uuid=project_uuid, code="wpp-cloud")
        response = []
        for app in apps:
            response.append(
                {
                    "waba_id": app.config.get("wa_waba_id", None),
                    "phone_number": app.config.get("wa_number"),
                }
            )
        return Response({"data": response}, status=status.HTTP_200_OK)
