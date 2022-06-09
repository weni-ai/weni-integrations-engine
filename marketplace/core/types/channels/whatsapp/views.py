from typing import TYPE_CHECKING

import requests
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from .apis import OnPremiseBusinessProfileAPI
from .facades import OnPremiseProfileFacade
from ..whatsapp_base.serializers import WhatsAppSerializer
from ..whatsapp_base import mixins


class WhatsAppViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):
    serializer_class = WhatsAppSerializer
    business_profile_class = OnPremiseBusinessProfileAPI
    profile_class = OnPremiseProfileFacade

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs):
        return Response("This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN)

    @property
    def profile_config_credentials(self) -> dict:
        config = self.get_object().config
        base_url = config.get("base_url", None)
        auth_token = config.get("auth_token", None)

        if base_url is None:
            raise ValidationError("The On-Premise URL is not configured")

        if auth_token is None:
            raise ValidationError("On-Premise authentication token is not configured")

        return dict(base_url=base_url, auth_token=auth_token)

    @action(detail=False, methods=["GET"], url_name="shared-wabas", url_path="shared-wabas")
    def shared_wabas(self, request: "Request", **kwargs):
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        headers = {"Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"}

        response = requests.get(f"{settings.WHATSAPP_API_URL}/debug_token?input_token={input_token}", headers=headers)
        response.raise_for_status()

        data = response.json().get("data")
        error = data.get("error")

        if error is not None:
            raise ValidationError(error.get("message"))

        granular_scopes = data.get("granular_scopes")

        try:
            scope = next(filter(lambda scope: scope.get("scope") == "whatsapp_business_management", granular_scopes))
        except StopIteration:
            return Response([])

        target_ids = scope.get("target_ids")

        wabas = []

        for target_id in target_ids:
            response = requests.get(f"{settings.WHATSAPP_API_URL}/{target_id}/?access_token={input_token}")
            response.raise_for_status()

            response_json = response.json()

            waba = dict()
            waba["id"] = target_id
            waba["name"] = response_json.get("name")
            wabas.append(waba)

        return Response(wabas)
