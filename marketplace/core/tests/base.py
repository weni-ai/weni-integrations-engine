import json

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
from rest_framework.response import Response
from rest_framework.views import APIView

from marketplace.core.types.base import AppType
from marketplace.core.types import APPTYPES


User = get_user_model()


class FakeRequestsResponse(object):
    def __init__(self, data: dict, error_message: str = None):
        self._data = data
        self.error_message = error_message

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class Request(object):
    def __init__(self, test_instance: TestCase):
        self.test_instance = test_instance
        self.factory = APIRequestFactory()
        self.set_view(test_instance.view)
        self.set_user(test_instance.user)

    def get_response_data(self, response: Response) -> dict:
        return json.loads(json.dumps(response.data))

    def set_view(self, view):
        self._view = view

    def set_user(self, user):
        self._user = user

    def _get_response(self, request, **kwargs) -> Response:
        response = self._view(request, **kwargs)
        setattr(response, "json", self.get_response_data(response))

        return response

    def get(self, url: str, **kwargs) -> Response:
        request = self.factory.get(url)
        force_authenticate(request, user=self._user)

        return self._get_response(request, **kwargs)

    def post(self, url: str, body=None, **kwargs) -> Response:
        request = self.factory.post(
            url, data=json.dumps(body), content_type="application/json"
        )
        force_authenticate(request, user=self._user)

        return self._get_response(request, **kwargs)

    def put(self, url: str, body=None, **kwargs) -> Response:
        request = self.factory.put(
            url, data=json.dumps(body), content_type="application/json"
        )
        force_authenticate(request, user=self._user)

        return self._get_response(request, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        request = self.factory.delete(url, content_type="application/json")
        force_authenticate(request, user=self._user)

        return self._get_response(request, **kwargs)

    def patch(self, url: str, body=None, **kwargs) -> Response:
        request = self.factory.patch(
            url, data=json.dumps(body), content_type="application/json"
        )
        force_authenticate(request, user=self._user)

        return self._get_response(request, **kwargs)


class APIBaseTestCase(TestCase):
    ACTION_CREATE = dict(post="create")
    ACTION_RETRIEVE = dict(get="retrieve")
    ACTION_UPDATE = dict(put="update")
    ACTION_DESTROY = dict(delete="destroy")
    ACTION_LIST = dict(get="list")

    url: str

    view_class: APIView
    request_class = Request

    def setUp(self):
        super().setUp()

        self.super_user = User.objects.create_superuser(email="admin@marketplace.ai")
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

        self.request = self._get_request()

    @property
    def view(self):
        raise NotImplementedError()

    def _get_request(self):
        return self.request_class(self)


class MockDynamicAppType:
    """
    Lets you add a list of apptypes dynamically
    Usage:

    with MockDynamicAppType([<APPTYPE_INSTANCES>]):
        ...
    """

    def __init__(self, apptypes: list):
        self.apptypes = apptypes

    def __enter__(self):
        for apptype in self.apptypes:
            assert isinstance(
                apptype, AppType
            ), f"Expected a `AppType`, `{apptype.__class__.__name__}` is not valid!"
            APPTYPES[apptype.code] = apptype

    def __exit__(self, *args):
        for apptype in self.apptypes:
            APPTYPES.pop(apptype.code)
