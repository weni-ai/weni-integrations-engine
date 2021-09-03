from marketplace.core.types.base import AppType
from . import views
from marketplace.applications.models import App


class WeniWebChatType(AppType):
    view_class = views.WeniWebChatViewSet

    code = "wwc"
    name = "Weni Web Chat"
    description = "weniWebChat.data.description"
    summary = "weniWebChat.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#00DED333"
    platform = App.PLATFORM_WENI_FLOWS
