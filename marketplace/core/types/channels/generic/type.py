from decouple import config
import json

from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import GenericChannelViewSet
from marketplace.connect.client import ConnectProjectClient


def get_channel_types():
        response = ConnectProjectClient().list_availables_channels()
        channel_types = response.json().get("channel_types")
        if channel_types:
            for channel in channel_types.keys():
                attribute_channel_types = channel_types.get(channel)
                channel_types[channel]["attributes"] = search_icon(attribute_channel_types["attributes"])
        return channel_types


def search_icon(attributes):
    # apptype_asset = AppTypeAsset.objects.filter(code=attributes.get("code").lower())
    # if apptype_asset.exists():
    #     apptype_asset = apptype_asset.first()
    #     icon_url = apptype_asset.url
    # else:
    icon_url = None

    attributes["icon_url"] = icon_url
    return attributes


class GenericType(AppType):    
    view_class = GenericChannelViewSet
    code = "generic"
    channeltype_code = None
    name = "Generic Type"
    description = "Generic.data.description"
    summary = "Generic.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"
    channels_available = [get_channel_types()]


