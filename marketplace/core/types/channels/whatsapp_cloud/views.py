from typing import TYPE_CHECKING

from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from django.conf import settings
import requests

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from .serializers import WhatsAppCloudSerializer
from ..whatsapp_base import mixins
from ..whatsapp_base.exceptions import FacebookApiException
from .facades import CloudProfileFacade, CloudProfileContactFacade
from .requests import PhoneNumbersRequest


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):

    serializer_class = WhatsAppCloudSerializer

    business_profile_class = CloudProfileContactFacade
    profile_class = CloudProfileFacade

    @property
    def profile_config_credentials(self) -> dict:
        config = self.get_object().config
        phone_numbrer_id = config.get("phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(phone_number_id=phone_numbrer_id)

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs) -> Response:
        return Response("This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["GET"])
    def waba_id(self, request: "Request", **kwargs):
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
        headers = {"Authorization": f"Bearer {input_token}"}

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise ValidationError(response.json())

        data = response.json().get("data")

        try:
            whatsapp_business_management = next(
                filter(lambda scope: scope.get("scope") == "whatsapp_business_management", data.get("granular_scopes"))
            )
        except StopIteration:
            raise ValidationError("Invalid token permissions")

        try:
            waba_id = whatsapp_business_management.get("target_ids")[0]
        except IndexError:
            raise ValidationError("Missing WhatsApp Business Accound Id")

        return Response(waba_id)

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

        input_token = request.query_params.get("input_token", None)
        waba_id = request.query_params.get("waba_id", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        if waba_id is None:
            raise ValidationError("waba_id is a required parameter!")

        request = PhoneNumbersRequest(input_token)

        try:
            return Response(request.get_phone_numbers(waba_id))
        except FacebookApiException as error:
            raise ValidationError(error)
