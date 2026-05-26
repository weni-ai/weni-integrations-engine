"""Submit a Partner-led Business Verification request to Meta."""

import logging
from typing import Optional

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import BusinessVerificationService

from ..constants import CONFIG_KEY, MAX_DOCUMENTS, VerificationStatus
from ..dto import AccountVerificationStateDTO, SubmitAccountVerificationDTO
from ..state import apply_submit_response, read_state, to_dto


logger = logging.getLogger(__name__)


WPP_CLOUD_CODE = "wpp-cloud"


class SubmitAccountVerificationUseCase:
    """Submit business documents to Meta's self_certify_whatsapp_business endpoint."""

    def __init__(
        self,
        verification_service: Optional[BusinessVerificationService] = None,
        partner_business_id: Optional[str] = None,
    ):
        self._verification_service = verification_service or self._default_service()
        self._partner_business_id = (
            partner_business_id or settings.WHATSAPP_BSP_BUSINESS_ID
        )

    @staticmethod
    def _default_service() -> BusinessVerificationService:
        return BusinessVerificationService(
            client=FacebookClient(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        )

    def execute(self, dto: SubmitAccountVerificationDTO) -> AccountVerificationStateDTO:
        if not self._partner_business_id:
            raise ValidationError(
                "Partner business portfolio ID (WHATSAPP_BSP_BUSINESS_ID) is not configured."
            )

        app = self._get_app(dto.app_uuid)
        end_business_id = self._get_end_business_id(app)
        self._guard_submission_allowed(app)

        logger.info(
            f"Submitting business verification for app_uuid={app.uuid} "
            f"end_business_id={end_business_id} documents={len(dto.documents)}"
        )

        response = self._verification_service.submit(
            partner_business_id=self._partner_business_id,
            end_business_id=end_business_id,
            documents=dto.documents,
        )

        return self._record_meta_submission(app.pk, response)

    def _get_app(self, app_uuid: str) -> App:
        try:
            app = App.objects.get(uuid=app_uuid)
        except App.DoesNotExist as exc:
            raise ValidationError(f"App not found for uuid={app_uuid}") from exc

        if app.code != WPP_CLOUD_CODE:
            raise ValidationError(
                "Account verification is only supported for WhatsApp Cloud apps."
            )
        return app

    def _get_end_business_id(self, app: App) -> str:
        end_business_id = app.config.get("wa_business_id")
        if not end_business_id:
            raise ValidationError("App is missing 'wa_business_id' in its config.")
        return end_business_id

    def _guard_submission_allowed(self, app: App) -> None:
        state = read_state(app.config)
        attempts = int(state.get("verification_attempts") or 0)
        status = state.get("status")

        if status == VerificationStatus.APPROVED:
            raise ValidationError("Business is already verified.")
        if status == VerificationStatus.PENDING:
            raise ValidationError(
                "A previous submission is still pending. Wait for the result before submitting again."
            )
        if attempts >= MAX_DOCUMENTS:
            raise ValidationError(
                f"Maximum of {MAX_DOCUMENTS} verification attempts reached. "
                "The client must verify the business manually on Meta."
            )

    def _record_meta_submission(
        self, app_pk: int, meta_response: dict
    ) -> AccountVerificationStateDTO:
        """Persist the freshly-created submission into app.config.

        Meta's submit endpoint is asynchronous: it acknowledges the request
        with `{success, verification_attempts}` but the verdict (APPROVED or
        FAILED) only arrives later via the `PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE`
        webhook. Therefore every accepted submission starts as `PENDING` and
        is later updated by `ProcessCertificationWebhookUseCase`.
        """
        with transaction.atomic():
            app = App.objects.select_for_update().get(pk=app_pk)
            state = read_state(app.config)
            apply_submit_response(state, meta_response)
            app.config[CONFIG_KEY] = state
            app.save(update_fields=["config", "modified_on"])
        return to_dto(state)
