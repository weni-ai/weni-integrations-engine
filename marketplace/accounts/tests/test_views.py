import uuid
import requests
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from marketplace.accounts.views import UserPermissionViewSet, UserViewSet
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import User, ProjectAuthorization


class BaseTest(APIBaseTestCase):
    def setUp(self):
        super().setUp()

class UserPermissionViewTestCase(BaseTest):
    project_uuid = uuid.uuid4()
    url = reverse("user_permission-detail", args=[project_uuid])

    view_class = UserPermissionViewSet

    @property
    def view(self):
        return self.view_class.as_view({"patch": "partial_update"})

    def test_patch(self):
        data = {
            "user": "test",
            "project_uuid": str(self.project_uuid),
            "data": "18-05-2022",
            "channeltype_code": "test"
        }
        patch_user = self.request.patch(url=self.url, project_uuid=self.project_uuid, body=data)

        self.assertEqual(patch_user.json["project_uuid"], str(self.project_uuid))


class UserViewTestCase(BaseTest):
    project_uuid = uuid.uuid4()
    url = reverse("user-list")

    view_class = UserViewSet

    @property
    def view(self):
        return self.view_class.as_view({"post": "create"})

    def test_patch(self):

        test_user = User.objects.create(email="test@weni.ai", first_name="User", last_name="Test")

        data = {
            "email": "test@weni.ai",
            "photo_url": "",
            "first_name": "User1",
            "last_name": "Test"
        }
        patch_user = self.request.post(url=self.url, body=data)

        test_user = User.objects.get(email="test@weni.ai")

        self.assertEqual(patch_user.json["first_name"], test_user.first_name)
