from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class VtexSerializer(serializers.Serializer):
    domain = serializers.CharField(required=True)
    app_key = serializers.CharField(required=True)
    app_token = serializers.CharField(required=True)
    wpp_cloud_uuid = serializers.UUIDField(required=True)
    uuid = serializers.UUIDField(required=True)
    project_uuid = serializers.UUIDField(required=True)
    store_domain = serializers.CharField(required=True)

    def validate_wpp_cloud_uuid(self, value):
        """
        Check that the wpp_cloud_uuid corresponds to an existing App with code 'wpp-cloud'.
        """
        try:
            App.objects.get(uuid=value, code="wpp-cloud")
        except App.DoesNotExist:
            raise ValidationError(
                "The wpp_cloud_uuid does not correspond to a valid 'wpp-cloud' App."
            )
        return str(value)


class VtexAppSerializer(AppTypeBaseSerializer):
    config = serializers.SerializerMethodField()

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

    def get_config(self, obj):
        config = obj.config.copy()
        api_credentials = config.get("api_credentials", {})
        if api_credentials:
            api_credentials["app_key"] = "***"
            api_credentials["app_token"] = "***"

        return config


class VtexSyncSellerSerializer(serializers.Serializer):
    sellers = serializers.ListField(required=False)
    sync_all_sellers = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        """
        Validate that either sellers list or sync_all_sellers is provided.
        """
        if not data.get("sellers") and not data.get("sync_all_sellers"):
            raise serializers.ValidationError(
                "Either 'sellers' list or 'sync_all_sellers' must be provided."
            )

        if data.get("sellers") and data.get("sync_all_sellers"):
            raise serializers.ValidationError(
                "Cannot provide both 'sellers' list and 'sync_all_sellers' at the same time."
            )

        return data


class VtexAdsSerializer(serializers.Serializer):
    vtex_ads = serializers.BooleanField(required=True)


class FirstProductInsertSerializer(serializers.Serializer):
    catalog_id = serializers.CharField(
        required=True,
        help_text="The catalog identifier to be linked with the VTEX app.",
    )


class SyncOnDemandSerializer(serializers.Serializer):
    id_sku = serializers.CharField(source="IdSku", required=True)
    seller_an = serializers.CharField(source="An", required=False)
    seller_chain = serializers.CharField(source="SellerChain", required=False)
