from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppDemoSerializer(AppTypeBaseSerializer):
    redirect_url = serializers.SerializerMethodField()

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
            "redirect_url",
        )
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        validated_data["platform"] = self.type_class.platform
        return super().create(validated_data)

    def get_redirect_url(self, instance) -> str:
        return instance.config.get("redirect_url")


class GetOrCreateWppDemoSerializer(serializers.Serializer):
    project_uuid = serializers.UUIDField()


class ReadWppDemoSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    flow_object_uuid = serializers.UUIDField()
    project_uuid = serializers.UUIDField()
    config = serializers.SerializerMethodField()

    def get_config(self, instance) -> str:
        return instance.config
