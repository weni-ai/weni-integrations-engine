import calendar
from typing import TYPE_CHECKING
from datetime import datetime

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.accounts.permissions import ProjectViewPermission
from .requests.facebook import FacebookConversationAPI
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


class WhatsAppConversationsMixin(object):
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
