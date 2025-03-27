import logging

from typing import Dict, Any, Optional

from redis import Redis

from django_redis import get_redis_connection
from django.conf import settings
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp.apis import FacebookWABAApi


User = get_user_model()
logger = logging.getLogger(__name__)

# Redis lock key for WABA synchronization
SYNC_WHATSAPP_WABA_LOCK_KEY = "sync_whatsapp_waba_lock:{app_uuid}"


class WABASyncUseCase:
    """
    Handles synchronization of WABA (WhatsApp Business Account) data from Facebook for a given app.
    """

    def __init__(self, app: App, redis_conn: Optional[Redis] = None):
        """
        Initialize the use case with an app and optional Redis connection.

        Args:
            app: The WhatsApp app to sync WABA for
            redis_conn: Optional Redis connection, will create one if not provided
        """
        self.app = app
        self.redis_conn = redis_conn or get_redis_connection()

    def sync_whatsapp_cloud_waba(self) -> Dict[str, Any]:
        """
        Synchronizes the WABA for the given app from Facebook.

        Returns:
            A dictionary with the result of the synchronization.
        """
        skip_result = self._check_sync_eligibility()
        if skip_result:
            return skip_result

        try:
            # Get access token and initialize API
            access_token = self.app.apptype.get_access_token(self.app)
            api = FacebookWABAApi(access_token)

            # Fetch waba_id from config
            waba_id = self.app.config.get("wa_waba_id")
            waba_data = api.get_waba(waba_id)

            # Update app configuration
            self._update_app_config_with_waba_data(waba_data)

            # Set lock to prevent frequent synchronizations
            self._set_sync_lock()

            logger.info(f"Successfully synced WABA for app {self.app.uuid}.")
            return {"status": "synced", "waba": self.app.config["waba"]}

        except Exception as e:
            logger.info(f"Error syncing WABA for app {self.app.uuid}: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _get_lock_key(self) -> str:
        """Generate the Redis lock key for the current app."""
        return SYNC_WHATSAPP_WABA_LOCK_KEY.format(app_uuid=str(self.app.uuid))

    def _check_sync_eligibility(self) -> Optional[Dict[str, Any]]:
        """
        Check if the app is eligible for synchronization.
        Returns:
            None if eligible, otherwise a dict with skip status and reason
        """
        key = self._get_lock_key()

        # Check if sync should be ignored
        if "ignores_meta_sync" in self.app.config:
            logger.info(
                f"Skipping WABA sync for app {self.app.uuid} based on previous error: "
                f"{self.app.config['ignores_meta_sync']}"
            )
            return {"status": "skipped", "reason": "ignores_meta_sync_flag"}

        # Check for recent sync lock
        if self.redis_conn.get(key) is not None:
            ttl = self.redis_conn.ttl(key)
            logger.info(
                f"Skipping WABA sync for app {self.app.uuid} (lock active, {ttl} seconds left)."
            )
            return {"status": "skipped", "reason": "recently_synced"}

        # Check for waba_id
        waba_id = self.app.config.get("wa_waba_id")
        if not waba_id:
            logger.info(
                f"Skipping WABA sync for app {self.app.uuid} because 'wa_waba_id' is missing."
            )
            return {"status": "skipped", "reason": "missing_wa_waba_id"}

        return None

    def _update_app_config_with_waba_data(self, waba_data: Dict[str, Any]) -> None:
        """Update app configuration with WABA data from Facebook."""
        self.app.config["waba"] = waba_data
        self.app.modified_by = User.objects.get_admin_user()
        self.app.save()

    def _set_sync_lock(self) -> None:
        """Set Redis lock to prevent frequent synchronizations."""
        key = self._get_lock_key()
        self.redis_conn.set(
            key,
            "synced",
            settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS,
        )
