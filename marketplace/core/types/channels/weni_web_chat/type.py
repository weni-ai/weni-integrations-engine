from marketplace.core.types.base import AppType
from . import views
from marketplace.applications.models import App


class WeniWebChatType(AppType):
    view_class = views.WeniWebChatViewSet

    code = "wwc"
    name = "Weni Web Chat"
    description = "O chat da Weni"  # TODO: Change to real description
    summary = "O chat da Weni"  # TODO: Change to real summary
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = dict(red=250, green=250, blue=250, alpha=0.2)  # TODO: Change to real bg_color
    platform = App.PLATFORM_WENI_FLOWS
