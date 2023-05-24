import abc
import calendar
from typing import TYPE_CHECKING
from datetime import datetime

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from rest_framework.request import Request
    from .interfaces import ProfileHandlerInterface, BusinessProfileHandlerInterface

from marketplace.accounts.permissions import ProjectViewPermission
from .requests.facebook import FacebookConversationAPI
from .exceptions import FacebookApiException, UnableProcessProfilePhoto
from .serializers import WhatsAppBusinessContactSerializer, WhatsAppProfileSerializer


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


class WhatsAppConversationsMixin(object, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def app_waba_id(self) -> dict:
        pass  # pragma: no cover

    @action(detail=True, methods=["GET"], permission_classes=[ProjectViewPermission])
    def conversations(self, request: "Request", **kwargs) -> Response:
        date_params = QueryParamsParser(request.query_params)

        try:
            conversations = FacebookConversationAPI().conversations(
                waba_id=self.app_waba_id,
                access_token=settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN,
                start=date_params.start,
                end=date_params.end,
            )
        except FacebookApiException as error:
            raise ValidationError(error)

        return Response(conversations.__dict__())


class WhatsAppContactMixin(object, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def profile_config_credentials(self) -> dict:
        pass  # pragma: no cover

    def business_profile_class(self) -> "BusinessProfileHandlerInterface":
        pass  # pragma: no cover

    @action(
        detail=True,
        methods=["GET", "PATCH"],
        serializer_class=WhatsAppBusinessContactSerializer,
    )
    def contact(self, request: "Request", **kwargs) -> Response:
        profile_handler = self.business_profile_class(**self.profile_config_credentials)

        try:
            serializer: WhatsAppBusinessContactSerializer = None

            if request.method == "GET":
                profile = profile_handler.get_profile()
                serializer = self.get_serializer(profile)

            if request.method == "PATCH":
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                profile_handler.set_profile(serializer.validated_data)

            return Response(serializer.data)

        except FacebookApiException:
            raise ValidationError(
                "There was a problem requesting the On-Premise API, check if your authentication token is correct"
            )


class WhatsAppProfileMixin(object, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def profile_class(self) -> "ProfileHandlerInterface":
        pass  # pragma: no cover

    @abc.abstractproperty
    def profile_config_credentials(self) -> dict:
        pass  # pragma: no cover

    @action(
        detail=True,
        methods=["GET", "PATCH", "DELETE"],
        serializer_class=WhatsAppProfileSerializer,
    )
    def profile(self, request: "Request", **kwargs) -> Response:
        # TODO: Split this view in a APIView
        profile_handler = self.profile_class(**self.profile_config_credentials)

        try:
            serializer: WhatsAppProfileSerializer = None

            if request.method == "GET":
                profile = profile_handler.get_profile()
                serializer = self.get_serializer(profile)

            elif request.method == "PATCH":
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                profile_handler.set_profile(**serializer.validated_data)

            elif request.method == "DELETE":
                profile_handler.delete_profile_photo()

            return Response(getattr(serializer, "data", None))

        except FacebookApiException:
            raise ValidationError(
                "There was a problem requesting the On-Premise API, check if your authentication token is correct"
            )

        except UnableProcessProfilePhoto as error:
            raise ValidationError(error)
