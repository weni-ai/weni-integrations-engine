import logging

from typing import Optional, TypedDict

from marketplace.services.insights.service import InsightsService
from marketplace.clients.insights.client import InsightsClient
from marketplace.interfaces.insights.interfaces import InsightsUseCaseSyncInterface
from marketplace.applications.models import App

logger = logging.getLogger(__name__)


class WhatsAppInsightsDeleteSyncUseCase(InsightsUseCaseSyncInterface):
    """
    UseCase responsible for syncing WhatsApp data with Insights service when template
    is deleted.
    """

    class WhatsappDeleteData(TypedDict):
        project_uuid: str
        waba_id: str

    def __init__(
        self,
        app: App,
        insights_service: Optional[InsightsService] = None,
    ):
        self.instance = app
        self._insights_service = insights_service or InsightsService(
            client=InsightsClient()
        )

    def _collect_template_data(self) -> WhatsappDeleteData:
        return {
            "waba_id": self.instance.config.get("wa_waba_id"),
            "project_uuid": str(self.instance.project_uuid),
        }

    def sync(self) -> None:
        whatsapp_delete_data = self._collect_template_data()
        self._insights_service.delete_whatsapp_integration(
            whatsapp_delete_data["project_uuid"], whatsapp_delete_data["waba_id"]
        )
