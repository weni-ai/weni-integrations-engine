from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from .timezones import TIMEZONES


class WhatsAppConfigWABASerializer(serializers.Serializer):
    id_ = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    timezone = serializers.SerializerMethodField(required=False)
    namespace = serializers.CharField(required=False, source="message_template_namespace")

    def get_timezone(self, instance):
        timezone_id = instance.get("timezone_id")
        return TIMEZONES.get(timezone_id, {}).get("name")

    def get_fields(self):
        """
        `id` is a reserved word of the language, to avoid conflicts the attribute
        name was given as `id_`. This method renames the field to be more readable in the API
        """
        fields = super().get_fields()
        fields["id"] = fields.pop("id_")
        return fields


class WhatsAppConfigPhoneNumberSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    display_phone_number = serializers.CharField()
    consent_status = serializers.CharField(required=False)
    certificate = serializers.CharField(required=False)


class WhatsAppConfigSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)

    # TODO: this is a mock, made just to return fake data. Adjust later.
    waba = WhatsAppConfigWABASerializer(required=False)
    phone_number = WhatsAppConfigPhoneNumberSerializer(required=False)
    message_day_limit = serializers.SerializerMethodField()
    pin_verification = serializers.SerializerMethodField()
    default_template_language = serializers.SerializerMethodField()

    def get_message_day_limit(self, obj: App) -> int:
        return 10000

    def get_pin_verification(self, obj: App) -> bool:
        return True

    def get_default_template_language(self, obj: App) -> str:
        return "pt_BR"

    class Meta:
        fields = ("title",)


class WhatsAppSerializer(AppTypeBaseSerializer):
    config = WhatsAppConfigSerializer()

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

        # TODO: Validate fields
