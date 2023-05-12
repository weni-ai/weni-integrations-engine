from .views import GenericExternalsViewSet

from marketplace.interfaces.flows import FlowsInterface
from marketplace.interfaces.connect import ConnectInterface

from marketplace.core.types.base import AppType, GenericAppType


class GenericExternalAppType(GenericAppType):
    view_class = GenericExternalsViewSet
    category = AppType.CATEGORY_EXTERNAL
    code = "generic-external"

    @classmethod
    def list(cls, client: FlowsInterface, flows_type_code=None):
        return client.list_external_types(flows_type_code)

    @classmethod
    def release(cls, client: FlowsInterface, uuid: str, user_email: str):
        return client.release_external_service(uuid, user_email)

    @classmethod
    def create(
        cls,
        client: ConnectInterface,
        user: str,
        project_uuid: str,
        attrs: dict,
        external_code: str,
    ):
        return client.create_external_service(user, project_uuid, attrs, external_code)
