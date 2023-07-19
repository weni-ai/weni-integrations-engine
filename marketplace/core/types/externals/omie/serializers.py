from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class OmieSerializer(AppTypeBaseSerializer):
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
        # TODO: Send the responsibility of this method to the AppTypeBaseSerializer and create an object from the type
        validated_data["platform"] = self.type_class.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    app_key = serializers.CharField()
    app_secret = serializers.CharField()


class OmieConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
