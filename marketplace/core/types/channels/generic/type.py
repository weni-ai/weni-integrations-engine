
from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import GenericChannelViewSet


def get_channel_types():
    from marketplace.connect.client import ConnectProjectClient
    response = ConnectProjectClient().list_availables_channels()
    if response.status_code == 200:
        return response.json().get("channel_types")

    return None


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
