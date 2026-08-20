import logging
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from redis import Redis

from marketplace.applications.models import App
from marketplace.core.pacing.constants import TTL_WHATSAPP_CLOUD_WABAS
from marketplace.core.pacing.ttl import is_recently_synced, mark_synced
from marketplace.core.types.channels.whatsapp.apis import FacebookWABAApi


User = get_user_model()
logger = logging.getLogger(__name__)

WPP_CLOUD_CODE = "wpp-cloud"


class WABASyncUseCase:
    """Synchronize WABA metadata from Meta once per WABA, then fan-out to sibling apps."""

    def __init__(
        self,
        app: Optional[App] = None,
        redis_conn: Optional[Redis] = None,
        api_factory: Optional[Callable[[str], FacebookWABAApi]] = None,
        token_factory: Optional[Callable[[App], str]] = None,
    ):
        self.app = app
        self.redis_conn = redis_conn or get_redis_connection()
        self._api_factory = api_factory or self._default_api_factory
        self._token_factory = token_factory or self._default_token_factory

    def sync_waba(self, waba_id: str) -> Dict[str, Any]:
        """Fetch WABA data once and write `config.waba` on every eligible sibling."""
        eligible_apps = self._eligible_apps(waba_id)
        if not eligible_apps:
            logger.info(f"No eligible apps found for WABA sync: {waba_id}")
            return {"status": "skipped", "reason": "no_eligible_apps"}

        api = self._build_api(eligible_apps)
        if api is None:
            logger.error(f"No access token available for WABA sync: {waba_id}")
            return {"status": "error", "error": "no_access_token"}

        try:
            waba_data = api.get_waba(waba_id)
        except Exception as exc:
            logger.error(f"Error fetching WABA {waba_id}: {exc}")
            return {"status": "error", "error": str(exc)}

        admin = User.objects.get_admin_user()
        for app in eligible_apps:
            self._write_waba(app, deepcopy(waba_data), admin)

        mark_synced(
            self._ttl_key(waba_id),
            settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS,
            redis=self.redis_conn,
        )
        logger.info(
            f"Successfully synced WABA {waba_id} onto {len(eligible_apps)} app(s)."
        )
        return {
            "status": "synced",
            "waba": waba_data,
            "updated": len(eligible_apps),
        }

    def sync_whatsapp_cloud_waba(self) -> Dict[str, Any]:
        """Ensure `self.app` has `config.waba`, reusing a sibling cache when TTL is fresh."""
        app = self.app
        if app is None:
            return {"status": "error", "error": "app is required"}

        config = app.config or {}
        if "ignores_meta_sync" in config:
            logger.info(
                f"Skipping WABA sync for app {app.uuid} based on previous error: "
                f"{config['ignores_meta_sync']}"
            )
            return {"status": "skipped", "reason": "ignores_meta_sync_flag"}

        waba_id = config.get("wa_waba_id")
        if not waba_id:
            logger.info(
                f"Skipping WABA sync for app {app.uuid} because 'wa_waba_id' is missing."
            )
            return {"status": "skipped", "reason": "missing_wa_waba_id"}

        if is_recently_synced(self._ttl_key(waba_id), redis=self.redis_conn):
            copied_waba = self._copy_sibling_waba_cache(app, waba_id)
            if copied_waba is not None:
                logger.info(
                    f"Copied cached WABA {waba_id} onto app {app.uuid} (TTL still fresh)."
                )
                return {"status": "copied", "waba": copied_waba}

        return self.sync_waba(waba_id)

    def _eligible_apps(self, waba_id: str) -> List[App]:
        apps = App.objects.filter(
            code=WPP_CLOUD_CODE,
            configured=True,
            config__wa_waba_id=waba_id,
        )
        return [app for app in apps if "ignores_meta_sync" not in (app.config or {})]

    def _copy_sibling_waba_cache(
        self, app: App, waba_id: str
    ) -> Optional[Dict[str, Any]]:
        siblings = App.objects.filter(
            code=WPP_CLOUD_CODE,
            configured=True,
            config__wa_waba_id=waba_id,
        ).exclude(uuid=app.uuid)

        for sibling in siblings:
            sibling_config = sibling.config or {}
            if "ignores_meta_sync" in sibling_config:
                continue
            cached_waba = sibling_config.get("waba")
            if not cached_waba:
                continue
            self._write_waba(app, deepcopy(cached_waba), User.objects.get_admin_user())
            return cached_waba
        return None

    def _build_api(self, apps: List[App]) -> Optional[FacebookWABAApi]:
        for app in apps:
            try:
                token = self._token_factory(app)
            except Exception as exc:
                logger.warning(f"Failed to get access token for app {app.uuid}: {exc}")
                continue
            if not token:
                continue
            return self._api_factory(token)
        return None

    def _write_waba(self, app: App, waba_data: Dict[str, Any], admin) -> None:
        config = dict(app.config or {})
        config["waba"] = waba_data
        app.config = config
        app.modified_by = admin
        app.save()

    def _ttl_key(self, waba_id: str) -> str:
        return TTL_WHATSAPP_CLOUD_WABAS.format(waba_id=waba_id)

    @staticmethod
    def _default_token_factory(app: App) -> str:
        return app.apptype.get_access_token(app)

    @staticmethod
    def _default_api_factory(access_token: str) -> FacebookWABAApi:
        return FacebookWABAApi(access_token)
