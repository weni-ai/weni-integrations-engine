from marketplace.clients.flows.client import FlowsClient
from marketplace.clients.commerce.client import CommerceClient
from marketplace.services.flows.service import FlowsService
from marketplace.services.commerce.service import CommerceService
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)
from marketplace.wpp_templates.utils import (
    TemplateCategoryChangeHandler,
    TemplateStatusUpdateHandler,
    TemplateWebhookEventProcessor,
)


def create_status_use_case(app):
    return TemplateLibraryStatusUseCase(app)


def create_template_webhook_event_processor() -> TemplateWebhookEventProcessor:
    flows_service = FlowsService(FlowsClient())
    commerce_service = CommerceService(CommerceClient())

    status_update_handler = TemplateStatusUpdateHandler(
        flows_service=flows_service,
        commerce_service=commerce_service,
        status_use_case_factory=create_status_use_case,
    )
    category_change_handler = TemplateCategoryChangeHandler(
        commerce_service=commerce_service,
    )

    return TemplateWebhookEventProcessor(
        status_update_handler=status_update_handler,
        category_change_handler=category_change_handler,
    )
