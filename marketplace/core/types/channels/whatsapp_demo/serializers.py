from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.connect.client import ConnectProjectClient


class WhatsAppDemoSerializer(AppTypeBaseSerializer):

    redirect_url = serializers.SerializerMethodField()
    flows_starts = serializers.SerializerMethodField()

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
            "flows_starts",
        )
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import WhatsAppDemoType

        validated_data["platform"] = WhatsAppDemoType.platform
        return super().create(validated_data)

    def get_redirect_url(self, instance) -> str:
        return instance.config.get("redirect_url")

    def get_flows_starts(self, instance):
        """
        Returns entity-related flows
        """
        client = ConnectProjectClient()
        flows_starts = client.list_flows(instance.project_uuid.hex)
        return flows_starts
