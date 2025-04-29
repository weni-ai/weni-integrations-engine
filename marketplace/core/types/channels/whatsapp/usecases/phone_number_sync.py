import logging
from typing import Dict, Optional, Any

from django_redis import get_redis_connection
from django.conf import settings
from redis import Redis

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp.apis import FacebookPhoneNumbersAPI
from django.contrib.auth import get_user_model


User = get_user_model()
logger = logging.getLogger(__name__)

# Redis lock key for phone number synchronization
SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY = "sync_whatsapp_phone_number_lock:{app_uuid}"


class PhoneNumberSyncUseCase:
    """
    Handles synchronization of WhatsApp phone numbers from Facebook for a given app.
    """

    def __init__(self, app: App, redis_conn: Optional[Redis] = None):
        """
        Initialize the use case with an app and optional Redis connection.

        Args:
            app: The WhatsApp app to sync phone number for
            redis_conn: Optional Redis connection, will create one if not provided
        """
        self.app = app
        self.redis_conn = redis_conn or get_redis_connection()

    def sync_whatsapp_cloud_phone_number(self) -> Dict[str, Any]:
        """
        Synchronizes the phone number for the given app from Facebook.

        Returns:
            A dictionary with the result of the synchronization.
        """
        # Check if app is eligible for synchronization
        skip_result = self._check_sync_eligibility()
        if skip_result:
            return skip_result

        try:
            # Get access token and initialize API
            access_token = self.app.apptype.get_access_token(self.app)
            api = FacebookPhoneNumbersAPI(access_token)

            # Fetch phone number data
            phone_number_id = self.app.config.get("wa_phone_number_id")
            phone_data = api.get_phone_number(phone_number_id)

            # Update app configuration with phone data
            self._update_app_config_with_phone_data(phone_data)

            # Set lock to prevent frequent synchronizations
            self._set_sync_lock()

            logger.info(f"Successfully synced phone number for app {self.app.uuid}.")
            return {"status": "synced", "phone_number": self.app.config["phone_number"]}

        except Exception as e:
            logger.info(f"Error syncing phone number for app {self.app.uuid}: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _get_lock_key(self) -> str:
        """
        Generate the Redis lock key for the current app.

        Returns:
            The formatted Redis lock key
        """
        return SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY.format(app_uuid=str(self.app.uuid))

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
                f"Skipping sync for app {self.app.uuid} based on previous error: "
                f"{self.app.config['ignores_meta_sync']}"
            )
            return {"status": "skipped", "reason": "ignores_meta_sync_flag"}

        # Check for recent sync lock
        if self.redis_conn.get(key) is not None:
            ttl = self.redis_conn.ttl(key)
            logger.info(
                f"Skipping sync for app {self.app.uuid} (lock active, {ttl} seconds left)."
            )
            return {"status": "skipped", "reason": "recently_synced"}

        # Check for phone number ID
        phone_number_id = self.app.config.get("wa_phone_number_id")
        if not phone_number_id:
            logger.info(
                f"Skipping sync for app {self.app.uuid} because 'wa_phone_number_id' is missing."
            )
            return {"status": "skipped", "reason": "missing_wa_phone_number_id"}

        return None

    def _update_app_config_with_phone_data(self, phone_data: Dict[str, Any]) -> None:
        """
        Update app configuration with phone number data.

        Args:
            phone_data: Phone number data from Facebook API
        """
        phone_number_id = phone_data.get("id")
        display_phone_number = phone_data.get("display_phone_number")
        verified_name = phone_data.get("verified_name")
        consent_status = phone_data.get("cert_status")
        certificate = phone_data.get("certificate")

        # Update app configuration
        self.app.config["phone_number"] = {
            "id": phone_number_id,
            "display_phone_number": display_phone_number,
            "display_name": verified_name,
        }

        if consent_status is not None:
            self.app.config["phone_number"]["cert_status"] = consent_status

        if certificate is not None:
            self.app.config["phone_number"]["certificate"] = certificate

        # Save changes
        self.app.modified_by = User.objects.get_admin_user()
        self.app.save()

    def _set_sync_lock(self) -> None:
        """Set Redis lock to prevent frequent synchronizations"""
        key = self._get_lock_key()
        self.redis_conn.set(
            key,
            "synced",
            ex=settings.WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS,
        )
