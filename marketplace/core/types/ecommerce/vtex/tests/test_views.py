import uuid

from unittest.mock import patch
from unittest.mock import Mock
from unittest.mock import PropertyMock

from django.urls import reverse

from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from marketplace.core.types.ecommerce.vtex.views import VtexViewSet
from marketplace.core.types.ecommerce.vtex.type import VtexType


apptype = VtexType()


class MockVtexService:
    def get_vtex_app_or_error(self, project_uuid):
        mock_app = Mock(spec=App)
        mock_app.config = {}
        return mock_app

    def check_is_valid_credentials(self, credentials):
        return True

    def configure(self, app, credentials):
        app.configured = True
        app.config["api_credentials"] = credentials.to_dict()
        app.save()
        return app


class SetUpService(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()

        # Mock service
        self.mock_service = MockVtexService()
        patcher = patch.object(
            self.view_class,
            "service",
            new_callable=PropertyMock,
            return_value=self.mock_service,
        )
        self.addCleanup(patcher.stop)
        patcher.start()


class CreateVtexAppTestCase(SetUpService):
    url = reverse("vtex-app-list")

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {
            "project_uuid": project_uuid,
            "app_key": "valid-app-key",
            "app_token": "valid-app-token",
            "domain": "valid.domain.com",
        }
        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    def test_request_ok(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_VTEX)

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_configuration_exception(self):
        original_configure = self.mock_service.configure
        self.mock_service.configure = Mock(side_effect=Exception("Configuration error"))

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Configuration error")

        self.mock_service.configure = original_configure


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
