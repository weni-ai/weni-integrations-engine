import logging

from datetime import timedelta

from copy import deepcopy

from typing import Dict, Any, Optional

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

        Args:
            data: Dictionary containing library_templates and languages lists.

        Returns:
            A dictionary containing the template creation status.
        """
        waba_id = self.app.config["wa_waba_id"]
        templates_status = {}
        has_pending = False

        logger.info(
            f"Starting template batch creation for app {self.app.uuid} with {len(data['library_templates'])} "
            f"templates in {len(data['languages'])} languages"
        )

        # Iterate over each template and create it for all specified languages
        for template_base in data["library_templates"]:
            for lang in data["languages"]:
                template_data = deepcopy(
                    template_base
                )  # Ensure original data is not modified
                template_data["language"] = lang

                try:
                    # Call the service while keeping the loop logic in the Use Case
                    response_data = self.service.create_library_template_message(
                        waba_id=waba_id, template_data=template_data
                    )

                    # Store the template status (only by name, ignoring language variations)
                    templates_status[template_data["name"]] = response_data["status"]

                    # If any template is in "PENDING" status, mark it
                    if response_data["status"] == "PENDING":
                        has_pending = True

                    logger.info(
                        f"Template created: name={template_data['name']}, language={lang}, "
                        f"status={response_data['status']} for app {self.app.uuid}"
                    )

                except CustomAPIException as e:
                    logger.error(
                        f"Error creating template {template_data['name']}: {str(e)} for app {self.app.uuid}"
                    )
                    templates_status[template_data["name"]] = "ERROR"
                    has_pending = True

        logger.info(
            f"Template batch creation completed for app {self.app.uuid}. Status summary: {templates_status}"
        )

        # If there are pending templates, store their status in Redis and schedule a final sync
        if has_pending:
            self.status_use_case.store_pending_templates_status(templates_status)
            logger.info(
                f"Pending templates detected for app {self.app.uuid}. Scheduled final sync."
            )
            self._schedule_final_sync()
        else:
            # If all templates are approved immediately, notify commerce without using Redis
            self.status_use_case.notify_commerce_module(templates_status)
            logger.info(
                f"All templates approved immediately for app {self.app.uuid}. Commerce module notified."
            )

        return {
            "message": "Library templates creation process initiated",
            "templates_status": templates_status,
        }

    def _schedule_final_sync(self):
        """
        Schedules a final sync task to check pending templates after a defined waiting period.
        """
        countdown = timedelta(hours=8).total_seconds()

        celery_app.send_task(
            name="sync_pending_templates",
            kwargs={"app_uuid": str(self.app.uuid)},
            countdown=countdown,
        )

        logger.info(f"Scheduled final sync task for app {self.app.uuid} in 8 hours.")
