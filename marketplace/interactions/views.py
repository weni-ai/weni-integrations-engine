from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated

from .models import Comment
from .serializers import CommentSerializer, RatingSerializer, FeedbackSerializer
from .permissions import CommentManagePermission


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects
    serializer_class = CommentSerializer
    lookup_field = "uuid"
    permission_classes = (CommentManagePermission,)

    def get_queryset(self):
        return super().get_queryset().filter(code=self.kwargs["apptype_pk"])

    def perform_create(self, serializer):
        serializer.save(code=self.kwargs["apptype_pk"])


class RatingViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = RatingSerializer

    def perform_create(self, serializer):
        serializer.save(code=self.kwargs["apptype_pk"])


class FeedbackViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
