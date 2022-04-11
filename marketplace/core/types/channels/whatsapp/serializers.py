from pytz import timezone
from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppConfigSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)

    # TODO: this is a mock, made just to return fake data. Adjust later.
    waba = serializers.SerializerMethodField()

    def get_waba(self, obj: App) -> dict:
        return dict(
            id="372347354000000",
            name="Weni Tecnologia - FB 881768118500000",
            message_behalf_name="Weni Tecnologia",
            timezone="America/Sao_Paulo",
            namespace="2ee3daabc_0f8e_0000_ae7c_175b808f916",
        )

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
