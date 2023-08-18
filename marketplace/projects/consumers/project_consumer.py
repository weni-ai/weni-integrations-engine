import amqp

from ..usecases import TemplateTypeIntegrationUseCase, ProjectCreationUseCase, AppSetupHandlerUseCase, ProjectCreationDTO
from marketplace.connect.client import ConnectProjectClient, WPPRouterChannelClient
from marketplace.event_driven.parsers import JSONParser


class ProjectConsumer:
    @staticmethod
    def consume(message: amqp.Message):
        body = JSONParser.parse(message.body)
        print(f"[ProjectConsumer] - Consuming a message. Body: {body}")

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

        message.channel.basic_ack(message.delivery_tag)
