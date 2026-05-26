import logging
from typing import Optional

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    CERTIFICATION_EVENT,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.usecases import (
    ProcessCertificationWebhookUseCase,
)


class AccountUpdateWebhookEventProcessor:
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        certification_use_case: Optional[ProcessCertificationWebhookUseCase] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self._certification_use_case = (
            certification_use_case or ProcessCertificationWebhookUseCase()
        )

    def get_apps_by_waba_id(self, waba_id: str):
        return App.objects.filter(config__wa_waba_id=waba_id)

    def process_account_update(self, waba_id: str, value: dict, webhook: dict):
        apps = self.get_apps_by_waba_id(waba_id)
        if not apps.exists():
            self.logger.info(f"There are no applications linked to waba: {waba_id}")
            return

        event_type = value.get("event", "")
        if not event_type:
            self.logger.info(f"Event type not found in webhook data: {webhook}")
            return

        if event_type == "MM_LITE_TERMS_SIGNED":
            for app in apps:
                app.config["mmlite_status"] = "active"
                app.save()
            return

        if event_type == CERTIFICATION_EVENT:
            self._certification_use_case.execute(waba_id=waba_id, value=value)
            return

    def process_event(self, waba_id: str, value: dict, event_type: str, webhook: dict):
        if event_type == "account_update":
            self.process_account_update(waba_id, value, webhook)
