import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional

import sentry_sdk
from django_redis import get_redis_connection

from marketplace.applications.models import App
from marketplace.clients.facebook.client import FacebookClient
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.facebook.service import BusinessMetaService


logger = logging.getLogger(__name__)


SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY = "sync-whatsapp-cloud-mmlite-status-lock"
WPP_CLOUD_CODE = "wpp-cloud"
MMLITE_STATUS_ACTIVE = "active"
META_ONBOARDING_STATUS_ONBOARDED = "ONBOARDED"


class SyncMmliteStatusUseCase:
    """Reconcile mmlite_status for wpp-cloud apps against Meta.

    Apps are grouped by `wa_waba_id` so each WABA is queried at most once. When
    any app sharing the WABA is already `active`, the remaining apps are flipped
    locally without a Meta call (sibling propagation). Whenever an app is flipped
    to `active`, the Flows channel config is also updated with `mmlite: True`.
    """

    def __init__(
        self,
        business_service_factory: Optional[Callable[[App], BusinessMetaService]] = None,
        flows_client: Optional[FlowsClient] = None,
        redis_connection=None,
    ):
        self._business_service_factory = (
            business_service_factory or self._default_business_service_factory
        )
        self.flows_client = flows_client or FlowsClient()
        self.redis = redis_connection or get_redis_connection()

    def execute(self) -> Optional[Dict[str, int]]:
        if self._is_locked():
            logger.info(
                "MMLite status sync is already running by another task, skipping."
            )
            return None

        summary = {
            "candidates": 0,
            "wabas": 0,
            "propagated": 0,
            "activated_via_meta": 0,
            "skipped_not_onboarded": 0,
            "errors": 0,
        }

        try:
            self._acquire_lock()
            grouped = self._group_candidates_by_waba()
            summary["wabas"] = len(grouped)
            summary["candidates"] = sum(len(apps) for apps in grouped.values())

            for waba_id, apps in grouped.items():
                try:
                    self._process_waba_group(waba_id, apps, summary)
                except Exception as exc:
                    summary["errors"] += 1
                    logger.error(
                        f"Error syncing mmlite status for waba {waba_id}: {exc}"
                    )
                    sentry_sdk.capture_exception(exc)

            return summary
        finally:
            self._release_lock()

    def _is_locked(self) -> bool:
        return bool(self.redis.get(SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY))

    def _acquire_lock(self) -> None:
        self.redis.set(SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY, "1", ex=600)

    def _release_lock(self) -> None:
        self.redis.delete(SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY)

    def _group_candidates_by_waba(self) -> Dict[str, List[App]]:
        # Django 3.2's .exclude on JSONField nested keys does not reliably
        # include rows where the key is missing, so the predicate is applied
        # in Python after a code-scoped DB filter.
        wpp_cloud_apps = App.objects.filter(code=WPP_CLOUD_CODE)

        grouped: Dict[str, List[App]] = defaultdict(list)
        for app in wpp_cloud_apps:
            config = app.config or {}
            if config.get("mmlite_status") == MMLITE_STATUS_ACTIVE:
                continue
            waba_id = config.get("wa_waba_id")
            if not waba_id:
                continue
            grouped[waba_id].append(app)
        return grouped

    def _has_active_sibling(self, waba_id: str) -> bool:
        return App.objects.filter(
            code=WPP_CLOUD_CODE,
            config__wa_waba_id=waba_id,
            config__mmlite_status=MMLITE_STATUS_ACTIVE,
        ).exists()

    def _process_waba_group(
        self, waba_id: str, apps: List[App], summary: Dict[str, int]
    ) -> None:
        if self._has_active_sibling(waba_id):
            logger.info(
                f"Propagating mmlite_status=active to {len(apps)} app(s) "
                f"sharing waba {waba_id} from already-active sibling."
            )
            for app in apps:
                self._promote_app_to_active(app)
            summary["propagated"] += len(apps)
            return

        meta_status = self._fetch_meta_status(waba_id, apps[0])
        if meta_status == META_ONBOARDING_STATUS_ONBOARDED:
            logger.info(
                f"Meta reports waba {waba_id} as ONBOARDED. "
                f"Flipping {len(apps)} app(s) to mmlite_status=active."
            )
            for app in apps:
                self._promote_app_to_active(app)
            summary["activated_via_meta"] += len(apps)
        else:
            logger.info(f"Meta reports waba {waba_id} as {meta_status!r}. Skipping.")
            summary["skipped_not_onboarded"] += len(apps)

    def _fetch_meta_status(
        self, waba_id: str, representative_app: App
    ) -> Optional[str]:
        business_service = self._business_service_factory(representative_app)
        response = business_service.get_mmlite_status(waba_id)
        return response.get("marketing_messages_onboarding_status")

    def _promote_app_to_active(self, app: App) -> None:
        app.config["mmlite_status"] = MMLITE_STATUS_ACTIVE
        app.save()

        if not app.flow_object_uuid:
            logger.info(
                f"App {app.uuid} has no flow_object_uuid; skipping Flows config update."
            )
            return

        try:
            detail_channel = self.flows_client.detail_channel(app.flow_object_uuid)
            flows_config = detail_channel.get("config") or {}
            flows_config["mmlite"] = True
            self.flows_client.update_config(
                data=flows_config, flow_object_uuid=app.flow_object_uuid
            )
        except Exception as exc:
            logger.error(f"Failed to update Flows config for app {app.uuid}: {exc}")
            sentry_sdk.capture_exception(exc)

    @staticmethod
    def _default_business_service_factory(app: App) -> BusinessMetaService:
        access_token = app.apptype.get_access_token(app)
        return BusinessMetaService(client=FacebookClient(access_token))
