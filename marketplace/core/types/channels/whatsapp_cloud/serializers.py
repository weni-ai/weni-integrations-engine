from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


# TODO: Remove unnecessary serializers
class WhatsAppCloudSerializer(AppTypeBaseSerializer):
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


class WhatsAppCloudConfigureSerializer(serializers.Serializer):
    waba_id = serializers.CharField(required=True)
    phone_number_id = serializers.CharField(required=True)
    auth_code = serializers.CharField(required=True)


class WhatsAppCloudChannelsQueryParamsSerializer(serializers.Serializer):
    project_uuid = serializers.UUIDField(required=True)


class WhatsAppCloudChannelSerializer(serializers.Serializer):
    """Represents a WhatsApp Cloud channel (App) for the channel-selection
    screen consumed by external services such as `retail`.

    `channel_uuid` is the App's `flow_object_uuid` (the identifier `retail`
    uses as the channel) and `app_uuid` is the App's own uuid.

    Phone number and display name may live either in the flat keys written at
    creation time (`wa_number`, `wa_phone_number_id`, `wa_waba_id`,
    `wa_verified_name`) or in the nested `phone_number` / `waba` objects written
    later by the sync use cases. Both shapes are normalized here so the contract
    is stable regardless of how far the channel has progressed through sync.

    The raw `config` is intentionally not exposed: it holds secrets such as
    `wa_user_token` and `wa_pin`.
    """

    def to_representation(self, instance: App) -> dict:
        config = instance.config or {}
        phone_number = config.get("phone_number") or {}
        waba = config.get("waba") or {}

        return {
            "app_uuid": str(instance.uuid),
            "channel_uuid": (
                str(instance.flow_object_uuid) if instance.flow_object_uuid else None
            ),
            "phone_number": (
                phone_number.get("display_phone_number")
                or config.get("wa_number")
                or config.get("title")
            ),
            "phone_number_id": (
                phone_number.get("id") or config.get("wa_phone_number_id")
            ),
            "waba_id": waba.get("id") or config.get("wa_waba_id"),
            "name": (
                phone_number.get("display_name")
                or config.get("wa_verified_name")
                or waba.get("name")
                or config.get("title")
            ),
        }
