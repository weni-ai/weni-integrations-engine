import json

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
from rest_framework.response import Response
from rest_framework.views import APIView


User = get_user_model()


class Request(object):
    def __init__(self, test_instance: TestCase):
        self.test_instance = test_instance
        self.factory = APIRequestFactory()

    def get_response_data(self, response: Response) -> dict:
        return json.loads(json.dumps(response.data))

    def get(self, url: str, **kwargs) -> Response:
        request = self.factory.get(url)
        force_authenticate(request, user=self.test_instance.user)
        response = self.test_instance.view(request, **kwargs)
        setattr(response, "json", self.get_response_data(response))

        return response

    def post(self):
        # TODO: Implements POST method later
        ...

    def put(self):
        # TODO: Implements PUT method later
        ...

    def delete(self):
        # TODO: Implements DELETE method later
        ...


class APIBaseTestCase(TestCase):
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
