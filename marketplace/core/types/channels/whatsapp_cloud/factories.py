from marketplace.core.types.channels.whatsapp_cloud.processors import AccountUpdateWebhookEventProcessor


def create_account_update_webhook_event_processor() -> AccountUpdateWebhookEventProcessor:
    return AccountUpdateWebhookEventProcessor()
