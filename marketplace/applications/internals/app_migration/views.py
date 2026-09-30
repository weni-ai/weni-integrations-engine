from rest_framework import status, views
from rest_framework.response import Response

from marketplace.applications.internals.app_migration.serializers import (
    AppMigrationCreateSerializer,
    AppMigrationModuleStatusSerializer,
    AppMigrationSerializer,
)
from marketplace.applications.models import AppMigration
from marketplace.applications.usecases.app_migration.exceptions import (
    AppMigrationNotFoundError,
)
from marketplace.applications.usecases.app_migration.migrate_app import (
    MigrateAppUseCase,
)
from marketplace.internal.permissions import CanCommunicateInternally


class AppMigrationCreateView(views.APIView):
    """POST /internals/app-migrations — trigger an app migration."""

    permission_classes = [CanCommunicateInternally]

    def post(self, request, **kwargs):
        serializer = AppMigrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requested_by = getattr(request.user, "email", None)
        migration = MigrateAppUseCase().execute(
            app_uuid=serializer.validated_data.get("app_uuid"),
            channel_uuid=serializer.validated_data.get("channel_uuid"),
            project_to=serializer.validated_data["project_to"],
            requested_by=requested_by,
        )
        return Response(
            AppMigrationSerializer(migration).data,
            status=status.HTTP_200_OK,
        )


class AppMigrationDetailView(views.APIView):
    """GET /internals/app-migrations/<event_id>"""

    permission_classes = [CanCommunicateInternally]

    def get(self, request, event_id, **kwargs):
        try:
            migration = AppMigration.objects.get(uuid=event_id)
        except AppMigration.DoesNotExist:
            raise AppMigrationNotFoundError()

        return Response(
            AppMigrationSerializer(migration).data,
            status=status.HTTP_200_OK,
        )


class AppMigrationStatusView(views.APIView):
    """POST /internals/app-migrations/<event_id>/status"""

    permission_classes = [CanCommunicateInternally]

    def post(self, request, event_id, **kwargs):
        serializer = AppMigrationModuleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        migration = MigrateAppUseCase().register_module_status(
            event_id=event_id,
            module=serializer.validated_data["module"],
            status=serializer.validated_data["status"],
            error=serializer.validated_data.get("error"),
        )
        return Response(
            AppMigrationSerializer(migration).data,
            status=status.HTTP_200_OK,
        )


class AppMigrationRepublishView(views.APIView):
    """POST /internals/app-migrations/<event_id>/republish"""

    permission_classes = [CanCommunicateInternally]

    def post(self, request, event_id, **kwargs):
        migration = MigrateAppUseCase().republish(event_id=event_id)
        return Response(
            AppMigrationSerializer(migration).data,
            status=status.HTTP_200_OK,
        )
