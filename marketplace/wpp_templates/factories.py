from marketplace.clients.flows.client import FlowsClient
from marketplace.clients.commerce.client import CommerceClient
from marketplace.services.flows.service import FlowsService
from marketplace.services.commerce.service import CommerceService
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)
from marketplace.wpp_templates.utils import (
    TemplateStatusUpdateHandler,
    WebhookEventProcessor,
)


def create_status_use_case(app):
    return TemplateLibraryStatusUseCase(app)


def create_webhook_event_processor() -> WebhookEventProcessor:
    flows_service = FlowsService(FlowsClient())
    commerce_service = CommerceService(CommerceClient())

    handler = TemplateStatusUpdateHandler(
        flows_service=flows_service,
        commerce_service=commerce_service,
        status_use_case_factory=create_status_use_case,
    )

    return WebhookEventProcessor(handler=handler)
