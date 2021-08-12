from marketplace.interactions.models import Rating
from rest_framework import serializers
from marketplace.core.types.base import AppType


class ColorSerializer(serializers.Serializer):
    red = serializers.IntegerField()
    green = serializers.IntegerField()
    blue = serializers.IntegerField()
    alpha = serializers.FloatField()


class AppTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    summary = serializers.CharField()
    category = serializers.ChoiceField(choices=AppType.CATEGORY_CHOICES, source="get_category_display")
    icon = serializers.URLField(source="get_icon_url")
    bg_color = ColorSerializer()
    rating = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    assets = serializers.SerializerMethodField()

    def get_assets(self, obj):
        return [
            {
                "type": asset.get_asset_type_display(),
                "url": asset.attachment.url,
                "description": asset.description,
            }
            for asset in obj.assets
        ]

    def get_rating(self, obj) -> dict:
        rating = dict(average=obj.get_ratings_average(), mine=None)

        user = self.context["request"].user
        try:
            rating_instance = user.created_ratings.get(app_code=obj.code)
            rating["mine"] = rating_instance.rate
        except Rating.DoesNotExist:
            pass

        return rating

    def get_comments_count(self, obj) -> int:
        return obj.comments.count()
