from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import WeniWebChatSerializer, WeniWebChatConfigureSerializer
from marketplace.core.types.views import BaseAppTypeViewSet


class WeniWebChatViewSet(BaseAppTypeViewSet):
    serializer_class = WeniWebChatSerializer

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        self.serializer_class = WeniWebChatConfigureSerializer
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)
