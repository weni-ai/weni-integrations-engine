import amqp

from ..usecases import ProjectCreationUseCase, AppSetupHandlerUseCase, ProjectCreationDTO
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
            user_email=body.get("user_email"),
            date_format=body.get("date_format"),
            template_type_uuid=body.get("template_type_uuid"),
            timezone=body.get("timezone"),
        )

        connect_client = ConnectProjectClient()
        wpp_router_client = WPPRouterChannelClient()

        app_setup_handler = AppSetupHandlerUseCase(connect_client, wpp_router_client)

        project_creation = ProjectCreationUseCase(app_setup_handler)
        project_creation.create_project(project_dto)

        message.channel.basic_ack(message.delivery_tag)
