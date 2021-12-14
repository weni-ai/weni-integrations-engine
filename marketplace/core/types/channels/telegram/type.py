from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from . import views


class TelegramType(AppType):
    view_class = views.TelegramViewSet

    code = "tg"
    channeltype_code = "TG"
    name = "Telegram"
    description = "telegram.data.description"
    summary = "telegram.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#00DED333"
    platform = App.PLATFORM_WENI_FLOWS
