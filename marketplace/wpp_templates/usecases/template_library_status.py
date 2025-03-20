from datetime import timedelta
import logging
import json

from typing import Dict, Optional, Any

from django_redis import get_redis_connection
from marketplace.applications.models import App
from marketplace.clients.commerce.client import CommerceClient
from marketplace.services.commerce.service import CommerceService


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
            template_statuses[template_name] = new_status
            self._update_redis_status(template_statuses)

        # Call the unified method to finalize if needed
        self._finalize_template_sync(template_statuses)

    def sync_all_templates(self):
        """
        Manually triggers the synchronization process for all stored templates.
        Useful for batch processing or external calls.
        """
        template_statuses = self._get_template_statuses_from_redis()
        if not template_statuses:
            logger.info(f"No pending templates found for app {self.app.uuid}.")
            return

        # Call the unified method to finalize if needed
        self._finalize_template_sync(template_statuses)

    def _finalize_template_sync(self, template_statuses: Dict[str, str]):
        """
        Finalizes the synchronization process if no pending templates remain.

        If all templates have been processed, notifies the commerce module,
        deletes the Redis key, and cancels the scheduled sync task.

        Args:
            template_statuses (dict): The final statuses of all templates.
        """
        has_pending = any(status == "PENDING" for status in template_statuses.values())

        if not has_pending:
            self.notify_commerce_module(template_statuses)
            self.redis_conn.delete(self.redis_key)
            self.cancel_scheduled_sync()
            logger.info(
                f"All templates synchronized and Redis key removed for app {self.app.uuid}."
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
        response = self.commerce_service.send_template_library_status_update(data)
        logger.info(f"Commerce module notified for app {self.app.uuid}.")
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

    def schedule_final_sync(self):
        """
        Schedules a final sync task to check pending templates after a defined waiting period.
        """
        from marketplace.wpp_templates.tasks import (
            sync_pending_templates,
        )  # TODO: Remove this import and fix circular import

        countdown = timedelta(hours=8).total_seconds()
        sync_pending_templates.apply_async((str(self.app.uuid),), countdown=countdown)
        logger.info(f"Scheduled final sync task for app {self.app.uuid} in 8 hours.")

    def cancel_scheduled_sync(self):
        """
        Cancels the scheduled sync task if all templates have been processed.
        """
        redis_task_key = f"sync_task:{self.app.uuid}"
        redis_task_id = self.redis_conn.get(redis_task_key)

        if redis_task_id:
            self.redis_conn.delete(redis_task_key)
            logger.info(f"Cancelled scheduled sync task for app {self.app.uuid}.")
