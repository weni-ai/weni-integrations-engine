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
        instance = serializer.save(code=self.type_class.code)

        data = dict(
            number=type_class.NUMBER,
            country=type_class.COUNTRY,
            base_url=type_class.BASE_URL,
            username=type_class.USERNAME,
            password=type_class.PASSWORD,
            facebook_namespace=type_class.FACEBOOK_NAMESPACE,
            facebook_template_list_domain="graph.facebook.com",
            facebook_business_id="null",
            facebook_access_token="null",
        )

        client = ConnectProjectClient()
        result = client.create_channel(user.email, str(instance.project_uuid), data, instance.channeltype_code)

        instance.config["title"] = result.get("name")
        instance.config["channelUuid"] = result.get("uuid")

        ch_client = WPPRouterChannelClient()
        ch_result = ch_client.get_channel_token(result.get("uuid"), result.get("name"))

        instance.config["routerToken"] = ch_result
        instance.config["redirect_url"] = f"https://wa.me/{type_class.NUMBER}?text={ch_result}"
        instance.modified_by = user
        instance.save()
