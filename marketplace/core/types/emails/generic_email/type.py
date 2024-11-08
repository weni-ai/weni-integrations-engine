from marketplace.core.types.emails.base_type import EmailAppType

from . import views


class GenericEmailType(EmailAppType):
    view_class = views.GenericEmailViewSet
    code = "email"
    name = "Email"
    config_design = "sidebar"
    bg_color = "#C6FFF7"
