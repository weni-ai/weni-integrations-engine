from rest_framework import viewsets
from rest_framework import mixins

from marketplace.interactions.models import Comment, Rating
from marketplace.interactions.serializers import CommentSerializer, RatingSerializer


class CommentViewSet(viewsets.ModelViewSet):

    queryset = Comment.objects
    serializer_class = CommentSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return super().get_queryset().filter(app_code=self.kwargs["apptype_pk"])

    def perform_create(self, serializer):
        serializer.save(app_code=self.kwargs["apptype_pk"])


class RatingViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):

    serializer_class = RatingSerializer

    def perform_create(self, serializer):
        serializer.save(app_code=self.kwargs["apptype_pk"])
