"""  this view manages all available channels configuring them in a generic way """

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework import viewsets

from .serializers import GenericChannelSerializer, GenericConfigureSerializer

from marketplace.core.types import views
from marketplace.connect.client import ConnectProjectClient
from marketplace.applications.models import AppTypeAsset
from marketplace.applications.serializers import AppTypeSerializer
from marketplace.core import types

from . import type as type_


class GenericChannelViewSet(views.BaseAppTypeViewSet):
    """ Generic channel create and listing """
    serializer_class = GenericChannelSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.GenericType.code)

    def perform_create(self, serializer):
        channel_code = self.request.data.get("channel_code", None)
        channel_name = None
        channel_claim_blurb = None

        if channel_code:
            channel_code = channel_code.strip()

        if not channel_code:
            raise serializers.ValidationError('Code not be empty.')

        client = ConnectProjectClient()
        response = client.detail_channel_type(channel_code=channel_code)

        if response.status_code == 200:
            response = response.json()
            if response.get("attributes"):
                if response.get("attributes").get("claim_blurb"):
                    channel_claim_blurb = str(response.get("attributes").get("claim_blurb"))

                if response.get("attributes").get("name"):
                    channel_name = response.get("attributes").get("name")

        instance = serializer.save(code="generic")
        instance.config["channel_code"] = channel_code
        instance.config["channel_name"] = channel_name
        instance.config["channel_icon_url"] = search_icon(channel_code)
        instance.config["channel_claim_blurb"] = channel_claim_blurb
        instance.modified_by = self.request.user
        instance.save()

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, uuid=None):
        """ Add the generic channel in weni-flows """
        self.serializer_class = GenericConfigureSerializer
        data = request.data
        serializer = self.get_serializer(self.get_object(), data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class DetailChannelType(viewsets.ViewSet):
    """ Search the details of a channel

    Args:
        code_channel

    Returns:
        attributes:{},
        form:{}
    """
    lookup_field = "code_channel"

    def retrieve(self, request, code_channel=None):
        client = ConnectProjectClient()
        response = client.detail_channel_type(channel_code=code_channel)
        if response.status_code == 200:
            return Response(response.json(),status=response.status_code)

        return Response({'message': 'There was an error in the request'}, status=response.status_code)


class GetIcons(viewsets.ViewSet):
    """ Return a dictionary  with the channel_code as key and its value is the url of the icon

        Returns:
        {
            'tg': "url.com",
            'exemple': "url2.com"
        }
    """
    def list(self, request):
        client = ConnectProjectClient()
        response = client.list_availables_channels()
        if response.status_code == 200:
            response = response.json()
            channels_icons = {}
            for channel in response.get('channel_types').keys():
                channels_icons[channel] = search_icon(channel)

            return Response(channels_icons)

        return Response({'message': 'There was an error in the request'}, status=response.status_code)


class MyGenericApps(viewsets.ViewSet):
    serializer_class = AppTypeSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = {"request": self.request}
        return self.serializer_class(*args, **kwargs)

    def list(self, request):
        category = request.query_params.get("category", None)
        apptypes = types.APPTYPES

        if category is not None:
            apptypes = apptypes.filter(
                lambda apptype: apptype.get_category_display() == request.query_params.get("category")
            )

        # TODO: remove this filter, it is only while whatsapp is in beta
        apptypes = apptypes.filter(lambda apptype: apptype.code != "wpp")

        serializer = self.get_serializer(apptypes.values(), many=True)

        return Response(serializer.data)


def search_icon(code):
    """ Search icon url from a channel_code

        Args:
            Receive: channel_code

        Return:
            "exemple.url.com"
    """
    apptype_asset = AppTypeAsset.objects.filter(code=code.lower())
    if apptype_asset.exists():
        apptype_asset = apptype_asset.first()
        icon_url = apptype_asset.attachment.url
    else:
        apptype_asset = AppTypeAsset.objects.filter(code='generic')
        if apptype_asset.exists():
            apptype_asset = apptype_asset.first()
            icon_url = apptype_asset.attachment.url
        else:
            icon_url = None

    return icon_url
