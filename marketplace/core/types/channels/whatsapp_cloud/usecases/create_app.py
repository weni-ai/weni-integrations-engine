import logging
import string
from dataclasses import dataclass
from typing import Any, Optional

from django.utils.crypto import get_random_string

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp.usecases.phone_number_sync import (
    PhoneNumberSyncUseCase,
)
from marketplace.core.types.channels.whatsapp.usecases.waba_sync import WABASyncUseCase
from marketplace.core.types.channels.whatsapp_cloud.usecases.mmlite_status_sync import (
    SyncMmliteStatusUseCase,
)
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_insights_sync import (
    WhatsAppInsightsSyncUseCase,
)
from marketplace.services.facebook.service import (
    BusinessMetaService,
    PhoneNumbersService,
    TemplateService,
)
from marketplace.services.flows.service import FlowsService


logger = logging.getLogger(__name__)

APP_CODE = "wpp-cloud"
WABA_CURRENCY = "BRL"
PHONE_NUMBER_FIELDS = "display_phone_number,verified_name,status,platform_type"
CONNECTED_STATUS = "CONNECTED"
CLOUD_API_PLATFORM = "CLOUD_API"


@dataclass(frozen=True)
class CreateWhatsAppCloudAppDTO:
    project_uuid: Any
    waba_id: str
    phone_number_id: str
    auth_code: str
    created_by: Any
    user_email: str


class CreateWhatsAppCloudAppUseCase:
    def __init__(
        self,
        business_service: BusinessMetaService,
        phone_numbers_service: PhoneNumbersService,
        template_service: TemplateService,
        flows_service: FlowsService,
    ):
        self._business_service = business_service
        self._phone_numbers_service = phone_numbers_service
        self._template_service = template_service
        self._flows_service = flows_service

    def execute(self, dto: CreateWhatsAppCloudAppDTO) -> App:
        config_data = self._business_service.configure_whatsapp_cloud(
            dto.auth_code, dto.waba_id, dto.phone_number_id, WABA_CURRENCY
        )

        user_access_token = config_data["user_access_token"]
        phone_number = self._phone_numbers_service.get_phone_number(
            dto.phone_number_id, fields=PHONE_NUMBER_FIELDS
        )
        pin = self._register_phone_number_if_needed(
            dto.phone_number_id, user_access_token, phone_number
        )

        config = self._build_channel_config(
            dto=dto,
            phone_number=phone_number,
            pin=pin,
            user_access_token=user_access_token,
            business_id=config_data["business_id"],
            message_template_namespace=config_data["message_template_namespace"],
            dataset_id=config_data["dataset_id"],
        )

        channel = self._flows_service.create_wac_channel(
            dto.user_email, dto.project_uuid, dto.phone_number_id, config
        )

        config["title"] = config.get("wa_number")
        config["wa_allocation_config_id"] = config_data["allocation_config_id"]
        config["wa_phone_number_id"] = dto.phone_number_id
        config["has_insights"] = self._template_service.setup_insights(dto.waba_id)

        app = App.objects.create(
            code=APP_CODE,
            config=config,
            project_uuid=dto.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=dto.created_by,
            flow_object_uuid=channel.get("uuid"),
            configured=True,
        )

        self._sync_app(app)
        return app

    def _register_phone_number_if_needed(
        self, phone_number_id: str, user_access_token: str, phone_number: dict
    ) -> Optional[str]:
        if self._is_registered_for_cloud_api(phone_number):
            logger.info(
                f"Skipping phone number register; already CONNECTED on Cloud API. "
                f"phone_number_id={phone_number_id}"
            )
            return None

        pin = get_random_string(6, string.digits)
        self._business_service.register_phone_number(
            phone_number_id,
            user_access_token,
            dict(messaging_product="whatsapp", pin=pin),
        )
        return pin

    def _is_registered_for_cloud_api(self, phone_number: dict) -> bool:
        return (
            phone_number.get("status") == CONNECTED_STATUS
            and phone_number.get("platform_type") == CLOUD_API_PLATFORM
        )

    def _build_channel_config(
        self,
        dto: CreateWhatsAppCloudAppDTO,
        phone_number: dict,
        pin: Optional[str],
        user_access_token: str,
        business_id: str,
        message_template_namespace: str,
        dataset_id: Optional[str],
    ) -> dict:
        return dict(
            wa_number=phone_number.get("display_phone_number"),
            wa_verified_name=phone_number.get("verified_name"),
            wa_waba_id=dto.waba_id,
            wa_currency=WABA_CURRENCY,
            wa_business_id=business_id,
            wa_message_template_namespace=message_template_namespace,
            wa_pin=pin,
            wa_user_token=user_access_token,
            wa_dataset_id=dataset_id,
        )

    def _sync_app(self, app: App) -> None:
        WABASyncUseCase(app).sync_whatsapp_cloud_waba()
        PhoneNumberSyncUseCase(app).sync_whatsapp_cloud_phone_number()
        WhatsAppInsightsSyncUseCase(app).sync()
        SyncMmliteStatusUseCase().sync_for_app(app)
