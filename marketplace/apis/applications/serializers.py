from rest_framework import serializers


class AppTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    summary = serializers.CharField()
    category = serializers.ChoiceField()
    icon = serializers.SerializerMethodField()

    # rating (LATER)

    comments_count = serializers.SerializerMethodField()
    featured = serializers.SerializerMethodField()

    # assets (LATER)

    def get_assets(self, obj):
        ...

    def get_icon(self, obj):
        ...

    def get_comments_count(self, obj):
        ...

    def get_featured(self, obj):
        ...
