import logging
from typing import Dict, List, Optional

from decouple import config

from django_redis import get_redis_connection
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from marketplace.clients.flows.client import FlowsClient
from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_insights_delete_sync import (
    WhatsAppInsightsDeleteSyncUseCase,
)

logger = logging.getLogger(__name__)

User = get_user_model()

SYNC_WHATSAPP_CLOUD_LOCK_KEY = "sync-whatsapp-cloud-lock"


class SyncWhatsAppCloudAppsUseCase:
    """UseCase for synchronizing WhatsApp Cloud apps with Flows channels."""

    def __init__(self):
        self.app_type = APPTYPES.get("wpp-cloud")
        self.client = FlowsClient()
        self.redis = get_redis_connection()
        self.admin_user = User.objects.get_admin_user()

    def execute(self) -> Optional[bool]:
        """Execute the synchronization process."""
        if self._is_locked():
            logger.info("The apps are already syncing by another task!")
            return None

        try:
            self._acquire_lock()
            channels = self._fetch_channels()
            self._process_channels(channels)
            return True
        finally:
            self._release_lock()

    def _is_locked(self) -> bool:
        """Check if the sync process is already locked."""
        return bool(self.redis.get(SYNC_WHATSAPP_CLOUD_LOCK_KEY))

    def _acquire_lock(self) -> None:
        """Acquire the lock for sync process."""
        self.redis.set(SYNC_WHATSAPP_CLOUD_LOCK_KEY, "1", ex=600)

    def _release_lock(self) -> None:
        """Release the lock for sync process."""
        self.redis.delete(SYNC_WHATSAPP_CLOUD_LOCK_KEY)

    def _fetch_channels(self) -> List[Dict]:
        """Fetch WhatsApp Cloud channels from Flows API."""
        return self.client.list_channels(
            self.app_type.flows_type_code, exclude_wpp_demo=True
        )

    def _process_channels(self, channels: List[Dict]) -> None:
        """Process all channels from the API."""
        for channel in channels:
            # Skipping WhatsApp demo channels
            if channel.get("address") == config("ROUTER_PHONE_NUMBER_ID"):
                continue

            try:
                self._process_single_channel(channel)
            except Exception as e:
                logger.error(
                    f"Error on processing sync_whatsapp_cloud_apps for channel {channel.get('uuid')}: {e}"
                )

    def _process_single_channel(self, channel: Dict) -> None:
        """Process a single WhatsApp Cloud channel."""
        project_uuid = channel.get("project_uuid")
        uuid = channel.get("uuid")
        address = channel.get("address")
        is_active = channel.get("is_active")

        if project_uuid is None:
            logger.info(f"The channel {uuid} does not have a project_uuid.")
            return

        config = self._prepare_config(channel, address)
        apps = App.objects.filter(flow_object_uuid=uuid)

        if apps.exists():
            self._update_existing_app(apps.first(), is_active, config)
        else:
            self._create_new_app(is_active, uuid, project_uuid, config)

    def _prepare_config(self, channel: Dict, address: str) -> Dict:
        """Prepare the app configuration from channel data."""
        config = channel.get("config", {})
        config["title"] = config.get("wa_number")
        config["wa_phone_number_id"] = address
        return config

    def _update_existing_app(self, app: App, is_active: bool, config: Dict) -> None:
        """Update an existing app or delete it if inactive."""
        if not is_active:
            try:
                app.delete()
                WhatsAppInsightsDeleteSyncUseCase(app).sync()
            except Exception as e:
                logger.error(str(e))
            return

        if app.code != self.app_type.code:
            logger.info(
                f"Migrating an {app.code} to WhatsApp Cloud Type. App: {app.uuid}"
            )
            app.code = self.app_type.code
            config["config_before_migration"] = app.config

        app.config = config
        app.modified_by = self.admin_user
        app.save()

    def _create_new_app(
        self, is_active: bool, uuid: str, project_uuid: str, config: Dict
    ) -> None:
        """Create a new app if needed."""
        if not is_active:
            logger.info(
                f"Skipping creation of WhatsApp Cloud app for the flow_object_uuid: {uuid} (is_active=False)"
            )
            return

        logger.info(
            f"Creating a new WhatsApp Cloud app for the flow_object_uuid: {uuid}"
        )
        self.app_type.create_app(
            created_by=self.admin_user,
            project_uuid=project_uuid,
            flow_object_uuid=uuid,
            config=config,
            configured=True,
        )
