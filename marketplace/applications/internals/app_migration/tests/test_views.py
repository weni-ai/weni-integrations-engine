import json
import uuid
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from marketplace.applications.internals.app_migration.views import (
    AppMigrationCreateView,
    AppMigrationDetailView,
    AppMigrationRepublishView,
    AppMigrationStatusView,
)
from marketplace.applications.models import App, AppMigration, AppMigrationStatus
from marketplace.applications.usecases.app_migration.migrate_app import (
    MODULE_STATUS_ERROR,
    MODULE_STATUS_SUCCESS,
    MigrateAppUseCase,
)
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from marketplace.projects.models import Project

User = get_user_model()


class AppMigrationViewsTestCase(PermissionTestCaseMixin, TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="migration_view@marketplace.ai")
        self.grant_permission(self.user, "can_communicate_internally")

        self.project_from = Project.objects.create(
            uuid=uuid.uuid4(), name="View Source Project", created_by=self.user
        )
        self.project_to = Project.objects.create(
            uuid=uuid.uuid4(), name="View Dest Project", created_by=self.user
        )
        self.channel_uuid = uuid.uuid4()
        self.app = App.objects.create(
            code="wwc",
            config={},
            project_uuid=self.project_from.uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
            flow_object_uuid=self.channel_uuid,
            configured=True,
        )

    def test_create_migration_by_app_uuid(self):
        mock_publisher = Mock()
        use_case = MigrateAppUseCase(publisher=mock_publisher)

        with patch(
            "marketplace.applications.internals.app_migration.views.MigrateAppUseCase",
            return_value=use_case,
        ):
            request = self.factory.post(
                "/internals/app-migrations",
                {
                    "app_uuid": str(self.app.uuid),
                    "project_to": str(self.project_to.uuid),
                },
                format="json",
            )
            force_authenticate(request, user=self.user)

            with self.captureOnCommitCallbacks(execute=True):
                response = AppMigrationCreateView.as_view()(request)
            response.render()

        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        migration = AppMigration.objects.get(uuid=content["event_id"])
        self.assertEqual(migration.status, AppMigrationStatus.IN_PROGRESS)
        self.assertEqual(content["app_uuid"], str(self.app.uuid))
        self.assertEqual(content["channel_uuid"], str(self.channel_uuid))
        self.assertEqual(content["project_from"], str(self.project_from.uuid))
        self.assertEqual(content["project_to"], str(self.project_to.uuid))

        self.app.refresh_from_db()
        self.assertEqual(self.app.project_uuid, self.project_to.uuid)
        mock_publisher.publish_channel_migrated.assert_called_once()

    def test_create_migration_by_channel_uuid(self):
        mock_publisher = Mock()
        use_case = MigrateAppUseCase(publisher=mock_publisher)

        with patch(
            "marketplace.applications.internals.app_migration.views.MigrateAppUseCase",
            return_value=use_case,
        ):
            request = self.factory.post(
                "/internals/app-migrations",
                {
                    "channel_uuid": str(self.channel_uuid),
                    "project_to": str(self.project_to.uuid),
                },
                format="json",
            )
            force_authenticate(request, user=self.user)

            with self.captureOnCommitCallbacks(execute=True):
                response = AppMigrationCreateView.as_view()(request)
            response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_rejects_both_lookup_keys(self):
        request = self.factory.post(
            "/internals/app-migrations",
            {
                "app_uuid": str(self.app.uuid),
                "channel_uuid": str(self.channel_uuid),
                "project_to": str(self.project_to.uuid),
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = AppMigrationCreateView.as_view()(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_migration(self):
        migration = AppMigration.objects.create(
            app=self.app,
            flow_object_uuid=self.channel_uuid,
            project_from=self.project_from.uuid,
            project_to=self.project_to.uuid,
            status=AppMigrationStatus.IN_PROGRESS,
            modules_status={"flows": {"status": MODULE_STATUS_SUCCESS}},
        )

        request = self.factory.get(f"/internals/app-migrations/{migration.uuid}")
        force_authenticate(request, user=self.user)
        response = AppMigrationDetailView.as_view()(request, event_id=migration.uuid)
        response.render()
        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["event_id"], str(migration.uuid))
        self.assertEqual(content["channel_uuid"], str(self.channel_uuid))
        self.assertEqual(
            content["modules_status"]["flows"]["status"], MODULE_STATUS_SUCCESS
        )

    @override_settings(APP_MIGRATION_EXPECTED_MODULES=["flows"])
    def test_register_module_status(self):
        migration = AppMigration.objects.create(
            app=self.app,
            flow_object_uuid=self.channel_uuid,
            project_from=self.project_from.uuid,
            project_to=self.project_to.uuid,
            status=AppMigrationStatus.IN_PROGRESS,
        )

        request = self.factory.post(
            f"/internals/app-migrations/{migration.uuid}/status",
            {
                "module": "flows",
                "status": MODULE_STATUS_ERROR,
                "error": "db unavailable",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = AppMigrationStatusView.as_view()(request, event_id=migration.uuid)
        response.render()
        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["status"], AppMigrationStatus.PARTIAL_ERROR)
        self.assertEqual(content["modules_status"]["flows"]["error"], "db unavailable")

    def test_republish(self):
        migration = AppMigration.objects.create(
            app=self.app,
            flow_object_uuid=self.channel_uuid,
            project_from=self.project_from.uuid,
            project_to=self.project_to.uuid,
            status=AppMigrationStatus.PUBLISH_FAILED,
        )
        mock_publisher = Mock()

        with patch(
            "marketplace.applications.internals.app_migration.views.MigrateAppUseCase",
            return_value=MigrateAppUseCase(publisher=mock_publisher),
        ):
            request = self.factory.post(
                f"/internals/app-migrations/{migration.uuid}/republish",
                {},
                format="json",
            )
            force_authenticate(request, user=self.user)
            response = AppMigrationRepublishView.as_view()(
                request, event_id=migration.uuid
            )
            response.render()

        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["status"], AppMigrationStatus.IN_PROGRESS)
        mock_publisher.publish_channel_migrated.assert_called_once()

    def test_create_requires_internal_permission(self):
        unauthorized = User.objects.create_user(email="no_perm@marketplace.ai")
        request = self.factory.post(
            "/internals/app-migrations",
            {
                "app_uuid": str(self.app.uuid),
                "project_to": str(self.project_to.uuid),
            },
            format="json",
        )
        force_authenticate(request, user=unauthorized)
        response = AppMigrationCreateView.as_view()(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
