from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class TelegramSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import TelegramType

        validated_data["platform"] = TelegramType.platform
        return super().create(validated_data)
