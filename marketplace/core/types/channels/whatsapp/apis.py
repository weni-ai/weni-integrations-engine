import requests
from requests.models import Response
from django.conf import settings

from .exceptions import FacebookApiException


def _request(url: str, method: str = "GET", *args, **kwargs):
    return requests.request(method.upper(), url, *args, **kwargs)


class BaseOnPremiseAPI(object):
    _endpoint: str = None

    def __init__(self, base_url: str, auth_token: str):
        self._base_url = base_url
        self._auth_token = auth_token

    @property
    def _url(self) -> dict:
        return self._base_url + self._endpoint

    @property
    def _headers(self) -> dict:
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self._auth_token}"}

    def _validate_response(self, response: Response) -> None:
        errors = response.json().get("errors", None)
        if errors is not None:
            raise FacebookApiException(errors)

    def _request(self, url: str, method: str = "get", *args, **kwargs) -> Response:
        response = getattr(requests, method.lower())(url, *args, **kwargs)
        self._validate_response(response)
        return response


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
        data_points_dict = next(filter(lambda data_content: "data_points" in data_content, data))
        return data_points_dict.get("data_points")

    def __dict__(self) -> dict:
        return dict(
            user_initiated=self._user_initiated,
            business_initiated=self._business_initiated,
            total=self._total,
        )


class OnPremiseBusinessProfile(object):

    address: str = None
    description: str = None
    email: str = None
    vertical: str = None
    websites: str = None

    def __init__(self, profile_settings: dict):
        self._business_profile = profile_settings.get("business", {}).get("profile")
        self._set_properties()

    def _set_properties(self):
        self.__dict__.update(self._business_profile)


class BaseFacebookBaseApi(object):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _validate_response(self, response: Response):
        error = response.json().get("error", None)
        if error is not None:
            raise FacebookApiException(error.get("message"))

    def _request(self, url: str, method: str = "GET", *args, **kwargs) -> Response:
        response = _request(url, method, *args, **kwargs)
        self._validate_response(response)

        return response


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

    def conversations(self, waba_id: str, access_token: str, start: str, end: str) -> Conversations:
        fields = self._get_fields(start, end)
        params = dict(fields=fields, access_token=access_token)
        response = self._request(
            f"https://graph.facebook.com/v13.0/{waba_id}", params=params
        )  # TODO: Change to environment variables
        conversation_analytics = response.json().get("conversation_analytics")

        return Conversations(conversation_analytics)


class FacebookWABAApi(BaseFacebookBaseApi):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def get_waba(self, waba_id: str) -> dict:
        response = self._request(
            f"https://graph.facebook.com/v13.0/{waba_id}/", headers=self._headers
        )  # TODO: Change to environment variables

        return response.json()


class FacebookPhoneNumbersAPI(BaseFacebookBaseApi):
    def _get_url(self, endpoint: str) -> str:
        return f"{settings.WHATSAPP_API_URL}/{endpoint}"

    def get_phone_numbers(self, waba_id: str) -> list:
        url = self._get_url(f"{waba_id}/phone_numbers")
        response = self._request(url, headers=self._headers)

        return response.json().get("data", [])

    def get_phone_number(self, phone_number_id: str):
        url = self._get_url(phone_number_id)
        response = self._request(url, headers=self._headers)

        return response.json()


class OnPremiseBusinessProfileAPI(BaseOnPremiseAPI):

    _endpoint = "/v1/settings/business/profile"

    def get_business_profile(self) -> OnPremiseBusinessProfile:
        response = self._request(self._url, headers=self._headers)
        profile_settings = response.json().get("settings")
        return OnPremiseBusinessProfile(profile_settings)


class OnPremiseProfileAPI(BaseOnPremiseAPI):

    _endpoint = "/v1/settings/profile/about"

    def get_about_text(self) -> str:
        response = self._request(self._url, headers=self._headers)
        profile_settings = response.json().get("settings")
        return profile_settings.get("profile", {}).get("about", {}).get("text")


class OnPremisePhotoAPI(BaseOnPremiseAPI):

    _endpoint = "/v1/settings/profile/photo?format=link"

    def get_photo_url(self) -> str:
        response = self._request(self._url, headers=self._headers)
        profile_settings = response.json().get("settings")
        return profile_settings.get("profile", {}).get("photo", {}).get("link")
