QUEUE_WHATSAPP_TEMPLATES = "paced:whatsapp-templates"
QUEUE_FACEBOOK_CATALOGS = "paced:facebook-catalogs"
QUEUE_PRODUCT_POLICIES = "paced:product-policies"
QUEUE_WHATSAPP_CLOUD_WABAS = "paced:whatsapp-cloud-wabas"
QUEUE_WHATSAPP_CLOUD_PHONE_NUMBERS = "paced:whatsapp-cloud-phone-numbers"

TASK_DRAIN_PACED_QUEUE = "task_drain_paced_queue"
TASK_SYNC_WHATSAPP_TEMPLATES_ITEM = "task_sync_whatsapp_templates_item"
TASK_SYNC_FACEBOOK_CATALOG_ITEM = "task_sync_facebook_catalog_item"
TASK_SYNC_PRODUCT_POLICIES_ITEM = "task_sync_product_policies_item"
TASK_SYNC_WHATSAPP_CLOUD_WABA_ITEM = "task_sync_whatsapp_cloud_waba_item"
TASK_SYNC_WHATSAPP_CLOUD_PHONE_NUMBER_ITEM = (
    "task_sync_whatsapp_cloud_phone_number_item"
)

TTL_WHATSAPP_TEMPLATES = "sync-whatsapp-templates-lock-waba:{waba_id}"
TTL_FACEBOOK_CATALOGS = "sync-facebook-catalogs-lock-app:{app_uuid}"
TTL_PRODUCT_POLICIES = "sync-product-policies-lock-catalog:{catalog_uuid}"
TTL_WHATSAPP_CLOUD_WABAS = "sync-whatsapp-cloud-waba-lock-waba:{waba_id}"
