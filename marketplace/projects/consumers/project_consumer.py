import amqp
from sentry_sdk import capture_exception

from ..usecases import TemplateTypeIntegrationUseCase, ProjectCreationUseCase, AppSetupHandlerUseCase, ProjectCreationDTO
from ..usecases.exceptions import InvalidProjectData, InvalidTemplateTypeData
from marketplace.connect.client import ConnectProjectClient, WPPRouterChannelClient
from marketplace.event_driven.parsers import JSONParser, ParseError
from marketplace.event_driven.consumers import EDAConsumer


class ProjectConsumer(EDAConsumer):
    def consume(self, message: amqp.Message):
        print(f"[ProjectConsumer] - Consuming a message. Body: {message.body}")

        try:
            body = JSONParser.parse(message.body)

            project_dto = ProjectCreationDTO(
                uuid=body.get("uuid"),
                name=body.get("name"),
                is_template=body.get("is_template"),
                date_format=body.get("date_format"),
                template_type_uuid=body.get("template_type_uuid"),
                timezone=body.get("timezone"),
            )

            connect_client = ConnectProjectClient()
            wpp_router_client = WPPRouterChannelClient()

            app_setup_handler = AppSetupHandlerUseCase(connect_client, wpp_router_client)
            template_type_integration = TemplateTypeIntegrationUseCase(app_setup_handler)

            project_creation = ProjectCreationUseCase(template_type_integration)
            project_creation.create_project(project_dto, body.get("user_email"))

        except Exception as exception:
            capture_exception(exception)
            message.channel.basic_reject(message.delivery_tag, requeue=False)
            print(f"[ProjectConsumer] - Message rejected by: {exception}")
            return None

        message.channel.basic_ack(message.delivery_tag)
