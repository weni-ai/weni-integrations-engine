from marketplace.core.types.emails.base_type import EmailAppType

from . import views


class GmailType(EmailAppType):
    view_class = views.GmailViewSet
    code = "gmail"
