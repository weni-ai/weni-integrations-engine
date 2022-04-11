from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppConfigSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)

    # TODO: this is a mock, made just to return fake data. Adjust later.
    waba = serializers.SerializerMethodField()
    message_day_limit = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    pin_verification = serializers.SerializerMethodField()
    default_template_language = serializers.SerializerMethodField()
    certificate = serializers.SerializerMethodField()
    consent_status = serializers.SerializerMethodField()

    def get_waba(self, obj: App) -> dict:
        return dict(
            id="372347354000000",
            name="Weni Tecnologia - FB 881768118500000",
            message_behalf_name="Weni Tecnologia",
            timezone="America/Sao_Paulo",
            namespace="2ee3daabc_0f8e_0000_ae7c_175b808f916",
        )

    def get_message_day_limit(self, obj: App) -> int:
        return 10000

    def get_display_name(self, obj: App) -> str:
        return "Weni"

    def get_pin_verification(self, obj: App) -> bool:
        return True

    def get_default_template_language(self, obj: App) -> str:
        return "pt_BR"

    def get_certificate(self, obj: App) -> str:
        return "AbCdEfGhIjKlMnOpQrStUvWxYz"

    def get_consent_status(self, obj: App) -> str:
        return "Approved"

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
