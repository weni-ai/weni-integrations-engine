import uuid
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from marketplace.applications.models import App, AppMigration, AppMigrationStatus
from marketplace.applications.usecases.app_migration.exceptions import (
    ActiveMigrationConflictError,
    AmbiguousLookupError,
    AppMigrationNotFoundError,
    AppMigrationRepublishError,
    AppNotFoundError,
    ChannelNotFoundError,
    MissingFlowObjectUuidError,
    ProjectNotFoundError,
    SameProjectMigrationError,
)
from marketplace.applications.usecases.app_migration.migrate_app import (
    MODULE_STATUS_ERROR,
    MODULE_STATUS_SUCCESS,
    MigrateAppUseCase,
)
from marketplace.projects.models import Project

User = get_user_model()


class MigrateAppUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="migration@marketplace.ai")
        self.project_from = Project.objects.create(
            uuid=uuid.uuid4(), name="Source Project", created_by=self.user
        )
        self.project_to = Project.objects.create(
            uuid=uuid.uuid4(), name="Destination Project", created_by=self.user
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
        self.mock_publisher = Mock()
        self.use_case = MigrateAppUseCase(publisher=self.mock_publisher)

    def test_execute_by_app_uuid_reassigns_project_and_publishes(self):
        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
                requested_by=self.user.email,
            )

        self.app.refresh_from_db()
        migration.refresh_from_db()

        self.assertEqual(self.app.project_uuid, self.project_to.uuid)
        self.assertEqual(migration.project_from, self.project_from.uuid)
        self.assertEqual(migration.project_to, self.project_to.uuid)
        self.assertEqual(migration.flow_object_uuid, self.channel_uuid)
        self.assertEqual(migration.status, AppMigrationStatus.IN_PROGRESS)
        self.assertIsNotNone(migration.published_at)
        self.assertEqual(migration.requested_by, self.user.email)

        self.mock_publisher.publish_channel_migrated.assert_called_once_with(
            event_id=migration.uuid,
            channel_uuid=self.channel_uuid,
            app_uuid=self.app.uuid,
            project_from=self.project_from.uuid,
            project_to=self.project_to.uuid,
        )

    def test_execute_by_channel_uuid(self):
        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                channel_uuid=self.channel_uuid,
                project_to=self.project_to.uuid,
            )

        self.app.refresh_from_db()
        self.assertEqual(self.app.project_uuid, self.project_to.uuid)
        self.assertEqual(migration.app_id, self.app.id)

    def test_execute_rejects_both_lookup_keys(self):
        with self.assertRaises(AmbiguousLookupError):
            self.use_case.execute(
                app_uuid=self.app.uuid,
                channel_uuid=self.channel_uuid,
                project_to=self.project_to.uuid,
            )

    def test_execute_rejects_neither_lookup_key(self):
        with self.assertRaises(AmbiguousLookupError):
            self.use_case.execute(project_to=self.project_to.uuid)

    def test_execute_is_idempotent_for_active_migration(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )
            second = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        self.assertEqual(first.uuid, second.uuid)
        self.assertEqual(AppMigration.objects.count(), 1)
        self.assertEqual(self.mock_publisher.publish_channel_migrated.call_count, 1)

    def test_execute_rejects_active_migration_to_different_project(self):
        other_project = Project.objects.create(
            uuid=uuid.uuid4(), name="Other Destination", created_by=self.user
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        with self.assertRaises(ActiveMigrationConflictError):
            self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=other_project.uuid,
            )

        self.assertEqual(AppMigration.objects.count(), 1)

    def test_execute_rejects_same_project(self):
        with self.assertRaises(SameProjectMigrationError):
            self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_from.uuid,
            )

    def test_execute_raises_app_not_found(self):
        with self.assertRaises(AppNotFoundError):
            self.use_case.execute(
                app_uuid=uuid.uuid4(),
                project_to=self.project_to.uuid,
            )

    def test_execute_raises_channel_not_found(self):
        with self.assertRaises(ChannelNotFoundError):
            self.use_case.execute(
                channel_uuid=uuid.uuid4(),
                project_to=self.project_to.uuid,
            )

    def test_execute_raises_project_not_found(self):
        with self.assertRaises(ProjectNotFoundError):
            self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=uuid.uuid4(),
            )

    def test_execute_rejects_app_without_flow_object_uuid(self):
        app = App.objects.create(
            code="wwc",
            config={},
            project_uuid=self.project_from.uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
            flow_object_uuid=None,
        )
        with self.assertRaises(MissingFlowObjectUuidError):
            self.use_case.execute(
                app_uuid=app.uuid,
                project_to=self.project_to.uuid,
            )

    def test_publish_failure_marks_publish_failed(self):
        self.mock_publisher.publish_channel_migrated.side_effect = RuntimeError(
            "broker"
        )

        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        migration.refresh_from_db()
        self.assertEqual(migration.status, AppMigrationStatus.PUBLISH_FAILED)
        self.assertIsNone(migration.published_at)

    def test_republish_after_publish_failed(self):
        self.mock_publisher.publish_channel_migrated.side_effect = [
            RuntimeError("broker"),
            None,
        ]

        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        migration.refresh_from_db()
        self.assertEqual(migration.status, AppMigrationStatus.PUBLISH_FAILED)

        republished = self.use_case.republish(event_id=migration.uuid)
        self.assertEqual(republished.status, AppMigrationStatus.IN_PROGRESS)
        self.assertIsNotNone(republished.published_at)
        self.assertEqual(self.mock_publisher.publish_channel_migrated.call_count, 2)

    def test_republish_rejects_non_failed_status(self):
        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        with self.assertRaises(AppMigrationRepublishError):
            self.use_case.republish(event_id=migration.uuid)

    @override_settings(APP_MIGRATION_EXPECTED_MODULES=["flows", "insights"])
    def test_register_module_status_recomputes_completed(self):
        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        self.use_case.register_module_status(
            event_id=migration.uuid,
            module="flows",
            status=MODULE_STATUS_SUCCESS,
        )
        migration = self.use_case.register_module_status(
            event_id=migration.uuid,
            module="insights",
            status=MODULE_STATUS_SUCCESS,
        )

        self.assertEqual(migration.status, AppMigrationStatus.COMPLETED)
        self.assertEqual(
            migration.modules_status["flows"]["status"], MODULE_STATUS_SUCCESS
        )
        self.assertEqual(
            migration.modules_status["insights"]["status"], MODULE_STATUS_SUCCESS
        )

    @override_settings(APP_MIGRATION_EXPECTED_MODULES=["flows", "insights"])
    def test_register_module_status_partial_error(self):
        with self.captureOnCommitCallbacks(execute=True):
            migration = self.use_case.execute(
                app_uuid=self.app.uuid,
                project_to=self.project_to.uuid,
            )

        self.use_case.register_module_status(
            event_id=migration.uuid,
            module="flows",
            status=MODULE_STATUS_SUCCESS,
        )
        migration = self.use_case.register_module_status(
            event_id=migration.uuid,
            module="insights",
            status=MODULE_STATUS_ERROR,
            error="timeout",
        )

        self.assertEqual(migration.status, AppMigrationStatus.PARTIAL_ERROR)
        self.assertEqual(migration.modules_status["insights"]["error"], "timeout")

    def test_register_module_status_not_found(self):
        with self.assertRaises(AppMigrationNotFoundError):
            self.use_case.register_module_status(
                event_id=uuid.uuid4(),
                module="flows",
                status=MODULE_STATUS_SUCCESS,
            )
