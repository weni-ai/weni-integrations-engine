from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class TelegramSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = (
            "code",
            "uuid",
            "project_uuid",
            "platform",
            "config",
            "created_by",
            "created_on",
            "modified_by",
        )
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        validated_data["platform"] = self.type_class.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class TelegramConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
