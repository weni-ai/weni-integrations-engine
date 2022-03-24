from typing import TYPE_CHECKING

import requests
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from marketplace.accounts.permissions import ProjectViewPermission
from .serializers import WhatsAppSerializer


class WhatsAppViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    @action(detail=True, methods=["GET"], permission_classes=[ProjectViewPermission])
    def conversations(self, request: "Request", **kwargs) -> Response:
        """
        obs: this is just a mock to speed up the front end delivery
        """
        self.get_object()
        request.query_params.get("start")
        request.query_params.get("end")

        return Response(dict(incoming=50, outgoing=50, total=100))

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
