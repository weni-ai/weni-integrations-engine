from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from rest_framework import viewsets

from marketplace.flows.client import FlowsClient

from .serializers import GenericExternalSerializer, GenericConfigureSerializer
from marketplace.core.types import views

from django.conf import settings

from marketplace.applications.models import AppTypeAsset


IMPORTANCE_CHANNELS_ORDER = settings.IMPORTANCE_CHANNELS_ORDER


class GenericExternalsViewSet(views.BaseAppTypeViewSet):
    serializer_class = GenericExternalSerializer

    def get_queryset(self):
        # TODO: Send the responsibility of this method to the BaseAppTypeViewSet
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        external_code = self.request.data.get("external_code", None)
        external_name = None
        if external_code:
            external_code = external_code.strip()
        else:
            raise serializers.ValidationError("external_code not be empty.")

        response = self.type_class.list(FlowsClient(), flows_type_code=external_code)
        if response.get("attributes"):
            if response.get("attributes").get("name"):
                external_name = response.get("attributes").get("name")

        instance = serializer.save(code="generic-external")
        instance.config["external_code"] = external_code
        instance.config["name"] = external_name
        instance.config["external_icon_url"] = search_icon(external_code)
        instance.modified_by = self.request.user
        instance.save()

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, uuid=None):
        self.serializer_class = GenericConfigureSerializer
        data = request.data
        serializer = self.get_serializer(self.get_object(), data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        flows_object_uuid = instance.config.get("channelUuid", None)
        if flows_object_uuid:
            self.type_class.release(
                FlowsClient(), flows_object_uuid, self.request.user.email
            )

        instance.delete()


class DetailGenericExternals(viewsets.ViewSet):
    """Search the details of a external type

    Args:
        flows_type_code

    Returns:
        attributes:{},
        form:{}
    """

    lookup_field = "flows_type_code"

    def retrieve(self, request, flows_type_code=None):
        client = FlowsClient()
        response = client.list_external_types(flows_type_code=flows_type_code)
        return Response(response)


class ExternalsIcons(viewsets.ViewSet):
    """Return a dictionary  with the channel_code as key and its value is the url of the icon

    Returns:
    {
        'tg': "url.com",
        'exemple': "url2.com"
    }
    """

    def list(self, request):
        client = FlowsClient()
        response = client.list_external_types()
        externals_icons = {}
        for external in response.get("external_types").keys():
            externals_icons[external] = search_icon(external)

        return Response(externals_icons)


class ExternalsAppTypes(viewsets.ViewSet):
    """Returns a dictionary of externals from flows

    Returns:
    {
    "omie": {
        "attributes": {...}
    },
    "...": {
        "attributes": {...}
    }...
    """

    def list(self, request):
        client = FlowsClient()
        response = client.list_external_types()
        types = sort_types(response.get("external_types"))
        return Response(types)


def search_icon(code):
    """Search icon url from a channel_code

    Args:
        Receive: code

    Return:
        "exemple.url.com"
    """
    apptype_asset = AppTypeAsset.objects.filter(code=code.lower())
    if apptype_asset.exists():
        apptype_asset = apptype_asset.first()
        icon_url = apptype_asset.attachment.url
    else:
        apptype_asset = AppTypeAsset.objects.filter(code="generic-external")
        if apptype_asset.exists():
            apptype_asset = apptype_asset.first()
            icon_url = apptype_asset.attachment.url
        else:
            icon_url = None

    return icon_url


def sort_types(types):
    """Receives a dictionary of types and returns
    them ordered by importance and alphabetical order of the code"""

    importance_order = (
        []
    )  # TODO: later a list of types will be introduced that must be displayed first
    keys_sorted = sorted(set(importance_order + list(types.keys())))
    items = [(key, types[key]) for key in keys_sorted]

    # Sort the list of tuples in order of importance and by name within the attributes
    items_sorted = sorted(
        items,
        key=lambda x: (
            importance_order.index(x[0]) if x[0] in importance_order else float("inf"),
            x[0],
        ),
    )
    types_sorted = {key: value for key, value in items_sorted}
    return types_sorted
