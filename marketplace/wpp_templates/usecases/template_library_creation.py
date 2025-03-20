import logging

from copy import deepcopy

from typing import Dict, Any

from marketplace.applications.models import App

from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import TemplateService


logger = logging.getLogger(__name__)


class TemplateCreationUseCase:
    """
    Handles the creation of multiple library templates and their status tracking.
    """

    def __init__(self, app: App):
        self.app = app
        self.service = TemplateService(
            client=FacebookClient(app.apptype.get_system_access_token(app))
        )
        self.status_use_case = TemplateLibraryStatusUseCase(app)

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

                except Exception as e:
                    logger.error(
                        f"Error creating template {template_data['name']}: {str(e)} for app {self.app.uuid}"
                    )
                    templates_status[template_data["name"]] = "ERROR"
                    has_pending = True

        # If there are pending templates, store their status in Redis and schedule a final sync
        if has_pending:
            self.status_use_case.store_pending_templates_status(templates_status)
            self.status_use_case.schedule_final_sync()
        else:
            # If all templates are approved immediately, notify commerce without using Redis
            self.status_use_case.notify_commerce_module(templates_status)

        return {
            "message": "Library templates creation process initiated",
            "templates_status": templates_status,
        }
