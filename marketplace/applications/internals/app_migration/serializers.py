from rest_framework import serializers

from marketplace.applications.models import AppMigration
from marketplace.applications.usecases.app_migration.exceptions import (
    AmbiguousLookupError,
)
from marketplace.applications.usecases.app_migration.migrate_app import (
    MODULE_STATUS_ERROR,
    MODULE_STATUS_SUCCESS,
)


class AppMigrationCreateSerializer(serializers.Serializer):
    app_uuid = serializers.UUIDField(required=False)
    channel_uuid = serializers.UUIDField(required=False)
    project_to = serializers.UUIDField()

    def validate(self, attrs):
        has_app = "app_uuid" in attrs and attrs["app_uuid"] is not None
        has_channel = "channel_uuid" in attrs and attrs["channel_uuid"] is not None
        if has_app == has_channel:
            raise AmbiguousLookupError()
        return attrs


class AppMigrationModuleStatusSerializer(serializers.Serializer):
    module = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(
        choices=[MODULE_STATUS_SUCCESS, MODULE_STATUS_ERROR]
    )
    error = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )


class AppMigrationSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField(source="uuid", read_only=True)
    app_uuid = serializers.UUIDField(source="app.uuid", read_only=True)
    channel_uuid = serializers.UUIDField(source="flow_object_uuid", read_only=True)

    class Meta:
        model = AppMigration
        fields = [
            "event_id",
            "app_uuid",
            "channel_uuid",
            "project_from",
            "project_to",
            "status",
            "modules_status",
            "requested_by",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
