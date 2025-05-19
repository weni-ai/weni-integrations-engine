import logging

from copy import deepcopy

from typing import Dict, Any, Optional

from django.conf import settings

from marketplace.applications.models import App

from marketplace.clients.commerce.client import CommerceClient
from marketplace.clients.exceptions import CustomAPIException
from marketplace.services.commerce.service import CommerceService
from marketplace.wpp_templates.models import (
    TemplateButton,
    TemplateMessage,
    TemplateTranslation,
)
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
        commerce_service: Optional[CommerceService] = None,
    ):
        self.app = app
        self.service = service or TemplateService(
            client=FacebookClient(app.apptype.get_system_access_token(app))
        )
        self.commerce_service = commerce_service or CommerceService(CommerceClient())
        self.status_use_case = status_use_case or TemplateLibraryStatusUseCase(app)

    def create_library_template_messages_batch(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates multiple library templates in Meta for different languages.

        This method processes a batch of template messages, creating them in Meta's
        WhatsApp Business API for each specified language. It also updates the local
        database objects and manages status tracking in Redis.

        Args:
            data (Dict[str, Any]): Dictionary containing 'library_templates' list and
                'languages' list. Each template in 'library_templates' should have
                at least a 'name' field and other required template properties.

        Returns:
            Dict[str, Any]: Status information for all processed templates.

        Raises:
            CustomAPIException: If there's an error communicating with Meta's API.
        """
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
                    # Create template in Meta API and save to local database
                    # Returns response with template status (APPROVED, PENDING, etc.)
                    response_data = self._create_and_save_local_template(
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

    def create_library_template_single(
        self, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a single library template and optionally link a gallery version.

        This method performs the following operations:
        - Sends the template to Meta to create a single-language template.
        - Saves the resulting TemplateMessage and TemplateTranslation locally.
        - Optionally associates a gallery_template_version to the template.
        - Notifies Commerce if the status is not 'PENDING' and gallery_version is defined.

        Args:
            template_data (Dict[str, Any]): A dictionary containing template information,
            including an optional 'gallery_version'.

        Returns:
            Dict[str, Any]: A response summary with the creation status.
        """
        waba_id = self.app.config["wa_waba_id"]

        # Extract and remove gallery_version if present
        gallery_version = template_data.pop("gallery_version", None)

        # Send to Meta and persist locally
        response_data = self.service.create_library_template_message(
            waba_id=waba_id,
            template_data=template_data,
        )
        translation = self._save_template_in_db(template_data, response_data)

        # Associate gallery version if defined
        if gallery_version:
            translation.template.gallery_version = gallery_version
            translation.template.save()

            # Notify Commerce if the template is not pending and a gallery version is defined
            status = response_data.get("status")
            if status != "PENDING":
                try:
                    self.commerce_service.send_gallery_template_version(
                        gallery_version_uuid=str(gallery_version),
                        status=response_data["status"],
                    )
                    logger.info(
                        f"[Commerce] Gallery version {gallery_version} for template: {translation.template.name}, "
                        f"translation: {translation.language}, status: {translation.status} sent successfully."
                    )
                except Exception as e:
                    logger.error(
                        f"[Commerce] Failed to send gallery version for template: {translation.template.name}, "
                        f"translation: {translation.language}, status: {translation.status}, error: {e}"
                    )

        return {
            "message": "Template created successfully.",
            "template_response": response_data,
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

        logger.info(
            f"Scheduled final sync task for app {self.app.uuid} in {countdown} seconds."
        )

    def _create_and_save_local_template(
        self, waba_id: str, template_data: dict
    ) -> dict:
        """
        Creates a template on Meta API and saves it to the local database.

        This method performs the following operations:
        1. Calls Meta API to create the template
        2. Saves/updates the local database objects (TemplateMessage, TemplateTranslation, Buttons)

        Args:
            waba_id: The WhatsApp Business Account ID
            template_data: Dictionary containing template configuration

        Returns:
            dict: The Meta API response data
        """
        # Create template on Facebook
        response_data = self.service.create_library_template_message(
            waba_id=waba_id, template_data=template_data
        )
        # Save locally in database
        translation = self._save_template_in_db(template_data, response_data)
        logger.info(
            f"Template created locally: {translation.template.name} (lang={translation.language})"
        )
        return response_data

    def _save_template_in_db(self, template_data: dict, response_data: dict):
        """
        Creates or updates template-related database records.

        This method handles the persistence of template data by creating or updating
        the following database entities:
        - TemplateMessage: The base template record
        - TemplateTranslation: Language-specific version of the template
        - TemplateButton: Interactive buttons associated with the template

        Args:
            template_data: Dictionary containing the template configuration from request
            response_data: Dictionary containing the API response from Meta

        Returns:
            TemplateTranslation: The created or updated template translation object
        """
        template_name = template_data["name"]
        category = response_data.get("category", "UTILITY")
        template_language = template_data["language"]
        message_template_id = response_data["id"]
        button_inputs = template_data.get("library_template_button_inputs", [])
        status = response_data["status"]

        # Create or update TemplateMessage
        found_template, _ = TemplateMessage.objects.get_or_create(
            app=self.app,
            name=template_name,
            defaults={"category": category, "template_type": "TEXT"},
        )
        found_template.category = category
        found_template.save()

        # Create or update TemplateTranslation
        translation, _ = TemplateTranslation.objects.get_or_create(
            template=found_template,
            language=template_language,
            defaults={
                "status": status,
                "message_template_id": message_template_id,
                "body": "",
                "footer": "",
                "variable_count": 0,
                "country": "Brazil",
            },
        )
        translation.status = status
        translation.message_template_id = message_template_id
        translation.save()

        # Create Buttons if any
        for button in button_inputs:
            TemplateButton.objects.get_or_create(
                translation=translation,
                button_type=button["type"],
                url=button["url"]["base_url"] if "url" in button else None,
                example=button["url"].get("url_suffix_example")
                if "url" in button
                else None,
                text=button.get("text", ""),
                phone_number=None,
            )

        return translation
