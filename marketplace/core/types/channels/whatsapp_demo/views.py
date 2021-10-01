from rest_framework.decorators import action

from marketplace.core.types.views import BaseAppTypeViewSet
from .serializers import WhatsAppDemoSerializer


class WhatsAppDemoViewSet(BaseAppTypeViewSet):

    serializer_class = WhatsAppDemoSerializer

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        ...
