from marketplace.core.types import views
from .serializers import WhatsAppDemoSerializer
from marketplace.connect.client import ConnectProjectClient, WPPRouterChannelClient

from rest_framework.response import Response
from rest_framework import status


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

        channel_client = WPPRouterChannelClient()
        channel_token = channel_client.get_channel_token(result.get("uuid"), result.get("name"))

        instance.config["routerToken"] = channel_token
        instance.config["redirect_url"] = f"https://wa.me/{type_class.NUMBER}?text={channel_token}"
        instance.modified_by = user
        instance.save()

    def update(self, request, *args, **kwargs):
        """ saves the sent flows_starts inside the config and sends it to the router """
        instance = self.get_object()
        flows_starts = request.data.get("flows_starts")
        if not flows_starts:
            return Response({'message': f'the flows_starts not found in request: {request.data}'},
                            status=status.HTTP_404_NOT_FOUND)

        instance.config["flows_starts"] = flows_starts
        instance.modified_by = self.request.user
        instance.save(update_fields=['config','modified_by'])

        channel_client = WPPRouterChannelClient()
        channel_client.set_flows_starts(flows_starts, instance.flow_object_uuid.hex)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status.HTTP_201_CREATED)
