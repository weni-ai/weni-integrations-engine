from abc import abstractproperty

from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class ExternalAppType(AppType):

    platform = App.PLATFORM_WENI_FLOWS
    category = AppType.CATEGORY_EXTERNAL

    # TODO: uncomment this method
    # @abstractproperty
    # def flows_type_code(self) -> str:
    #     pass
