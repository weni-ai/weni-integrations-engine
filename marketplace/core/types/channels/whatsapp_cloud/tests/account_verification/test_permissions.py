"""Tests for AppProjectManagePermission."""

import uuid
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.account_verification.permissions import (
    AppProjectManagePermission,
)


User = get_user_model()


class AppProjectManagePermissionTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.app = App.objects.create(
            code="wpp-cloud",
            config={},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.permission = AppProjectManagePermission()

    def _view(self, app_uuid=None):
        view = MagicMock()
        view.kwargs = {
            "app_uuid": app_uuid if app_uuid is not None else str(self.app.uuid)
        }
        return view

    def _grant(self, role):
        authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        authorization.set_role(role)
        return authorization

    def test_unauthenticated_request_is_denied(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, self._view()))

    def test_missing_app_uuid_is_denied(self):
        request = self.factory.get("/")
        request.user = self.user
        view = MagicMock()
        view.kwargs = {}
        self.assertFalse(self.permission.has_permission(request, view))

    def test_unknown_app_uuid_is_denied(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertFalse(
            self.permission.has_permission(
                request, self._view(app_uuid=str(uuid.uuid4()))
            )
        )

    def test_admin_can_write(self):
        self._grant(ProjectAuthorization.ROLE_ADMIN)
        request = self.factory.post("/")
        request.user = self.user
        self.assertTrue(self.permission.has_permission(request, self._view()))

    def test_contributor_can_write(self):
        self._grant(ProjectAuthorization.ROLE_CONTRIBUTOR)
        request = self.factory.post("/")
        request.user = self.user
        self.assertTrue(self.permission.has_permission(request, self._view()))

    def test_viewer_cannot_write(self):
        self._grant(ProjectAuthorization.ROLE_VIEWER)
        request = self.factory.post("/")
        request.user = self.user
        self.assertFalse(self.permission.has_permission(request, self._view()))

    def test_viewer_can_read(self):
        self._grant(ProjectAuthorization.ROLE_VIEWER)
        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(self.permission.has_permission(request, self._view()))

    def test_user_without_authorization_is_denied(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertFalse(self.permission.has_permission(request, self._view()))

    def test_internal_communication_perm_falls_back_to_allow(self):
        self._grant_internal_perm()
        request = self.factory.post("/")
        request.user = self.user
        self.assertTrue(self.permission.has_permission(request, self._view()))

    def _grant_internal_perm(self):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(User)
        perm, _ = Permission.objects.get_or_create(
            content_type=ct,
            codename="can_communicate_internally",
            defaults={"name": "Can communicate internally"},
        )
        self.user.user_permissions.add(perm)
