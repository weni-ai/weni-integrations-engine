from marketplace.applications.models import App
from marketplace.services.flows.service import FlowsService
from marketplace.clients.exceptions import CustomAPIException
from marketplace.core.types.ecommerce.vtex.publisher.vtex_app_created_publisher import (
    VtexAppCreatedPublisher,
)

from rest_framework.exceptions import APIException

from typing import TypedDict, Optional, Union, Dict, Any


class CreateVtexIntegrationUseCase:
    def __init__(self, flows_service: FlowsService, publisher: VtexAppCreatedPublisher):
        self.flows_service = flows_service
        self.publisher = publisher

    class CreateVtexData(TypedDict):
        account: str
        store_type = Optional[str]
        project_uuid: str

    @staticmethod
    def configure_app(app: App, data: CreateVtexData) -> App:
        app.config["account"] = data.get("account")
        app.config["store_type"] = data.get("store_type")
        app.config["initial_sync_completed"] = False
        app.config["connected_catalog"] = False
        app.configured = True
        app.save()
        return app

    def notify_flows(self, app: App) -> Union[bool, CustomAPIException]:
        return self.flows_service.update_vtex_integration_status(
            app.project_uuid, app.created_by.email, action="POST"
        )

    def publish_to_queue(self, data: Dict[str, Any]) -> Optional[APIException]:
        success = self.publisher.create_event(data)

        if not success:
            raise APIException(detail={"error": "Failed to publish Vtex app creation."})
