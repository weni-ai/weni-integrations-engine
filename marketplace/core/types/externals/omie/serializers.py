from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App
from marketplace.connect.client import ConnectProjectClient


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
        from .type import OmieType

        validated_data["platform"] = OmieType.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    app_key = serializers.CharField()
    app_secret = serializers.CharField()

    def validate(self, attrs: dict):
        app = self.parent.instance

        attrs["channelUuid"] = app.config.get("channelUuid", None)

        if attrs["channelUuid"] is None:
            response = self._create_channel(attrs, app)
            channel = response.json()

            attrs["channelUuid"] = channel.get("uuid")
            attrs["title"] = channel.get("name")

        return super().validate(attrs)

    def _create_channel(self, attrs: dict, app: App) -> str:
        user = self.context.get("request").user
        client = ConnectProjectClient()
        return client.create_external_service(
            user.email, app.project_uuid, attrs, app.channeltype_code
        )


class OmieConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
