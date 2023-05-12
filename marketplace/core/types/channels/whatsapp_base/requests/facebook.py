import requests
from requests.models import Response

from ..exceptions import FacebookApiException

from django.conf import settings

WHATSAPP_VERSION = settings.WHATSAPP_VERSION


class Conversations(object):
    _user_initiated = 0
    _business_initiated = 0

    def __init__(self, conversation_analytics: dict) -> None:
        if conversation_analytics is not None:
            data = conversation_analytics.get("data")
            data_points = self._get_data_points(data)

            self._calculate_conversation(data_points)

    @property
    def _total(self) -> int:
        return self._user_initiated + self._business_initiated

    def _calculate_conversation(self, data_points: list) -> None:
        for data_point in data_points:
            conversation_direction = data_point.get("conversation_direction")
            conversation_count = data_point.get("conversation")

            if conversation_direction == "BUSINESS_INITIATED":
                self._business_initiated += conversation_count
            elif conversation_direction == "USER_INITIATED":
                self._user_initiated += conversation_count

    def _get_data_points(self, data: list):
        data_points_dict = next(
            filter(lambda data_content: "data_points" in data_content, data)
        )
        return data_points_dict.get("data_points")

    def __dict__(self) -> dict:
        return dict(
            user_initiated=self._user_initiated,
            business_initiated=self._business_initiated,
            total=self._total,
        )


class FacebookConversationAPI(object):  # TODO: Use BaseFacebookBaseApi
    def _validate_response(self, response: Response):
        error = response.json().get("error", None)
        if error is not None:
            raise FacebookApiException(error.get("message"))

    def _request(self, *args, **kwargs) -> Response:
        response = requests.get(*args, **kwargs)
        self._validate_response(response)

        return response

    def _get_fields(self, start: str, end: str):
        fields = "conversation_analytics"
        fields += f".start({start})"
        fields += f".end({end})"
        fields += ".granularity(DAILY)"
        fields += ".phone_numbers([])"
        fields += '.conversation_types(["REGULAR"])'
        fields += '.dimensions(["conversation_type", "conversation_direction"])'

        return fields

    def conversations(
        self, waba_id: str, access_token: str, start: str, end: str
    ) -> Conversations:
        fields = self._get_fields(start, end)
        params = dict(fields=fields, access_token=access_token)
        response = self._request(
            f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}", params=params
        )  # TODO: Change to environment variables
        conversation_analytics = response.json().get("conversation_analytics")

        return Conversations(conversation_analytics)
