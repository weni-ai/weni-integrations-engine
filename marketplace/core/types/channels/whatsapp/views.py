from typing import TYPE_CHECKING

import requests
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from .serializers import WhatsAppSerializer
from .facades import (
    WhatsAppFacade,
    AssignedUsersAPI,
    CreditLineAttachAPI,
    CreditLineAllocationConfigAPI,
    CreditLineValidatorAPI,
    CreditLineFacade,
)


class WhatsAppViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        user = self.request.user
        type_class = self.type_class

        validated_data = serializer.validated_data
        target_id = validated_data.get("target_id")

        assigned_users_api = AssignedUsersAPI(type_class)

        attach_api = CreditLineAttachAPI(type_class)
        allocation_config_api = CreditLineAllocationConfigAPI(type_class)
        validator_api = CreditLineValidatorAPI(type_class)

        credit_line_facade = CreditLineFacade(attach_api, allocation_config_api, validator_api)

        whatsapp = WhatsAppFacade(assigned_users_api, credit_line_facade)
        whatsapp.create(target_id)

    @action(detail=False, methods=["GET"], url_name="shared-wabas", url_path="shared-wabas")
    def shared_wabas(self, request: "Request", **kwargs):
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        headers = {"Authorization": f"Bearer {self.type_class.SYSTEM_USER_ACCESS_TOKEN}"}

        response = requests.get(f"{self.type_class.API_URL}/debug_token?input_token={input_token}", headers=headers)
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
            response = requests.get(f"{self.type_class.API_URL}/{target_id}/?access_token={input_token}")
            response.raise_for_status()

            response_json = response.json()

            waba = dict()
            waba["id"] = target_id
            waba["name"] = response_json.get("name")
            wabas.append(waba)

        return Response(wabas)
