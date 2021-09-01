from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.interactions.models import Comment, Rating


class CommentSerializer(AppTypeBaseSerializer):
    class Meta:
        model = Comment
        fields = ["code", "uuid", "content", "created_by", "created_on", "modified_by", "edited", "owned"]
        read_only_fields = ("code", "uuid", "created_on", "edited")

    owned = serializers.SerializerMethodField()

    def get_owned(self, obj) -> bool:
        request = self.context["request"]
        if request:
            return obj.created_by == request.user

        return False


class RatingSerializer(AppTypeBaseSerializer):
    class Meta:
        model = Rating
        fields = ["code", "uuid", "rate", "created_by", "modified_by"]
        read_only_fields = ("code", "uuid")

    def create(self, validated_data):
        rate = validated_data.get("rate")

        credentials = {
            "created_by": validated_data.get("created_by"),
            "code": validated_data.get("code"),
            "defaults": {"rate": rate},
        }

        rating, created = Rating.objects.get_or_create(**credentials)

        if not created:
            rating.modified_by = validated_data.get("modified_by")
            rating.rate = rate
            rating.save()

        return rating
