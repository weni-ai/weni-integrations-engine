from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App
from marketplace.flows.client import FlowsClient


class GenericExternalSerializer(AppTypeBaseSerializer):
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


class GenericExternalConfigSerializer(serializers.Serializer):
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
            channel = channel.json()
            attrs["channelUuid"] = channel.get("uuid")
            attrs["title"] = channel.get("name")

        return super().validate(attrs)

    def _create_channel(self, attrs: dict, app: App) -> str:
        request = self.context.get("request")
        user = request.user
        external_code = app.config.get("external_code")
        response = app.apptype.create(
            FlowsClient(), user.email, str(app.project_uuid), attrs, external_code
        )
        return response


class GenericConfigureSerializer(AppTypeBaseSerializer):
    config = GenericExternalConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
