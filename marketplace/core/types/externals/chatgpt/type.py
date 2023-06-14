from ..base import ExternalAppType
from .views import ChatGPTViewSet


class ChatGPTType(ExternalAppType):
    view_class = ChatGPTViewSet
    code = "chatgpt"
    flows_type_code = "chatgpt"
    name = "ChatGPT"
    description = "chatgpt.data.description"
    summary = "chatgpt.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = ""
