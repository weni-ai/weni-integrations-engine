from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WeniWebChatSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import WeniWebChatType

        validated_data["platform"] = WeniWebChatType.platform
        return super().create(validated_data)
