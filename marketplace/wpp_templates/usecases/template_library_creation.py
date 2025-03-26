import logging

from copy import deepcopy

from typing import Dict, Any, Optional

from django.conf import settings

from marketplace.applications.models import App

from marketplace.clients.exceptions import CustomAPIException
from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import TemplateService
from marketplace.celery import app as celery_app


logger = logging.getLogger(__name__)


class TemplateCreationUseCase:
    """
    Handles the creation of multiple library templates and their status tracking.
    """

    def __init__(
        self,
        app: App,
        service: Optional[TemplateService] = None,
        status_use_case: Optional[TemplateLibraryStatusUseCase] = None,
    ):
        """
        Initializes the use case with optional dependency injection for easier unit testing.

        Args:
            app (App): The application instance.
            service (TemplateService, optional): Template service instance. Defaults to None.
            status_use_case (TemplateLibraryStatusUseCase, optional): Status tracking use case. Defaults to None.
        """
        self.app = app
        self.service = service or TemplateService(
            client=FacebookClient(app.apptype.get_system_access_token(app))
        )
        self.status_use_case = status_use_case or TemplateLibraryStatusUseCase(app)

    def create_library_template_messages_batch(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates multiple library templates in Meta for different languages.

        This method processes a batch of templates across multiple languages:
        1. Initializes all templates with PENDING status
        2. Attempts to create each template in each language via Meta API
        3. Tracks status changes and handles errors
        4. Schedules follow-up sync for pending templates
        5. Notifies commerce module when all templates are processed

        Args:
            data: Dictionary containing library_templates and languages lists.

        Returns:
            A dictionary containing the template creation status and process message.
        """
        # Get WhatsApp Business Account ID from app configuration
        waba_id = self.app.config["wa_waba_id"]
        templates_status = {}
        has_pending = False

        logger.info(
            f"Starting template batch creation for app {self.app.uuid} with {len(data['library_templates'])} "
            f"templates in {len(data['languages'])} languages"
        )

        # Initialize all templates with PENDING status
        for template_base in data["library_templates"]:
            template_name = template_base["name"]
            templates_status[template_name] = "PENDING"

        # Store initial pending status in Redis
        self.status_use_case.store_pending_templates_status(templates_status)

        # Process each template in each language
        for template_base in data["library_templates"]:
            template_name = template_base["name"]

            for lang in data["languages"]:
                # Create a deep copy to avoid modifying the original template data
                template_data = deepcopy(template_base)
                template_data["language"] = lang

                try:
                    # Call Meta API to create the template
                    response_data = self.service.create_library_template_message(
                        waba_id=waba_id, template_data=template_data
                    )
                    current_status = response_data["status"]

                    # Update template status in Redis
                    self.status_use_case.update_template_status(
                        template_name, current_status
                    )

                    # Track if any template is still pending
                    if current_status == "PENDING":
                        has_pending = True

                    logger.info(
                        f"Template created: name={template_name}, language={lang}, "
                        f"status={current_status} for app {self.app.uuid}"
                    )

                except CustomAPIException as e:
                    # Handle API errors by marking template as ERROR
                    logger.error(
                        f"Error creating template {template_name} (lang={lang}): {str(e)} "
                        f"for app {self.app.uuid}"
                    )
                    self.status_use_case.update_template_status(template_name, "ERROR")
                    has_pending = True

        logger.info(f"Template batch creation completed for app {self.app.uuid}.")

        # Handle post-creation workflow based on template statuses
        if has_pending:
            # Schedule delayed sync for pending templates
            logger.info(
                f"Pending templates detected for app {self.app.uuid}. Scheduling final sync."
            )
            self._schedule_final_sync()
        else:
            # If all templates are immediately approved, sync and notify
            self.status_use_case.sync_templates_from_facebook(self.app)

            final_statuses = self.status_use_case._get_template_statuses_from_redis()
            self.status_use_case.notify_commerce_module(final_statuses)

            logger.info(
                f"All templates approved immediately for app {self.app.uuid}. Commerce module notified."
            )

        # Return creation status summary
        return {
            "message": "Library templates creation process initiated",
            "templates_status": self.status_use_case._get_template_statuses_from_redis(),
        }

    def _schedule_final_sync(self):
        """
        Schedules a final sync task to check pending templates after a defined waiting period.
        """
        countdown = settings.TEMPLATE_LIBRARY_WAIT_TIME_SYNC

        celery_app.send_task(
            name="sync_pending_templates",
            kwargs={"app_uuid": str(self.app.uuid)},
            countdown=countdown,
        )

        logger.info(f"Scheduled final sync task for app {self.app.uuid} in 8 hours.")
