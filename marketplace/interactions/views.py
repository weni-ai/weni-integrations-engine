from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from marketplace.interactions.models import Comment
from marketplace.interactions.serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):

    queryset = Comment.objects
    serializer_class = CommentSerializer

    def create(self, request, *args, **kwargs):
        data = dict()

        if request.data:
            data = dict(request.data)

        data["app_code"] = kwargs.get("app_code")

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        app_code = self.kwargs.get("app_code")
        return super().get_queryset().filter(app_code=app_code)
