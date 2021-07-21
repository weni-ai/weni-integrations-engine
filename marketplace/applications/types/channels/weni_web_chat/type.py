from marketplace.applications.types.base import AppType


class WeniWebChatType(AppType):
    code = "wwc"
    name = "Weni Web Chat"
    description = "O chat da Weni"  # TODO: Change to real description
    summary = "O chat da Weni"  # TODO: Change to real summary
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = dict(red=250, green=250, blue=250, alpha=0.2)  # TODO: Change to real bg_color
