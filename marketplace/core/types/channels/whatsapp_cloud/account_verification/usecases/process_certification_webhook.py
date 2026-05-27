"""Process the PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE webhook from Meta."""

import logging
from typing import Optional

from django.db import transaction

from marketplace.applications.models import App
from marketplace.clients.connect.client import ConnectClient
from marketplace.services.connect.service import ConnectService

from ..constants import CONFIG_KEY, VerificationStatus
from ..state import apply_webhook_event, read_state
from .get_account_verification_status import (
    invalidate_account_verification_cache,
)


logger = logging.getLogger(__name__)


class ProcessCertificationWebhookUseCase:
    """Update app.config with the verification result and notify the customer.

    Notification flow: integrations-engine -> Connect internal endpoint.
    Connect renders the email template (respecting User.language) and sends it.
    """

    def __init__(self, connect_service: Optional[ConnectService] = None):
        self._connect_service = connect_service or ConnectService(
            client=ConnectClient()
        )

    def execute(self, waba_id: str, value: dict) -> None:
        partner_info = value.get("partner_client_certification_info") or {}
        client_business_id = partner_info.get("client_business_id")

        if not client_business_id:
            logger.info(
                f"Missing client_business_id in certification webhook payload: {value}"
            )
            return

        app = self._resolve_app(waba_id=waba_id, client_business_id=client_business_id)
        if app is None:
            logger.info(
                f"No app matched certification webhook waba_id={waba_id} "
                f"client_business_id={client_business_id}"
            )
            return

        updated_state = self._update_state(app.pk, partner_info)
        if updated_state is None:
            logger.info(
                f"Certification webhook ignored as duplicate for app_uuid={app.uuid}"
            )
            return

        invalidate_account_verification_cache(client_business_id)

        self._notify_customer(app, updated_state)

    def _resolve_app(self, waba_id: str, client_business_id: str) -> Optional[App]:
        app = App.objects.filter(
            code="wpp-cloud", config__wa_business_id=client_business_id
        ).first()
        if app:
            return app
        return App.objects.filter(code="wpp-cloud", config__wa_waba_id=waba_id).first()

    def _update_state(self, app_pk: int, partner_info: dict) -> Optional[dict]:
        new_status = partner_info.get("status")
        if new_status not in (VerificationStatus.APPROVED, VerificationStatus.FAILED):
            logger.info(
                f"Ignoring certification webhook with unsupported status={new_status!r}"
            )
            return None

        with transaction.atomic():
            app = App.objects.select_for_update().get(pk=app_pk)
            state = read_state(app.config)

            if state.get("status") == new_status:
                return None

            apply_webhook_event(state, partner_info)
            app.config[CONFIG_KEY] = state
            app.save(update_fields=["config", "modified_on"])
            return state

    def _notify_customer(self, app: App, state: dict) -> None:
        user_email = self._resolve_user_email(app)
        if not user_email:  # pragma: no cover
            # Defensive: App.created_by is a PROTECT FK, so an email is always
            # present in practice. Branch kept to avoid crashing on data drift.
            logger.warning(
                f"Skipping verification email for app_uuid={app.uuid}: no user email."
            )
            return

        try:
            self._connect_service.notify_business_verification(
                user_email=user_email,
                status=state.get("status"),
                rejection_reasons=state.get("rejection_reasons") or [],
                verification_attempts=int(state.get("verification_attempts") or 0),
            )
        except Exception as exc:
            logger.error(
                f"Failed to notify Connect about business verification result "
                f"for app_uuid={app.uuid}: {exc}"
            )

    def _resolve_user_email(self, app: App) -> Optional[str]:
        return getattr(app.created_by, "email", None)
