from uuid import UUID
from dataclasses import dataclass
from typing import List

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage


class TemplateDetailUseCase:
    @dataclass(frozen=True)
    class WhatsappCloudDTO:
        app_uuid: str
        templates_uuid: List[str]

    @staticmethod
    def get_whatsapp_cloud_data_from_integrations(
        project_uuid: UUID, template_id: str
    ) -> List[WhatsappCloudDTO]:
        """
        Gets WhatsApp Cloud data from integrations.

        This function filters configured WhatsApp Cloud applications for a specific project
        and message templates matching the provided template ID, returning a list of DTOs
        with the app and template UUIDs.

        Args:
            project_uuid: UUID of the project to filter applications.
            template_id: Template ID to filter message templates.

        Returns:
            A list of WhatsappCloudDTO objects containing app UUID and template UUID pairs.
        """
        apps = App.objects.filter(
            project_uuid=project_uuid, code="wpp-cloud", configured=True
        )

        dtos = []

        for app in apps:
            templates = TemplateMessage.objects.filter(
                translations__message_template_id=template_id, app=app
            )
            templates_uuid = list(map(lambda template: str(template.uuid), templates))
            dtos.append(
                TemplateDetailUseCase.WhatsappCloudDTO(str(app.uuid), templates_uuid)
            )

        return dtos
