from typing import TYPE_CHECKING

import requests
from django.conf import settings

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import APIException

if TYPE_CHECKING:
    from rest_framework.request import Request  # pragma: no cover

from marketplace.core.types import views
from marketplace.flows.client import FlowsClient

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
        return Response(
            "This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN
        )

    @property
    def app_waba_id(self) -> dict:
        config = self.get_object().config
        waba_id = config.get("fb_business_id", None)

        if waba_id is None:
            raise ValidationError(
                "This app does not have WABA (Whatsapp Business Account ID) configured"
            )

        return waba_id

    @property
    def get_access_token(self) -> str:
        config = self.get_object().config
        access_token = config.get("fb_access_token", None)

        if access_token is None:
            raise ValidationError("This app does not have fb_access_token in config")

        return access_token

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

    @action(
        detail=False, methods=["GET"], url_name="shared-wabas", url_path="shared-wabas"
    )
    def shared_wabas(self, request: "Request", **kwargs):
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"
        }

        response = requests.get(
            f"{settings.WHATSAPP_API_URL}/debug_token?input_token={input_token}",
            headers=headers,
        )
        response.raise_for_status()

        data = response.json().get("data")
        error = data.get("error")

        if error is not None:
            raise ValidationError(error.get("message"))

        granular_scopes = data.get("granular_scopes")

        try:
            scope = next(
                filter(
                    lambda scope: scope.get("scope") == "whatsapp_business_management",
                    granular_scopes,
                )
            )
        except StopIteration:
            return Response([])

        target_ids = scope.get("target_ids")

        wabas = []

        for target_id in target_ids:
            response = requests.get(
                f"{settings.WHATSAPP_API_URL}/{target_id}/?access_token={input_token}"
            )
            response.raise_for_status()

            response_json = response.json()

            waba = dict()
            waba["id"] = target_id
            waba["name"] = response_json.get("name")
            wabas.append(waba)

        return Response(wabas)

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
