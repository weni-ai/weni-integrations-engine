import uuid

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from ..views import OmieViewSet
from ..type import OmieType


apptype = OmieType()


class CreateOmieAppTestCase(APIBaseTestCase):
    url = reverse("omie-app-list")
    view_class = OmieViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    def test_request_ok(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveOmieAppTestCase(APIBaseTestCase):
    view_class = OmieViewSet

    def setUp(self):
        super().setUp()

        self.app = apptype.create_app(created_by=self.user, project_uuid=str(uuid.uuid4()))
        self.user_authorization = self.user.authorizations.create(project_uuid=self.app.project_uuid)
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("omie-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class ConfigureOmieAppTestCase(APIBaseTestCase):
    view_class = OmieViewSet

    def setUp(self):
        super().setUp()

        self.app = apptype.create_app(created_by=self.user, project_uuid=str(uuid.uuid4()))
        self.user_authorization = self.user.authorizations.create(project_uuid=self.app.project_uuid)
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("omie-app-configure", kwargs={"uuid": self.app.uuid})
        self.body = {"config": {"name": "123", "app_key": "123", "app_secret": "4234"}}

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    def test_request_ok(self):
        response = self.request.patch(self.url, uuid=self.app.uuid, body=self.body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
