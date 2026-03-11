import logging

from marketplace.applications.models import App

logger = logging.getLogger(__name__)

WEBCHAT_APP_CODE = "wwc"


class CheckWebChatIntegrationUseCase:
    def execute(self, project_uuid: str) -> dict:
        logger.info(f"Checking webchat integration for project_uuid={project_uuid}")

        app = App.objects.filter(
            code=WEBCHAT_APP_CODE,
            project_uuid=project_uuid,
        ).first()

        if not app:
            return {"has_webchat": False}

        return {
            "has_webchat": True,
            "webchat_app_uuid": str(app.uuid),
            "flows_channel_uuid": str(app.flow_object_uuid),
        }
