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

        ad_account_id = value.get("waba_info", {}).get("ad_account_id")
        if not ad_account_id:
            self.logger.info(f"Ad account id not found in webhook data: {webhook}")
            return

        for app in apps:
            app.config["ad_account_id"] = ad_account_id
            app.config["mmlite_status"] = "active"
            app.save()

    def process_event(self, waba_id: str, value: dict, event_type: str, webhook: dict):
        if event_type == "account_update":
            self.process_account_update(waba_id, value, webhook)
