from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App
from marketplace.celery import app as celery_app
from marketplace.connect.client import ConnectProjectClient

class TelegramSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import TelegramType

        validated_data["platform"] = TelegramType.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):

    token = serializers.CharField(required=True)

    def validate(self, attrs: dict):
        app = self.parent.instance

        attrs["channelUuid"] = app.config.get("channelUuid", None)

        if attrs["channelUuid"] is None:
            channel = self._create_channel(attrs, app)
            attrs["channelUuid"] = channel.get("uuid")
            attrs["title"] = channel.get("name")

        return super().validate(attrs)

    def _create_channel(self, attrs: dict, app: App) -> str:
        user = self.context.get("request").user
        client = ConnectProjectClient()
        return client.create_channel(user.email, app.project_uuid, {"auth_token": attrs.get("token")}, app.channeltype_code)


class TelegramConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
