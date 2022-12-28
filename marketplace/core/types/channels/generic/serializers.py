from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.connect.client import ConnectProjectClient

from rest_framework.response import Response

class GenericChannelSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import GenericType

        validated_data["platform"] = GenericType.platform
        return super().create(validated_data)


class GenericConfigSerializer(serializers.Serializer):

    def validate(self, attrs: dict):
        request = self.context.get("request")
        app = self.parent.instance
        app_data = app.config
        data = request.data.get("config")
        for field in data.items():
            attrs[field[0]] = field[1]

        for value in app_data.items():
            attrs[value[0]] = value[1]

        attrs["channelUuid"] = app.config.get("channelUuid", None)
        if attrs["channelUuid"] is None:
            channel = self._create_channel(data, app)
            if channel.status_code != 200:
                raise serializers.ValidationError(f'{channel.reason} - {channel.status_code}')

            channel = channel.json()
            attrs["channelUuid"] = channel.get("uuid")
            attrs["title"] = channel.get("name")

        return super().validate(attrs)

    def _create_channel(self, attrs: dict, app: App) -> str:
        request = self.context.get("request")
        user = request.user
        channeltype_code = app.config.get("channel_code")
        client = ConnectProjectClient()
        response =  client.create_channel(
            user.email, app.project_uuid, attrs, channeltype_code.upper()
        )
        return response


class GenericConfigureSerializer(AppTypeBaseSerializer):
    config = GenericConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
