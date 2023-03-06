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

if TYPE_CHECKING:
    from rest_framework.request import Request

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
            raise ValidationError("This app does not have WABA (Whatsapp Business Account ID) configured")

        return waba_id

    @property
    def profile_config_credentials(self) -> dict:
        config = self.get_object().config
        phone_numbrer_id = config.get("wa_phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(phone_number_id=phone_numbrer_id)

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs) -> Response:
        return Response("This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN)

    def create(self, request, *args, **kwargs):
        serializer = WhatsAppCloudConfigureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_uuid = request.data.get("project_uuid")

        input_token = serializer.validated_data.get("input_token")
        waba_id = serializer.validated_data.get("waba_id")
        phone_number_id = serializer.validated_data.get("phone_number_id")
        business_id = serializer.validated_data.get("business_id")
        waba_currency = "USD"

        base_url = settings.WHATSAPP_API_URL
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"}

        url = f"{base_url}/{waba_id}"
        params = dict(fields="message_template_namespace")
        response = requests.get(url, params=params, headers=headers)

        message_template_namespace = response.json().get("message_template_namespace")

        url = f"{base_url}/{waba_id}/assigned_users"
        params = dict(
            user=settings.WHATSAPP_CLOUD_SYSTEM_USER_ID,
            access_token=settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN,
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

        phone_number_request = PhoneNumbersRequest(input_token)
        phone_number = phone_number_request.get_phone_number(phone_number_id)

        config = dict(
            wa_number=phone_number.get("display_phone_number"),
            wa_verified_name=phone_number.get("verified_name"),
            wa_waba_id=waba_id,
            wa_currency=waba_currency,
            wa_business_id=business_id,
            wa_message_template_namespace=message_template_namespace,
            wa_pin=pin,
        )

        client = ConnectProjectClient()
        channel = client.create_wac_channel(request.user.email, project_uuid, phone_number_id, config)

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
        )

        celery_app.send_task(name="sync_whatsapp_cloud_wabas")
        celery_app.send_task(name="sync_whatsapp_cloud_phone_numbers")

        return Response(serializer.validated_data)

    @action(detail=False, methods=["GET"])
    def debug_token(self, request: "Request", **kwargs):
        """
        Returns the waba id for the input token.

            Query Parameters:
                - input_token (str): User Facebook Access Token

            Return body:
            "<WABA_ID"
        """
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        url = f"{settings.WHATSAPP_API_URL}/debug_token"
        params = dict(input_token=input_token)
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"}

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise ValidationError(response.json())

        data = response.json().get("data")

        # TODO: This code snippet needs refactoring

        try:
            whatsapp_business_management = next(
                filter(
                    lambda scope: scope.get("scope") == "whatsapp_business_management",
                    data.get("granular_scopes"),
                )
            )
        except StopIteration:
            raise ValidationError("Invalid token permissions")

        try:
            business_management = next(
                filter(
                    lambda scope: scope.get("scope") == "business_management",
                    data.get("granular_scopes"),
                )
            )
        except StopIteration:
            business_management = dict()

        try:
            waba_id = whatsapp_business_management.get("target_ids")[0]
        except IndexError:
            raise ValidationError("Missing WhatsApp Business Accound Id")

        try:
            business_id = business_management.get("target_ids", [])[0]
        except IndexError:
            url = f"{settings.WHATSAPP_API_URL}/{waba_id}/"
            params = dict(
                access_token=settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN,
                fields="owner_business_info,on_behalf_of_business_info",
            )

            business_id = (
                requests.get(url, params=params, headers=headers)
                .json()
                .get("owner_business_info", {"id": None})
                .get("id")
            )

        return Response(dict(waba_id=waba_id, business_id=business_id))

    @action(detail=False, methods=["GET"])
    def phone_numbers(self, request: "Request", **kwargs):
        """
        Returns a list of phone numbers for a given WABA Id.

            Query Parameters:
                - input_token (str): User Facebook Access Token
                - waba_id (str): WhatsApp Business Account Id

            Return body:
            [
                {
                    "phone_number": "",
                    "phone_number_id": ""
                },
            ]
        """

        waba_id = request.query_params.get("waba_id", None)

        if waba_id is None:
            raise ValidationError("waba_id is a required parameter!")

        request = PhoneNumbersRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        try:
            return Response(request.get_phone_numbers(waba_id))
        except FacebookApiException as error:
            raise ValidationError(error)

    @action(detail=True, methods=["PATCH"])
    def update_webhook(self, request, uuid=None):
        """
        This method updates the flows config with the new  [webhook] information,
        if the update is successful, the webhook is updated in integrations,
        otherwise an exception will occur.
        """

        try:
            app = self.get_object()
            config = request.data["config"]
            flows_client = FlowsClient()
            response = flows_client.partial_config_update(
                key="webhook",
                data=config["webhook"],
                flow_object_uuid=app.flow_object_uuid,
            )
            response.raise_for_status()

        except requests.exceptions.HTTPError as exception:
            # Handles HTTP exceptions
            raise APIException(
                detail=f"HTTPError: {str(exception)}",
                code=400
            ) from exception
        except requests.exceptions.RequestException as exception:
            # Handle general network exceptions
            raise APIException(
                detail=f"RequestException: {str(exception)}",
                code=400
            ) from exception
        except KeyError as exception:
            # Handle missing keys
            raise APIException(
                detail=f"Missing key: {str(exception)}",
                code=400
            ) from exception

        app.config["webhook"] = config["webhook"]
        app.save()

        serializer = self.get_serializer(app)
        return Response(serializer.data)
