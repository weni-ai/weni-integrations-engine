from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.core.fields import Base64ImageField
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
    waba = WhatsAppConfigWABASerializer(required=False)
    phone_number = WhatsAppConfigPhoneNumberSerializer(required=False)


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


class WhatsAppBusinessProfileSerializer(serializers.Serializer):
    VERTICAl_CHOICES = (
        "Automotive",
        "Beauty, Spa and Salon",
        "Clothing and Apparel",
        "Education",
        "Entertainment",
        "Event Planning and Service",
        "Finance and Banking",
        "Food and Grocery",
        "Public Service",
        "Hotel and Lodging",
        "Medical and Health",
        "Non-profit",
        "Professional Services",
        "Shopping and Retail",
        "Travel and Transportation",
        "Restaurant",
        "Other",
    )

    description = serializers.CharField(required=False)
    vertical = serializers.ChoiceField(choices=VERTICAl_CHOICES, required=False, default="")
    vertical_choices = serializers.SerializerMethodField()

    def get_vertical_choices(self, _instance):
        return self.VERTICAl_CHOICES


class WhatsAppProfileSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=139, required=False)
    business = WhatsAppBusinessProfileSerializer(required=False)
    photo_url = serializers.URLField(read_only=True)
    photo = Base64ImageField(write_only=True, required=False)


class WhatsAppBusinessContactSerializer(serializers.Serializer):
    websites = serializers.ListField(required=False)
    email = serializers.CharField(required=False)
    address = serializers.CharField(required=False)

    def validate_websites(self, websites):
        if len(websites) > 2:
            raise serializers.ValidationError("Each app can only contain 2 websites!")

        return websites
