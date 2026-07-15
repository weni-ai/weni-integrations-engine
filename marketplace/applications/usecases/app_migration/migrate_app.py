from typing import Optional, Union
from uuid import UUID

import pendulum
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from marketplace.applications.models import App, AppMigration, AppMigrationStatus
from marketplace.applications.usecases.app_migration.eda_publisher import (
    AppMigrationEDAPublisher,
)
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
from marketplace.projects.models import Project

MODULE_STATUS_SUCCESS = "success"
MODULE_STATUS_ERROR = "error"


class MigrateAppUseCase:
    """Reusable use case for migrating an App between projects.

    Integrations is the source of truth for App.project_uuid: reassigns the
    project, persists an AppMigration record, then publishes
    integrations.channel.migrated on commit.
    """

    ACTIVE_STATUSES = [
        AppMigrationStatus.PENDING,
        AppMigrationStatus.PUBLISH_FAILED,
        AppMigrationStatus.IN_PROGRESS,
        AppMigrationStatus.PARTIAL_ERROR,
    ]

    def __init__(self, publisher: Optional[AppMigrationEDAPublisher] = None):
        self.publisher = publisher or AppMigrationEDAPublisher()

    def execute(
        self,
        project_to: Union[UUID, str],
        app_uuid: Optional[Union[UUID, str]] = None,
        channel_uuid: Optional[Union[UUID, str]] = None,
        requested_by: Optional[str] = None,
    ) -> AppMigration:
        has_app = app_uuid is not None
        has_channel = channel_uuid is not None
        if has_app == has_channel:
            raise AmbiguousLookupError()

        project_to_uuid = (
            project_to if isinstance(project_to, UUID) else UUID(str(project_to))
        )

        if not Project.objects.filter(uuid=project_to_uuid).exists():
            raise ProjectNotFoundError()

        with transaction.atomic():
            app = self._resolve_app_for_update(
                app_uuid=app_uuid, channel_uuid=channel_uuid
            )

            existing = (
                AppMigration.objects.filter(app=app, status__in=self.ACTIVE_STATUSES)
                .order_by("-created_at")
                .first()
            )
            if existing:
                if existing.project_to != project_to_uuid:
                    raise ActiveMigrationConflictError()
                return existing

            if app.project_uuid == project_to_uuid:
                raise SameProjectMigrationError()

            if app.flow_object_uuid is None:
                raise MissingFlowObjectUuidError()

            project_from = app.project_uuid
            app.project_uuid = project_to_uuid
            app.save(update_fields=["project_uuid", "modified_on"])

            migration = AppMigration.objects.create(
                app=app,
                flow_object_uuid=app.flow_object_uuid,
                project_from=project_from,
                project_to=project_to_uuid,
                status=AppMigrationStatus.PENDING,
                modules_status={},
                requested_by=requested_by,
            )
            migration_uuid = migration.uuid

            transaction.on_commit(
                lambda: self._publish_migration(migration_uuid=migration_uuid)
            )

        return AppMigration.objects.get(uuid=migration_uuid)

    def register_module_status(
        self,
        event_id: Union[UUID, str],
        module: str,
        status: str,
        error: Optional[str] = None,
    ) -> AppMigration:
        with transaction.atomic():
            try:
                migration = AppMigration.objects.select_for_update().get(uuid=event_id)
            except AppMigration.DoesNotExist:
                raise AppMigrationNotFoundError()

            modules_status = dict(migration.modules_status or {})
            modules_status[module] = {
                "status": status,
                "error": error,
                "reported_at": pendulum.now("UTC").to_iso8601_string(),
            }
            migration.modules_status = modules_status
            migration.status = self._recompute_status(modules_status)
            migration.save(update_fields=["modules_status", "status", "updated_at"])
            return migration

    def republish(self, event_id: Union[UUID, str]) -> AppMigration:
        try:
            migration = AppMigration.objects.get(uuid=event_id)
        except AppMigration.DoesNotExist:
            raise AppMigrationNotFoundError()

        if migration.status != AppMigrationStatus.PUBLISH_FAILED:
            raise AppMigrationRepublishError()

        self._publish_migration(migration_uuid=migration.uuid)
        return AppMigration.objects.get(uuid=migration.uuid)

    def _resolve_app_for_update(
        self,
        app_uuid: Optional[Union[UUID, str]],
        channel_uuid: Optional[Union[UUID, str]],
    ) -> App:
        queryset = App.objects.select_for_update()
        if app_uuid is not None:
            try:
                return queryset.get(uuid=app_uuid)
            except App.DoesNotExist:
                raise AppNotFoundError()

        try:
            return queryset.get(flow_object_uuid=channel_uuid)
        except App.DoesNotExist:
            raise ChannelNotFoundError()

    def _publish_migration(self, migration_uuid: UUID) -> None:
        try:
            migration = AppMigration.objects.select_related("app").get(
                uuid=migration_uuid
            )
        except AppMigration.DoesNotExist:
            return

        try:
            self.publisher.publish_channel_migrated(
                event_id=migration.uuid,
                channel_uuid=migration.flow_object_uuid,
                app_uuid=migration.app.uuid,
                project_from=migration.project_from,
                project_to=migration.project_to,
            )
        except Exception:
            migration.status = AppMigrationStatus.PUBLISH_FAILED
            migration.save(update_fields=["status", "updated_at"])
            return

        migration.status = AppMigrationStatus.IN_PROGRESS
        migration.published_at = timezone.now()
        migration.save(update_fields=["status", "published_at", "updated_at"])

    def _recompute_status(self, modules_status: dict) -> str:
        expected = list(settings.APP_MIGRATION_EXPECTED_MODULES or [])
        if not expected:
            has_error = any(
                entry.get("status") == MODULE_STATUS_ERROR
                for entry in modules_status.values()
            )
            return (
                AppMigrationStatus.PARTIAL_ERROR
                if has_error
                else AppMigrationStatus.IN_PROGRESS
            )

        statuses = [
            (modules_status.get(module) or {}).get("status") for module in expected
        ]

        if any(status == MODULE_STATUS_ERROR for status in statuses):
            return AppMigrationStatus.PARTIAL_ERROR

        if all(status == MODULE_STATUS_SUCCESS for status in statuses):
            return AppMigrationStatus.COMPLETED

        return AppMigrationStatus.IN_PROGRESS
