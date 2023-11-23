import uuid

from unittest.mock import patch, PropertyMock

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App

from ..views import VtexViewSet
from ..type import VtexType


apptype = VtexType()


class CreateVtexAppTestCase(APIBaseTestCase):
    url = reverse("vtex-app-list")
    view_class = VtexViewSet

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


class RetrieveVtexAppTestCase(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()

        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-detail", kwargs={"uuid": self.app.uuid})

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


class MockVtexProductsService:
    def __init__(self, *args, **kwargs):
        pass

    def is_domain_valid(self, domain):
        valid_domains = ["valid.domain.com"]
        return domain in valid_domains

    def configure(self, app, domain):
        if not self.is_domain_valid(domain):
            raise ValueError("The domain provided is invalid.")

        app.configured = True
        app.config["domain"] = domain
        app.save()
        return app


class SetUpView(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-configure", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})


class SetUpService(SetUpView):
    def setUp(self):
        super().setUp()

        # Mock service
        mock_service = MockVtexProductsService()
        patcher = patch.object(
            self.view_class, "service", PropertyMock(return_value=mock_service)
        )
        self.addCleanup(patcher.stop)
        patcher.start()


class ConfigureVtexAppTestCase(SetUpService):
    def test_configure_app_success(self):
        body = {"domain": "valid.domain.com"}
        response = self.request.patch(self.url, body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_app_failure(self):
        body = {"domain": "invalid.domain.com"}
        response = self.request.patch(self.url, body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DeleteVtexAppTestCase(APIBaseTestCase):
    view_class = VtexViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-detail", kwargs={"uuid": self.app.uuid})

    def test_delete_app_plataform(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())

    def test_delete_app_with_wrong_project_uuid(self):
        response = self.request.delete(self.url, uuid=str(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_app_without_autorization(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_release_ecommerce_service(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())
