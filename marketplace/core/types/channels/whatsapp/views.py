import calendar
from typing import TYPE_CHECKING
from datetime import datetime

import requests
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from marketplace.accounts.permissions import ProjectViewPermission
from .serializers import WhatsAppSerializer
from .apis import FacebookConversationAPI
from .exceptions import FacebookApiException


class QueryParamsParser(object):

    QUERY_PARAMS_START_KEY = "start"
    QUERY_PARAMS_END_KEY = "end"

    DATE_FORMAT = "%m-%d-%Y"

    ERROR_MESSAGE = "Parameter `{}` cannot be found or is invalid"

    def __init__(self, query_params: dict):
        self._query_params = query_params
        self.start = self._parse_to_unix(self._get_start())
        self.end = self._parse_to_unix(self._get_end())

    def _parse_to_unix(self, time: datetime) -> str:
        return calendar.timegm(time.utctimetuple())

    def _get_start(self) -> datetime:
        return self._get_param_datetime(self.QUERY_PARAMS_START_KEY)

    def _get_end(self) -> datetime:
        end = self._get_param_datetime(self.QUERY_PARAMS_END_KEY)
        return end.replace(hour=23, minute=59, second=59)

    def _get_param_datetime(self, key: str) -> datetime:
        param = self._query_params.get(key, None)
        try:
            return datetime.strptime(param, self.DATE_FORMAT)
        except (ValueError, TypeError):
            self._raise(key)

    def _raise(self, field: str):
        raise ValidationError(self.ERROR_MESSAGE.format(field))


class WhatsAppViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    @action(detail=True, methods=["GET"], permission_classes=[ProjectViewPermission])
    def conversations(self, request: "Request", **kwargs) -> Response:
        app = self.get_object()
        waba_id = app.config.get("fb_business_id", None)
        access_token = app.config.get("fb_access_token", None)

        if waba_id is None:
            raise ValidationError("This app does not have WABA (Whatsapp Business Account ID) configured")

        if access_token is None:
            raise ValidationError("This app does not have the Facebook Access Token configured")

        date_params = QueryParamsParser(request.query_params)

        try:
            conversations = FacebookConversationAPI().conversations(
                waba_id, access_token, date_params.start, date_params.end
            )
        except FacebookApiException as error:
            raise ValidationError(error)

        return Response(conversations.__dict__())

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
