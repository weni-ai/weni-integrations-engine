import logging

from typing import Dict, Optional

from marketplace.services.insights.service import InsightsService
from marketplace.clients.insights.client import InsightsClient
from marketplace.applications.models import App


logger = logging.getLogger(__name__)


class WhatsAppInsightsSyncUseCase:
    """
    UseCase responsible for syncing WhatsApp data with Insights service.
    """

    def __init__(self, app: App, insights_service: Optional[InsightsService] = None):
        self.app = app
        self._insights_service = insights_service or InsightsService(
            client=InsightsClient()
        )

    def _prepare_whatsapp_data(self) -> Optional[Dict]:
        """
        Prepares WhatsApp data structure for insights integration.
        Returns None if required config fields are missing.
        """
        if not self.app.uuid:
            logger.warning(
                f"[Insights Sync] Skipping sync for app {self.app.uuid} due to missing fields: app_uuid"
            )
            return None

        if not self.app.project_uuid:
            logger.warning(
                f"[Insights Sync] Skipping sync for app {self.app.uuid} due to missing fields: project_uuid"
            )
            return None

        app_uuid = str(self.app.uuid)
        project_uuid = str(self.app.project_uuid)
        waba_id = self.app.config.get("wa_waba_id")
        phone_number_id = self.app.config.get("wa_phone_number_id")
        display_phone_number = self.app.config.get("wa_number")

        missing_fields = []
        if not waba_id:
            missing_fields.append("wa_waba_id")
        if not phone_number_id:
            missing_fields.append("wa_phone_number_id")
        if not display_phone_number:
            missing_fields.append("wa_number")

        if missing_fields:
            logger.warning(
                f"[Insights Sync] Skipping sync for app {self.app.uuid} due to missing fields: "
                f"{', '.join(missing_fields)}"
            )
            return None

        return {
            "app_uuid": app_uuid,
            "project_uuid": project_uuid,
            "waba_id": waba_id,
            "phone_number": {
                "id": phone_number_id,
                "display_phone_number": display_phone_number,
            },
        }

    def sync(self) -> None:
        """
        Executes the sync operation with insights service.
        Skips if required WhatsApp config is incomplete.
        """
        whatsapp_data = self._prepare_whatsapp_data()
        if not whatsapp_data:
            return

        self._insights_service.create_whatsapp_integration(whatsapp_data)
