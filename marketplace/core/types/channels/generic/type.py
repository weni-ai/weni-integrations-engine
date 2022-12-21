from decouple import config
import json

from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import GenericChannelViewSet
from marketplace.connect.client import ConnectProjectClient

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
    channels_available = None #[get_channel_types()]
