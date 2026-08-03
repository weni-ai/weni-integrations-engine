from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from weni_commons.auth import WeniAuthContext

from marketplace.accounts.models import ProjectAuthorization
from marketplace.accounts.permissions import ProjectManagePermission


User = get_user_model()

AUTHORIZED_PROJECT = "11111111-1111-1111-1111-111111111111"
FOREIGN_PROJECT = "22222222-2222-2222-2222-222222222222"


class ProjectManagePermissionTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = ProjectManagePermission()
        self.view = APIView()
        self.user = User.objects.create_user(email="user@weni.ai")
        self.user.authorizations.create(
            project_uuid=AUTHORIZED_PROJECT, role=ProjectAuthorization.ROLE_ADMIN
        )

    def _build_request(self, body=None, auth=None, headers=None):
        request = self.factory.post(
            "/", data=body or {}, format="json", **(headers or {})
        )
        force_authenticate(request, user=self.user, token=auth)
        return APIView().initialize_request(request)

    def test_allows_when_body_project_is_authorized(self):
        request = self._build_request(body={"project_uuid": AUTHORIZED_PROJECT})

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_denies_when_body_project_is_not_authorized(self):
        request = self._build_request(body={"project_uuid": FOREIGN_PROJECT})

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_falls_back_to_header_when_body_has_no_project(self):
        request = self._build_request(headers={"HTTP_PROJECT_UUID": AUTHORIZED_PROJECT})

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_denies_when_no_project_can_be_resolved(self):
        request = self._build_request()

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_auth_context_project_takes_precedence_over_body(self):
        """The view acts on the context project, so the body must not decide access."""
        request = self._build_request(
            body={"project_uuid": AUTHORIZED_PROJECT},
            auth=WeniAuthContext(project_uuid=FOREIGN_PROJECT),
        )

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_allows_when_auth_context_project_is_authorized(self):
        request = self._build_request(
            body={"project_uuid": FOREIGN_PROJECT},
            auth=WeniAuthContext(project_uuid=AUTHORIZED_PROJECT),
        )

        self.assertTrue(self.permission.has_permission(request, self.view))
