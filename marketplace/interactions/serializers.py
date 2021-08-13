from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.interactions.models import Comment


class CommentSerializer(AppTypeBaseSerializer):
    class Meta:
        model = Comment
        fields = ["app_code", "uuid", "content", "created_by", "created_on", "modified_by", "edited", "owned"]
        read_only_fields = ("app_code", "uuid", "created_on", "edited")

    owned = serializers.SerializerMethodField()

    def get_owned(self, obj) -> bool:
        request = self.context["request"]
        if request:
            return obj.created_by == request.user

        return False
