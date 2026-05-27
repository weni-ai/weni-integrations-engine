"""Fetch the current Account Verification state with cache + Meta sync."""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import BusinessVerificationService

from ..constants import CONFIG_KEY, build_cache_key
from ..dto import AccountVerificationStateDTO
from ..state import (
    merge_from_meta_submissions,
    now_iso,
    read_state,
    to_dto,
)


logger = logging.getLogger(__name__)


WPP_CLOUD_CODE = "wpp-cloud"

DEFAULT_CACHE_TTL = 60


class GetAccountVerificationStatusUseCase:
    """Read state from app.config, refreshing from Meta when the cache is stale."""

    def __init__(
        self,
        verification_service: Optional[BusinessVerificationService] = None,
        cache_backend=None,
        ttl: Optional[int] = None,
        partner_business_id: Optional[str] = None,
    ):
        self._verification_service = verification_service or self._default_service()
        self._cache = cache_backend or cache
        self._ttl = (
            ttl
            if ttl is not None
            else getattr(settings, "ACCOUNT_VERIFICATION_CACHE_TTL", DEFAULT_CACHE_TTL)
        )
        self._partner_business_id = (
            partner_business_id or settings.WHATSAPP_BSP_BUSINESS_ID
        )

    @staticmethod
    def _default_service() -> BusinessVerificationService:  # pragma: no cover
        # DI fallback: instantiated only when no service is injected. Tests
        # always inject a mock so this branch is unreachable in unit tests.
        return BusinessVerificationService(
            client=FacebookClient(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
        )

    def execute(self, app_uuid: str) -> AccountVerificationStateDTO:
        app = self._get_app(app_uuid)
        end_business_id = app.config.get("wa_business_id")

        if not end_business_id or not self._partner_business_id:
            return to_dto(read_state(app.config))

        submissions = self._fetch_submissions(end_business_id)
        if submissions is None:
            return to_dto(read_state(app.config))

        return self._sync_and_return(app.pk, submissions)

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

    def _fetch_submissions(
        self, end_business_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        cache_key = build_cache_key(end_business_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug(
                f"account-verification cache hit end_business_id={end_business_id}"
            )
            return cached

        try:
            response = self._verification_service.list_submissions(
                partner_business_id=self._partner_business_id,
                end_business_id=end_business_id,
            )
        except CustomAPIException as exc:
            logger.warning(
                f"Failed to refresh account verification status from Meta "
                f"end_business_id={end_business_id}: {exc}"
            )
            return None

        submissions = response.get("data") or []
        self._cache.set(cache_key, submissions, self._ttl)
        return submissions

    def _sync_and_return(
        self, app_pk: int, submissions: List[Dict[str, Any]]
    ) -> AccountVerificationStateDTO:
        with transaction.atomic():
            app = App.objects.select_for_update().get(pk=app_pk)
            state = read_state(app.config)
            merge_from_meta_submissions(state, submissions)
            state["last_synced_at"] = now_iso()
            app.config[CONFIG_KEY] = state
            app.save(update_fields=["config", "modified_on"])
        return to_dto(state)


def invalidate_account_verification_cache(end_business_id: str) -> None:
    """Drop the cached submissions list for a single client business portfolio."""
    cache.delete(build_cache_key(end_business_id))
