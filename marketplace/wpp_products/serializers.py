from rest_framework import serializers

from marketplace.wpp_products.models import Catalog, Product, ProductFeed


class CatalogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    facebook_catalog_id = serializers.CharField(read_only=True)

    class Meta:
        model = Catalog
        fields = ("uuid", "name", "facebook_catalog_id")


class ProductFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeed
        fields = ["uuid", "facebook_feed_id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ("modified_on", "modified_by", "created_by", "catalog", "feed", "id")
