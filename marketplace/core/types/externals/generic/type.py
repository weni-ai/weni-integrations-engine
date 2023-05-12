from .views import GenericExternalsViewSet

from marketplace.applications.models import App
from marketplace.interfaces.flows import FlowsInterface

from marketplace.core.types.base import AppType, GenericAppType


class GenericExternalsAppType(GenericAppType):
    view_class = GenericExternalsViewSet
    platform = App.PLATFORM_WENI_FLOWS
    category = AppType.CATEGORY_EXTERNAL

    def list(self, flows_client: FlowsInterface, flows_type_code=None):
        return flows_client.list_external_types(flows_type_code)

    def release(self, flows_client: FlowsInterface, uuid: str, user_email: str):
        return flows_client.release_external_service(uuid, user_email)
