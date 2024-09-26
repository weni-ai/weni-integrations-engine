from marketplace.core.types.emails.base_type import EmailAppType

from . import views


class GenericEmailType(EmailAppType):
    view_class = views.GenericEmailViewSet
    code = "email"
