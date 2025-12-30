from unittest.mock import MagicMock, patch, call
from django.test import TestCase

from marketplace.wpp_templates.usecases.template_library_creation import (
    TemplateCreationUseCase,
)
from marketplace.clients.exceptions import CustomAPIException


class TestTemplateCreationUseCase(TestCase):
    """Unit tests for TemplateCreationUseCase using dependency injection and mocks."""

    def setUp(self):
        """Prepare a fake app and the injectable services for each test."""
        self.app = MagicMock()
        self.app.uuid = "app-uuid-123"
        self.app.config = {"wa_waba_id": "waba-123"}

        self.mock_service = MagicMock()
        self.mock_status_use_case = MagicMock()
        self.mock_commerce_service = MagicMock()

        self.uc = TemplateCreationUseCase(
            app=self.app,
            service=self.mock_service,
            status_use_case=self.mock_status_use_case,
            commerce_service=self.mock_commerce_service,
        )

    def test_create_library_template_messages_batch_with_pending(self):
        """Batch creation: any PENDING status triggers schedule_final_sync."""
        data = {
            "library_templates": [{"name": "welcome"}],
            "languages": ["en", "pt_BR"],
        }

        self.uc._create_and_save_local_template = MagicMock(
            return_value={"status": "PENDING"}
        )
        self.uc._schedule_final_sync = MagicMock()

        # Mock Redis status fetch to return the map used in response
        self.mock_status_use_case._get_template_statuses_from_redis.return_value = {
            "welcome": "PENDING"
        }

        result = self.uc.create_library_template_messages_batch(data)

        self.mock_status_use_case.store_pending_templates_status.assert_called_once_with(
            {"welcome": "PENDING"}
        )
        # Updated once per language
        self.assertEqual(self.mock_status_use_case.update_template_status.call_count, 2)
        self.uc._schedule_final_sync.assert_called_once()
        self.assertEqual(
            result,
            {
                "message": "Library templates creation process initiated",
                "templates_status": {"welcome": "PENDING"},
            },
        )

    def test_create_library_template_messages_batch_all_approved(self):
        """Batch creation: all APPROVED triggers immediate sync and notify."""
        data = {
            "library_templates": [{"name": "promo"}],
            "languages": ["es"],
        }

        self.uc._create_and_save_local_template = MagicMock(
            return_value={"status": "APPROVED"}
        )
        self.mock_status_use_case._get_template_statuses_from_redis.return_value = {
            "promo": "APPROVED"
        }

        result = self.uc.create_library_template_messages_batch(data)

        self.mock_status_use_case.sync_templates_from_facebook.assert_called_once_with(
            self.app
        )
        self.mock_status_use_case.notify_commerce_module.assert_called_once_with(
            {"promo": "APPROVED"}
        )
        self.assertEqual(
            result,
            {
                "message": "Library templates creation process initiated",
                "templates_status": {"promo": "APPROVED"},
            },
        )

    def test_create_library_template_messages_batch_exception_marks_error(self):
        """Batch creation: CustomAPIException marks template as ERROR and schedules sync."""
        data = {"library_templates": [{"name": "error_t"}], "languages": ["en"]}

        def _raise(*args, **kwargs):
            raise CustomAPIException("boom", status_code=400)

        self.uc._create_and_save_local_template = MagicMock(side_effect=_raise)
        self.uc._schedule_final_sync = MagicMock()

        self.uc.create_library_template_messages_batch(data)

        self.mock_status_use_case.update_template_status.assert_called_once_with(
            "error_t", "ERROR"
        )
        self.uc._schedule_final_sync.assert_called_once()

    def test_create_library_template_single_without_gallery(self):
        """Single creation: calls service and persists, no gallery flow."""
        template_data = {"name": "single", "language": "en_US"}
        response_data = {"id": "mtpl-1", "status": "PENDING"}

        self.mock_service.create_library_template_message.return_value = response_data
        self.uc._save_template_in_db = MagicMock(return_value=MagicMock())

        result = self.uc.create_library_template_single(template_data.copy())

        self.mock_service.create_library_template_message.assert_called_once()
        # Ensure we passed the original input fields (without gallery in this case)
        self.uc._save_template_in_db.assert_called_once_with(
            template_data, response_data
        )
        self.assertEqual(
            result,
            {
                "message": "Template created successfully.",
                "template_response": response_data,
            },
        )

    def test_create_library_template_single_with_gallery_approved(self):
        """Single creation: with gallery_version and APPROVED triggers commerce call."""
        translation_mock = MagicMock()
        translation_mock.language = "pt_BR"
        translation_mock.template.name = "gallery_tpl"

        template_data = {
            "name": "gallery_tpl",
            "language": "pt_BR",
            "gallery_version": "gv-123",
        }
        response_data = {"id": "mtpl-2", "status": "APPROVED"}

        self.mock_service.create_library_template_message.return_value = response_data
        self.uc._save_template_in_db = MagicMock(return_value=translation_mock)

        self.uc.create_library_template_single(template_data.copy())

        # Gallery version must be assigned and saved
        self.assertEqual(translation_mock.template.gallery_version, "gv-123")
        translation_mock.template.save.assert_called_once()
        # Commerce notification
        self.mock_commerce_service.send_gallery_template_version.assert_called_once_with(
            gallery_version_uuid="gv-123", status="APPROVED"
        )

    def test_create_library_template_single_with_gallery_pending(self):
        """Single creation: with gallery_version and PENDING must not notify commerce."""
        translation_mock = MagicMock()
        translation_mock.language = "en"
        translation_mock.template.name = "t"

        template_data = {"name": "t", "language": "en", "gallery_version": "gv-9"}
        response_data = {"id": "mtpl-3", "status": "PENDING"}

        self.mock_service.create_library_template_message.return_value = response_data
        self.uc._save_template_in_db = MagicMock(return_value=translation_mock)

        self.uc.create_library_template_single(template_data.copy())

        self.mock_commerce_service.send_gallery_template_version.assert_not_called()

    @patch("marketplace.wpp_templates.usecases.template_library_creation.logger")
    def test_create_library_template_single_with_gallery_approved_commerce_error(
        self, mock_logger
    ):
        """Single creation: with gallery_version APPROVED and Commerce error logs exception."""
        translation_mock = MagicMock()
        translation_mock.language = "pt_BR"
        translation_mock.template.name = "tpl"

        template_data = {
            "name": "tpl",
            "language": "pt_BR",
            "gallery_version": "gv-err",
        }
        response_data = {"id": "mtpl-err", "status": "APPROVED"}

        self.mock_service.create_library_template_message.return_value = response_data
        self.uc._save_template_in_db = MagicMock(return_value=translation_mock)
        self.mock_commerce_service.send_gallery_template_version.side_effect = (
            Exception("boom")
        )

        # Should not raise; error is handled and logged
        self.uc.create_library_template_single(template_data.copy())

        self.mock_commerce_service.send_gallery_template_version.assert_called_once_with(
            gallery_version_uuid="gv-err", status="APPROVED"
        )
        mock_logger.error.assert_called()

    @patch("marketplace.wpp_templates.usecases.template_library_creation.celery_app")
    @patch("marketplace.wpp_templates.usecases.template_library_creation.settings")
    def test_schedule_final_sync(self, mock_settings, mock_celery):
        """Schedule final sync uses countdown from settings and calls send_task."""
        mock_settings.TEMPLATE_LIBRARY_WAIT_TIME_SYNC = 42

        self.uc._schedule_final_sync()

        mock_celery.send_task.assert_called_once_with(
            name="sync_pending_templates",
            kwargs={"app_uuid": str(self.app.uuid)},
            countdown=42,
        )

    def test_create_and_save_local_template_calls(self):
        """create_and_save_local_template calls service and persister and returns response."""
        response_data = {"id": "mtpl-4", "status": "APPROVED"}
        self.mock_service.create_library_template_message.return_value = response_data
        self.uc._save_template_in_db = MagicMock(return_value=MagicMock())

        out = self.uc._create_and_save_local_template(
            "waba-1", {"name": "x", "language": "es"}
        )

        self.mock_service.create_library_template_message.assert_called_once_with(
            waba_id="waba-1", template_data={"name": "x", "language": "es"}
        )
        self.uc._save_template_in_db.assert_called_once_with(
            {"name": "x", "language": "es"}, response_data
        )
        self.assertEqual(out, response_data)

    @patch(
        "marketplace.wpp_templates.usecases.template_library_creation.TemplateButton"
    )
    @patch(
        "marketplace.wpp_templates.usecases.template_library_creation.TemplateTranslation"
    )
    @patch(
        "marketplace.wpp_templates.usecases.template_library_creation.TemplateMessage"
    )
    def test_save_template_in_db_persists_and_creates_buttons(
        self, mock_template_message, mock_template_translation, mock_template_button
    ):
        """_save_template_in_db persists TemplateMessage, TemplateTranslation and creates buttons."""
        # Arrange model managers
        template_obj = MagicMock()
        translation_obj = MagicMock()

        mock_template_message.objects.get_or_create.return_value = (template_obj, True)
        mock_template_translation.objects.get_or_create.return_value = (
            translation_obj,
            True,
        )

        # Prepare inputs
        template_data = {
            "name": "persist_tpl",
            "language": "pt_BR",
            "library_template_button_inputs": [
                {
                    "type": "URL",
                    "url": {"base_url": "https://ex.com/x", "url_suffix_example": "1"},
                },
                {"type": "QUICK_REPLY", "text": "Ok"},
            ],
        }
        response_data = {
            "id": "mtpl-5",
            "status": "APPROVED",
            "category": "MARKETING",
        }

        # Execute
        out = self.uc._save_template_in_db(template_data, response_data)

        # TemplateMessage get_or_create with defaults and update category
        mock_template_message.objects.get_or_create.assert_called_once()
        template_obj.save.assert_called()

        # TemplateTranslation get_or_create and updates
        mock_template_translation.objects.get_or_create.assert_called_once()
        self.assertEqual(translation_obj.status, "APPROVED")
        self.assertEqual(translation_obj.message_template_id, "mtpl-5")
        translation_obj.save.assert_called()

        # Buttons created for each button input
        self.assertEqual(mock_template_button.objects.get_or_create.call_count, 2)
        mock_template_button.objects.get_or_create.assert_has_calls(
            [
                call(
                    translation=translation_obj,
                    button_type="URL",
                    url="https://ex.com/x",
                    example="1",
                    text="",
                    phone_number=None,
                ),
                call(
                    translation=translation_obj,
                    button_type="QUICK_REPLY",
                    url=None,
                    example=None,
                    text="Ok",
                    phone_number=None,
                ),
            ],
            any_order=True,
        )

        # Returns translation
        self.assertIs(out, translation_obj)
