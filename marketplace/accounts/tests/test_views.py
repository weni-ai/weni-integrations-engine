import uuid

from django.urls import reverse
from rest_framework import status

from marketplace.accounts.views import UserPermissionViewSet, UserViewSet, UserAPITokenAPIView
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import User, ProjectAuthorization


class UserPermissionViewTestCase(APIBaseTestCase):
    project_uuid = uuid.uuid4()
    url = reverse("user_permission-detail", args=[project_uuid])

    view_class = UserPermissionViewSet

    def setUp(self):
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"patch": "partial_update"})

    def test_update_user_permission_patch(self):
        data = {
            "user": "test",
            "project_uuid": str(self.project_uuid),
            "data": "18-05-2022",
            "channeltype_code": "test",
            "role": 3,
        }
        self.request.patch(url=self.url, project_uuid=self.project_uuid, body=data)

        user = ProjectAuthorization.objects.get(project_uuid=self.project_uuid)

        self.assertEqual(str(user.user), "test")
        self.assertEqual(user.project_uuid, self.project_uuid)
        self.assertEqual(user.role, 3)


class UserViewTestCase(APIBaseTestCase):
    project_uuid = uuid.uuid4()
    url = reverse("user-list")

    view_class = UserViewSet

    def setUp(self):
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"post": "create"})

    def test_update_user_patch(self):
        test_user = User.objects.create(email="test@weni.ai", first_name="User", last_name="Test")

        data = {"email": "test@weni.ai", "photo_url": "https://photo.com", "first_name": "User1", "last_name": "Test1"}
        self.request.post(url=self.url, body=data)

        test_user_changed = User.objects.get(email="test@weni.ai")

        self.assertNotEqual(test_user.first_name, test_user_changed.first_name)
        self.assertNotEqual(test_user.last_name, test_user_changed.last_name)
        self.assertNotEqual(test_user.photo_url, test_user_changed.photo_url)


class UserAPITokenTestCase(APIBaseTestCase):

    view_class = UserAPITokenAPIView
    url = reverse("user_api_token")

    @property
    def view(self):
        return self.view_class.as_view()

    def test_returns_400_when_not_sent_project_uuid(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
