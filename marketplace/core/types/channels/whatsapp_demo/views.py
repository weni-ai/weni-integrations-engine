from marketplace.core.types import views
from .serializers import WhatsAppDemoSerializer
from marketplace.connect.client import ConnectProjectClient, WPPRouterChannelClient


class WhatsAppDemoViewSet(views.BaseAppTypeViewSet):
    serializer_class = WhatsAppDemoSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        user = self.request.user
        type_class = self.type_class
        app = serializer.save(code=self.type_class.code)

        channel_client = ConnectProjectClient()
        channel_token_client = WPPRouterChannelClient()

        type_class.configure_app(app, user, channel_client, channel_token_client)
