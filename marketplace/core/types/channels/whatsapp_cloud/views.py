import string
import requests

from typing import TYPE_CHECKING

from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException

from django.conf import settings
from django.utils.crypto import get_random_string

from marketplace.core.types import views
from marketplace.applications.models import App
from marketplace.celery import app as celery_app
from marketplace.connect.client import ConnectProjectClient
from marketplace.flows.client import FlowsClient

from ..whatsapp_base import mixins
from ..whatsapp_base.serializers import WhatsAppSerializer
from ..whatsapp_base.exceptions import FacebookApiException

from .facades import CloudProfileFacade, CloudProfileContactFacade
from .requests import PhoneNumbersRequest

from .serializers import WhatsAppCloudConfigureSerializer


if TYPE_CHECKING:
    from rest_framework.request import Request  # pragma: no cover


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):
    serializer_class = WhatsAppSerializer

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
        config = self.get_object().config
        phone_numbrer_id = config.get("wa_phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(phone_number_id=phone_numbrer_id)

    @property
    def get_access_token(self) -> str:
        user_acess_token = self.get_object().config.get("wa_user_token")
        access_token = (
            user_acess_token
            if user_acess_token
            else settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
        )
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

        base_url = settings.WHATSAPP_API_URL

        url = f"{base_url}/{settings.WHATSAPP_VERSION}/oauth/access_token/"
        params = dict(
            client_id=settings.WHATSAPP_APPLICATION_ID,
            client_secret=settings.WHATSAPP_APPLICATION_SECRET,
            code=auth_code,
        )
        response = requests.get(url, params=params)
        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        user_auth = response.json().get("access_token")

        headers = {"Authorization": f"Bearer {user_auth}"}

        url = f"{base_url}/{waba_id}"
        params = dict(fields="on_behalf_of_business_info,message_template_namespace")
        response = requests.get(url, params=params, headers=headers)

        message_template_namespace = response.json().get("message_template_namespace")
        business_id = response.json().get("on_behalf_of_business_info").get("id")

        url = f"{base_url}/{waba_id}/assigned_users"
        params = dict(
            user=settings.WHATSAPP_CLOUD_SYSTEM_USER_ID,
            access_token=user_auth,
            tasks="MANAGE",
        )
        response = requests.post(url, params=params, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        url = f"{base_url}/{settings.WHATSAPP_CLOUD_EXTENDED_CREDIT_ID}/whatsapp_credit_sharing_and_attach"
        params = dict(waba_id=waba_id, waba_currency=waba_currency)
        response = requests.post(url, params=params, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        allocation_config_id = response.json().get("allocation_config_id")

        url = f"{base_url}/{waba_id}/subscribed_apps"
        response = requests.post(url, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        url = f"{base_url}/{phone_number_id}/register"
        pin = get_random_string(6, string.digits)
        data = dict(messaging_product="whatsapp", pin=pin)
        response = requests.post(url, headers=headers, data=data)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        phone_number_request = PhoneNumbersRequest(user_auth)
        phone_number = phone_number_request.get_phone_number(phone_number_id)

        config = dict(
            wa_number=phone_number.get("display_phone_number"),
            wa_verified_name=phone_number.get("verified_name"),
            wa_waba_id=waba_id,
            wa_currency=waba_currency,
            wa_business_id=business_id,
            wa_message_template_namespace=message_template_namespace,
            wa_pin=pin,
            wa_user_token=user_auth,
        )

        client = ConnectProjectClient()
        channel = client.create_wac_channel(
            request.user.email, project_uuid, phone_number_id, config
        )

        config["title"] = config.get("wa_number")
        config["wa_allocation_config_id"] = allocation_config_id
        config["wa_phone_number_id"] = phone_number_id

        App.objects.create(
            code=self.type_class.code,
            config=config,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=request.user,
            flow_object_uuid=channel.get("uuid"),
            configured=True,
        )

        celery_app.send_task(name="sync_whatsapp_cloud_wabas")
        celery_app.send_task(name="sync_whatsapp_cloud_phone_numbers")

        return Response(serializer.validated_data)

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
