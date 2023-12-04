from rest_framework import serializers

from marketplace.wpp_products.models import Catalog


class CatalogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    facebook_catalog_id = serializers.CharField(read_only=True)
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        fields = ("uuid", "name", "facebook_catalog_id", "category", "is_connected")

    def get_is_connected(self, obj):
        connected_catalog_id = self.context.get("connected_catalog_id")
        return obj.facebook_catalog_id == connected_catalog_id


class ToggleVisibilitySerializer(serializers.Serializer):
    enable = serializers.BooleanField()


class TresholdSerializer(serializers.Serializer):
    treshold = serializers.FloatField()


class CatalogListSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        catalogs = obj

        serialized_data = []
        connected_data = None

        for catalog in catalogs:
            serialized_catalog = CatalogSerializer(catalog, context=self.context).data

            if serialized_catalog["is_connected"]:
                connected_data = serialized_catalog
            else:
                serialized_data.append(serialized_catalog)

        # If a connected catalog is found, insert it at the beginning of the list.
        if connected_data:
            serialized_data.insert(0, connected_data)

        return serialized_data
