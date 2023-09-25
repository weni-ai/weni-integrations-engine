from rest_framework import serializers

from marketplace.wpp_products.models import Catalog


class CatalogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    facebook_catalog_id = serializers.CharField(read_only=True)
    category = serializers.CharField(required=True)

    class Meta:
        model = Catalog
        fields = ("uuid", "name", "facebook_catalog_id", "category")


class ToggleVisibilitySerializer(serializers.Serializer):
    enable = serializers.BooleanField()
