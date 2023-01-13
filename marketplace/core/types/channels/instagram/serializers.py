from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App
from marketplace.connect.client import ConnectProjectClient


class InstagramSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import InstagramType

        validated_data["platform"] = InstagramType.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):

    user_access_token = serializers.CharField(required=True)
    page_name = serializers.CharField(required=True)
    page_id = serializers.CharField(required=True)
    fb_user_id = serializers.CharField(required=True)

    def validate(self, attrs: dict):
        app = self.parent.instance

        attrs["channelUuid"] = app.config.get("channelUuid", None)

        if attrs["channelUuid"] is None:
            channel = self._create_channel(attrs, app)
            if channel.status_code != 200:
                reason = channel.text if channel.text else ''
                raise serializers.ValidationError(f'{reason} - {channel.status_code}')
            attrs["channelUuid"] = channel.get("uuid")
            attrs["title"] = channel.get("name")

        return super().validate(attrs)

    def _create_channel(self, attrs: dict, app: App) -> str:
        user = self.context.get("request").user
        client = ConnectProjectClient()

        payload={
            'user_access_token': attrs.get("user_access_token"),
            'fb_user_id': attrs.get("fb_user_id"),
            'page_name': attrs.get("page_name"),
            'page_id': attrs.get("page_id")
        }
        response = client.create_channel(
            user.email, app.project_uuid, payload, app.channeltype_code
        )

        return response


class InstagramConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
