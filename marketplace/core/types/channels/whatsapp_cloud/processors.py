import logging
from typing import Optional

from marketplace.applications.models import App


class AccountUpdateWebhookEventProcessor:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

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

        # For now, we only support MM_LITE_TERMS_SIGNED event
        if event_type == "MM_LITE_TERMS_SIGNED":
            for app in apps:
                app.config["mmlite_status"] = "active"
                app.save()

    def process_event(self, waba_id: str, value: dict, event_type: str, webhook: dict):
        if event_type == "account_update":
            self.process_account_update(waba_id, value, webhook)
