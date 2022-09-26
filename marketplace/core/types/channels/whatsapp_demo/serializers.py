from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppDemoSerializer(AppTypeBaseSerializer):

    redirect_url = serializers.SerializerMethodField()
    flows = serializers.SerializerMethodField()

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
            "flows",
        )
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import WhatsAppDemoType

        validated_data["platform"] = WhatsAppDemoType.platform
        return super().create(validated_data)


    def get_redirect_url(self, instance) -> str:
        return instance.config.get("redirect_url")

    def get_flows(self, instance):
        """
        Returns entity-related flows
        """
        flows = None
        flows = [{'flow_name':'flow_disponivel_01', 'flow_uuid':'3a624a22-c825-461c-9bcf-2fdf7c38eb74', 'keyword':"olá"}, 
                 {'flow_name':'flow_disponivel_02', 'flow_uuid':'3a624a22-c825-461c-9bcf-2fdf7c38eb74', 'keyword':"hello"}, 
                 {'flow_name':'flow_disponivel_03', 'flow_uuid':'3a624a22-c825-461c-9bcf-2fdf7c38eb74', 'keyword':"cupom20"}] 
        
        return flows

