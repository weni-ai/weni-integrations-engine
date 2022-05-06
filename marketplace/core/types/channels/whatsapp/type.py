import urllib

from decouple import config

from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import WhatsAppViewSet


class WhatsAppType(AppType):

    view_class = WhatsAppViewSet

    code = "wpp"
    channeltype_code = "WA"
    name = "WhatsApp"
    description = "WhatsApp.data.description"
    summary = "WhatsApp.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"  # TODO: Change to real color
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"
