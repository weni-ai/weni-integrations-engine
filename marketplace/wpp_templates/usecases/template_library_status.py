import logging
import json

from typing import Dict, Optional, Any

from django_redis import get_redis_connection
from marketplace.applications.models import App
from marketplace.clients.commerce.client import CommerceClient
from marketplace.services.commerce.service import CommerceService
from marketplace.wpp_templates.usecases.template_sync import TemplateSyncUseCase


logger = logging.getLogger(__name__)


class TemplateLibraryStatusUseCase:
    """
    Handles template status updates, synchronization with Redis, and notifying external modules.
    """

    def __init__(
        self,
        app: App,
        redis_conn: Optional[Any] = None,
        commerce_service: Optional[CommerceService] = None,
    ):
        self.app = app
        self.redis_conn = (
            redis_conn if redis_conn is not None else get_redis_connection()
        )
        self.redis_key = f"template_status:{str(self.app.uuid)}"
        self.commerce_service = commerce_service or CommerceService(CommerceClient())

    def update_template_status(self, template_name: str, new_status: str):
        """
        Updates the template status in Redis and verifies if all templates have been processed.
        """
        template_statuses = self._get_template_statuses_from_redis()
        if not template_statuses:
            logger.info(
                f"No Redis entry found for app {self.app.uuid}. Skipping update."
            )
            return

        # Update only the specific template
        if template_name in template_statuses:
            old_status = template_statuses[template_name]
            if old_status in ["REJECTED", "ERROR"]:
                logger.info(
                    f"Keeping {old_status} status for template '{template_name}' (app {self.app.uuid}). "
                    f"Attempted to change to '{new_status}'"
                )
            else:
                template_statuses[template_name] = new_status
                logger.info(
                    f"Template status updated for app {self.app.uuid}: '{template_name}' "
                    f"changed from '{old_status}' to '{new_status}'"
                )
            self._update_redis_status(template_statuses)

    def synchronize_all_stored_templates(self, skip_facebook_sync: bool = False):
        """
        Manually triggers the synchronization process for all templates stored in Redis.

        This method retrieves all template statuses from Redis and initiates the
        synchronization process. It's particularly useful for batch operations
        or when called from external systems that need to force a sync.
        """
        logger.info(
            f"Starting manual synchronization of all templates for app {self.app.uuid}"
        )
        template_statuses = self._get_template_statuses_from_redis()
        if not template_statuses:
            logger.info(f"No pending templates found for app {self.app.uuid}.")
            return

        logger.info(
            f"Found {len(template_statuses)} templates in Redis to synchronize for app {self.app.uuid}"
        )
        # Process all templates and complete synchronization if all are ready
        self._complete_sync_process_if_no_pending(template_statuses, skip_facebook_sync)

    def _complete_sync_process_if_no_pending(
        self, template_statuses: Dict[str, str], skip_facebook_sync: bool
    ):
        """
        Completes the synchronization process if no templates are pending.

        This method checks if there are any templates with PENDING status.
        If all templates are processed (not PENDING), it syncs with Facebook,
        notifies the commerce module, and cleans up the Redis storage.

        Args:
            template_statuses (Dict[str, str]): Dictionary mapping template names to their statuses.
        """
        logger.info(f"Starting sync completion process for app {self.app.uuid}")
        has_pending = any(status == "PENDING" for status in template_statuses.values())
        logger.info(
            f"Template pending status for app {self.app.uuid}: has pending: {has_pending}"
        )

        if not has_pending:
            if not skip_facebook_sync:
                logger.info(
                    f"No pending templates found. Syncing from Facebook for app {self.app.uuid}"
                )
                self.sync_templates_from_facebook(self.app)

            self.notify_commerce_module(template_statuses)
            self.redis_conn.delete(self.redis_key)
            logger.info(
                f"All templates synchronized and {self.redis_key} key removed for app {self.app.uuid}."
            )

        else:
            logger.info(
                f"Pending templates found. Skipping sync for app {self.app.uuid}"
            )

    def _get_template_statuses_from_redis(self) -> Dict[str, str]:
        """
        Fetches template statuses stored in Redis.
        """
        stored_status = self.redis_conn.get(self.redis_key)
        if not stored_status:
            return {}

        try:
            return json.loads(stored_status)
        except json.JSONDecodeError:
            logger.error(f"Corrupted Redis data for {self.redis_key}. Resetting.")
            self.redis_conn.delete(self.redis_key)  # Remove corrupted data
            return {}

    def _update_redis_status(self, template_statuses: Dict[str, str]):
        """
        Updates the template statuses in Redis.
        """
        self.redis_conn.set(
            self.redis_key, json.dumps(template_statuses), ex=60 * 60 * 24
        )

    def notify_commerce_module(self, template_statuses: Dict[str, str]):
        """
        Notifies the commerce module that all templates for the given app have been synced.

        Args:
            template_statuses (dict): The final statuses of all templates.
        """
        data = {
            "app_uuid": str(self.app.uuid),
            "template_statuses": template_statuses,
        }
        logger.info(f"Notifying commerce module for app {self.app.uuid}. data: {data}")
        response = self.commerce_service.send_template_library_status_update(data)
        logger.info(
            f"Commerce module notified for app {self.app.uuid}. response: {response}"
        )
        return response

    def store_pending_templates_status(self, templates_status: Dict[str, str]):
        """
        Stores the pending template statuses in Redis.

        Args:
            templates_status (dict): The dictionary containing template names and their statuses.
        """
        self._update_redis_status(templates_status)
        logger.info(
            f"Stored pending templates status for app {self.app.uuid} in Redis."
        )

    def cancel_scheduled_sync(
        self,
    ):  # TODO: adjust this method to cancel the task from the celery app
        """
        Cancels the scheduled sync task if all templates have been processed.
        """
        redis_task_key = f"sync_task:{self.app.uuid}"
        redis_task_id = self.redis_conn.get(redis_task_key)

        if redis_task_id:
            self.redis_conn.delete(redis_task_key)
            logger.info(f"Cancelled scheduled sync task for app {self.app.uuid}.")

    def sync_templates_from_facebook(self, app: App):
        """
        Syncs templates from Facebook to the database.
        """
        logger.info(f"Syncing templates with Facebook for app {self.app.uuid}")
        use_case = TemplateSyncUseCase(self.app)
        use_case.sync_templates()
        logger.info(
            f"Templates successfully synced from Facebook for app {self.app.uuid}"
        )
