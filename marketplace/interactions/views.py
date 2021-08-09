from rest_framework import viewsets

from marketplace.interactions.models import Comment
from marketplace.interactions.serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):

    queryset = Comment.objects
    serializer_class = CommentSerializer

    def get_queryset(self):
        return super().get_queryset().filter(app_code=self.kwargs["apptypes_pk"])

    def perform_create(self, serializer):
        serializer.save(app_code=self.kwargs["apptypes_pk"])
