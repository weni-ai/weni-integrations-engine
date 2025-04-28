from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class NewWeniWebChatType(AppType):
    code = "nwwc"
    flows_type_code = "NWWC"
    name = "New Weni Web Chat"
    description = "newWeniWebChat.data.description"
    summary = "newWeniWebChat.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#00DED333"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "sidebar"

    @property
    def view_class(self):
        from . import views

        return views.NewWeniWebChatViewSet
