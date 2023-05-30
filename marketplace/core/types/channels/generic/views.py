"""  this view manages all available channels configuring them in a generic way """
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework import viewsets

from .serializers import GenericChannelSerializer, GenericConfigureSerializer

from marketplace.core.types import views
from marketplace.flows.client import FlowsClient

from marketplace.applications.models import AppTypeAsset

from . import type as type_

from django.conf import settings

IMPORTANCE_CHANNELS_ORDER = settings.IMPORTANCE_CHANNELS_ORDER


class GenericChannelViewSet(views.BaseAppTypeViewSet):
    """Generic channel create and listing"""

    serializer_class = GenericChannelSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.GenericChannelAppType.code)

    def perform_create(self, serializer):
        channel_code = self.request.data.get("channel_code", None)
        channel_name = None
        channel_claim_blurb = None

        if channel_code:
            channel_code = channel_code.strip()
        else:
            raise serializers.ValidationError("Code not be empty.")

        client = FlowsClient()
        response = client.list_channel_types(channel_code=channel_code)

        if response.status_code == 200:
            response = response.json()
            if response.get("attributes"):
                if response.get("attributes").get("claim_blurb"):
                    channel_claim_blurb = str(
                        response.get("attributes").get("claim_blurb")
                    )

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
        """Add the generic channel in weni-flows"""
        self.serializer_class = GenericConfigureSerializer
        data = request.data
        serializer = self.get_serializer(self.get_object(), data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class DetailChannelType(viewsets.ViewSet):
    """Search the details of a channel

    Args:
        code_channel

    Returns:
        attributes:{},
        form:{}
    """

    lookup_field = "code_channel"

    def retrieve(self, request, code_channel=None):
        client = FlowsClient()
        response = client.list_channel_types(channel_code=code_channel)
        if response.status_code == 200:
            return Response(response.json(), status=response.status_code)

        return Response(
            {"message": "There was an error in the request"},
            status=response.status_code,
        )


class GetIcons(viewsets.ViewSet):
    """Return a dictionary  with the channel_code as key and its value is the url of the icon

    Returns:
    {
        'tg': "url.com",
        'exemple': "url2.com"
    }
    """

    def list(self, request):
        client = FlowsClient()
        response = client.list_channel_types(channel_code=None)
        if response.status_code == 200:
            response = response.json()
            channels_icons = {}
            for channel in response.get("channel_types").keys():
                channels_icons[channel] = search_icon(channel)

            return Response(channels_icons)

        return Response(
            {"message": "There was an error in the request"},
            status=response.status_code,
        )


class GenericAppTypes(viewsets.ViewSet):
    """Returns a dictionary of channel codes from the flows

    Returns:
    {
    "D3": {
        "attributes": {...}
    },
    "ZVW": {
        "attributes": {...}
    }...
    """

    def list(self, request):
        client = FlowsClient()
        response = client.list_channel_types(channel_code=None)
        channel_types = sort_channel_types(response.json().get("channel_types"))
        return Response(channel_types, status=response.status_code)


def search_icon(code):
    """Search icon url from a channel_code

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
        apptype_asset = AppTypeAsset.objects.filter(code="generic")
        if apptype_asset.exists():
            apptype_asset = apptype_asset.first()
            icon_url = apptype_asset.attachment.url
        else:
            icon_url = None

    return icon_url


def sort_channel_types(channel_types):
    """Receives a dictionary of channels and returns
    them ordered by importance and alphabetical order of the channel code"""

    importance_order = IMPORTANCE_CHANNELS_ORDER
    keys_sorted = sorted(set(importance_order + list(channel_types.keys())))
    items = [(key, channel_types[key]) for key in keys_sorted]

    # Sort the list of tuples in order of importance and by name within the attributes
    items_sorted = sorted(
        items,
        key=lambda x: (
            importance_order.index(x[0]) if x[0] in importance_order else float("inf"),
            x[0],
        ),
    )
    channel_types_sorted = {key: value for key, value in items_sorted}
    return channel_types_sorted
