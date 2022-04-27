from marketplace.applications.models import App, AppTypeAsset
from marketplace.interactions.models import Rating
from rest_framework import serializers
from marketplace.core.types.base import AppType


class AppTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    summary = serializers.CharField()
    category = serializers.ChoiceField(choices=AppType.CATEGORY_CHOICES, source="get_category_display")
    icon = serializers.URLField(source="get_icon_url")
    bg_color = serializers.CharField()
    config_design = serializers.CharField()
    rating = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    integrations_count = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()
    can_add = serializers.SerializerMethodField()

    assets = serializers.SerializerMethodField()

    def get_assets(self, obj):
        return [
            {
                "type": asset.asset_type,
                "url": asset.url if asset.asset_type == AppTypeAsset.ASSET_TYPE_LINK else asset.attachment.url,
                "description": asset.description,
            }
            for asset in obj.assets
        ]

    def get_rating(self, obj) -> dict:
        rating = dict(average=obj.get_ratings_average(), mine=None)

        user = self.context["request"].user
        try:
            rating_instance = user.created_ratings.get(code=obj.code)
            rating["mine"] = rating_instance.rate
        except Rating.DoesNotExist:
            pass

        return rating

    def get_comments_count(self, obj) -> int:
        return obj.comments.count()

    def get_integrations_count(self, obj) -> int:
        return obj.apps.count()

    def get_metrics(self, obj):
        # TODO: Get real metric from AppType
        return 58602143

    def get_can_add(self, obj):
        project_uuid = self.context["request"].headers.get("Project-Uuid")
        return obj.can_add(project_uuid)


class MyAppSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj) -> str:  # TODO: Get `icon` from own App object
        return obj.apptype.get_icon_url()

    class Meta:
        model = App
        fields = ("uuid", "code", "name", "description", "summary", "icon", "config")
