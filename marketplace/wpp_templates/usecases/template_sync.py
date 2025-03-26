import logging

from marketplace.clients.flows.client import FlowsClient
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import TemplateService
from marketplace.wpp_templates.models import (
    TemplateButton,
    TemplateHeader,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.error_handlers import handle_error_and_update_config


logger = logging.getLogger(__name__)


class TemplateSyncUseCase:
    """
    Use case for synchronizing WhatsApp templates between Meta platform and the application.

    This class handles fetching templates from Meta's API, updating local database records,
    and cleaning up templates that no longer exist on Meta's platform.
    """

    def __init__(self, app):
        """
        Initialize the template sync use case.

        Args:
            app: The application instance to sync templates for
        """
        self.app = app
        try:
            access_token = app.apptype.get_access_token(app)
            self.template_service = TemplateService(client=FacebookClient(access_token))
        except ValueError as e:
            logger.error(f"Access token error for app {app.uuid}: {str(e)}")
            raise

        self.flows_client = FlowsClient()

    def sync_templates(self):
        """
        Synchronize templates from Meta's platform to the local database.

        This method fetches all templates from Meta's API, updates the flows service,
        and creates or updates local database records for each template.
        """
        waba_id = (
            self.app.config.get("waba").get("id")
            if self.app.config.get("waba")
            else self.app.config.get("wa_waba_id")
        )

        templates = self.template_service.list_template_messages(waba_id)

        if templates.get("error"):
            template_error = templates["error"]
            logger.error(
                f"A error occurred with waba_id: {waba_id}. \nThe error was:  {template_error}\n"
            )
            handle_error_and_update_config(self.app, template_error)
            return

        templates = templates.get("data", [])
        try:
            logger.info(f"Sending templates to flows for app {self.app.uuid}")
            self.flows_client.update_facebook_templates(
                str(self.app.flow_object_uuid), templates
            )
        except Exception as error:
            logger.error(
                f"An error occurred when sending facebook templates to flows: "
                f"App-{str(self.app.uuid)}, flows_object_uuid: {str(self.app.flow_object_uuid)} "
                f"Error: {error}"
            )

        if waba_id:
            self._delete_unexistent_translations(templates)

        for template in templates:
            try:
                logger.info(
                    f"Processing template: {template.get('name')} for app {self.app.uuid}"
                )
                translation = TemplateTranslation.objects.filter(
                    message_template_id=template.get("id"), template__app=self.app
                )
                if translation:
                    logger.info(
                        f"Found existing translation for template: {template.get('name')}"
                    )
                    translation = translation.last()
                    found_template = translation.template
                else:
                    logger.info(
                        f"Creating new template record for: {template.get('name')}"
                    )
                    found_template, _created = TemplateMessage.objects.get_or_create(
                        app=self.app,
                        name=template.get("name"),
                    )

                found_template.category = template.get("category")
                found_template.save()
                logger.info(
                    f"Template {found_template.name} saved with category: {found_template.category}"
                )

                body = ""
                footer = ""
                for translation in template.get("components"):
                    if translation.get("type") == "BODY":
                        body = translation.get("text", "")

                    if translation.get("type") == "FOOTER":
                        footer = translation.get("text", "")

                logger.info(
                    f"Creating/updating translation for template: {found_template.name} "
                    f"in language: {template.get('language')}"
                )
                (
                    returned_translation,
                    _created,
                ) = TemplateTranslation.objects.get_or_create(
                    template=found_template,
                    language=template.get("language"),
                )
                returned_translation.body = body
                returned_translation.footer = footer
                returned_translation.status = template.get("status")
                returned_translation.variable_count = 0
                returned_translation.message_template_id = template.get("id")
                returned_translation.save()
                logger.info(
                    f"Translation saved with status: {returned_translation.status} and "
                    f"ID: {returned_translation.message_template_id}"
                )

                for translation in template.get("components"):
                    if translation.get("type") == "HEADER":
                        logger.info(
                            f"Processing header component for template: {found_template.name}"
                        )
                        (
                            returned_header,
                            _created,
                        ) = TemplateHeader.objects.get_or_create(
                            translation=returned_translation,
                            header_type=translation.get("format"),
                        )
                        returned_header.text = translation.get("text", {})
                        returned_header.example = translation.get("example", {}).get(
                            "header_handle"
                        )
                        returned_header.save()

                    if translation.get("type") == "BUTTONS":
                        logger.info(
                            f"Processing button components for template: {found_template.name}"
                        )
                        for button in translation.get("buttons"):
                            (
                                _returned_button,
                                _created,
                            ) = TemplateButton.objects.get_or_create(
                                translation=returned_translation,
                                button_type=button.get("type"),
                                text=button.get("text"),
                                url=button.get("url"),
                                phone_number=button.get("phone_number"),
                            )

            except Exception as error:
                logger.error(
                    f"Error syncing templates for app {self.app.uuid}: {str(error)}"
                )
                continue

        logger.info(f"Task sync_templates completed for app {str(self.app.uuid)}")

    def _delete_unexistent_translations(self, templates):
        """
        Removes templates and translations that no longer exist in Meta's platform.

        This method compares local database records with the templates fetched from Meta's API
        and removes any templates or translations that are no longer present on Meta's platform.

        Args:
            templates: List of templates from Meta API
        """
        templates_message = self.app.template.all()
        templates_ids = [item["id"] for item in templates]

        for template in templates_message:
            try:
                template_translation = TemplateTranslation.objects.filter(
                    template=template
                )
                if not template_translation:
                    logger.info(f"Removing template without translation: {template}")
                    template.delete()
                    continue

                for translation in template_translation:
                    if translation.message_template_id not in templates_ids:
                        translation_language = (
                            translation.language
                            if translation.language
                            else "No language"
                        )
                        logger.info(
                            f"Removing translation {translation.message_template_id}: {translation_language}"
                        )
                        translation.delete()

                if template.translations.all().count() == 0:
                    template_name = template.name if template.name else "No name"
                    logger.info(
                        f"Removing template:{template_name} after removing translations"
                    )
                    template.delete()

            except Exception as e:
                logger.error(f"An error occurred during template cleanup: {e}")
                continue
