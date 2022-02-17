from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppSerializer(AppTypeBaseSerializer):
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

        # TODO: Validate fields
