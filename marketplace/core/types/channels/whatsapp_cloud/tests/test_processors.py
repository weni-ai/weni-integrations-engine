import logging
import uuid
from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.processors import (
    AccountUpdateWebhookEventProcessor,
)

User = get_user_model()


class AccountUpdateWebhookEventProcessorTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.get_admin_user()
        self.project_uuid = str(uuid.uuid4())
        self.waba_id = "123456789"

        # Create test apps
        self.app1 = App.objects.create(
            code="wpp-cloud",
            config={"wa_waba_id": self.waba_id},
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.app2 = App.objects.create(
            code="wpp-cloud",
            config={"wa_waba_id": self.waba_id},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        # Mock logger
        self.mock_logger = Mock(spec=logging.Logger)

        # Create processor instance
        self.processor = AccountUpdateWebhookEventProcessor(logger=self.mock_logger)

    def test_init_with_logger(self):
        """Test initialization with custom logger"""
        custom_logger = Mock(spec=logging.Logger)
        processor = AccountUpdateWebhookEventProcessor(logger=custom_logger)

        self.assertEqual(processor.logger, custom_logger)

    def test_init_without_logger(self):
        """Test initialization without logger uses default logger"""
        processor = AccountUpdateWebhookEventProcessor()

        self.assertIsInstance(processor.logger, logging.Logger)
        self.assertEqual(
            processor.logger.name,
            "marketplace.core.types.channels.whatsapp_cloud.processors",
        )

    def test_get_apps_by_waba_id_returns_matching_apps(self):
        """Test get_apps_by_waba_id returns apps with matching waba_id"""
        apps = self.processor.get_apps_by_waba_id(self.waba_id)

        self.assertEqual(apps.count(), 2)
        self.assertIn(self.app1, apps)
        self.assertIn(self.app2, apps)

    def test_get_apps_by_waba_id_returns_empty_for_non_matching(self):
        """Test get_apps_by_waba_id returns empty queryset for non-matching waba_id"""
        apps = self.processor.get_apps_by_waba_id("non_existent_waba")

        self.assertEqual(apps.count(), 0)

    def test_process_account_update_success(self):
        """Test successful account update processing"""
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        webhook = {"test": "data"}

        self.processor.process_account_update(self.waba_id, value, webhook)

        # Verify apps were updated
        self.app1.refresh_from_db()
        self.app2.refresh_from_db()

        self.assertEqual(self.app1.config["mmlite_status"], "active")
        self.assertEqual(self.app2.config["mmlite_status"], "active")

    def test_process_account_update_no_apps_found(self):
        """Test process_account_update when no apps are found"""
        non_existent_waba = "non_existent_waba"
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        webhook = {"test": "data"}

        self.processor.process_account_update(non_existent_waba, value, webhook)

        # Verify logger was called with appropriate message
        self.mock_logger.info.assert_called_once_with(
            f"There are no applications linked to waba: {non_existent_waba}"
        )

    def test_process_account_update_missing_event(self):
        """Test process_account_update when event is missing"""
        value = {}
        webhook = {"test": "data"}

        self.processor.process_account_update(self.waba_id, value, webhook)

        # Verify logger was called with appropriate message
        self.mock_logger.info.assert_called_once_with(
            f"Event type not found in webhook data: {webhook}"
        )

        # Verify apps were not updated
        self.app1.refresh_from_db()
        self.app2.refresh_from_db()

        self.assertNotIn("mmlite_status", self.app1.config)
        self.assertNotIn("mmlite_status", self.app2.config)

    def test_process_account_update_unsupported_event(self):
        """Test process_account_update with unsupported event"""
        value = {"event": "OTHER_EVENT"}
        webhook = {"test": "data"}

        self.processor.process_account_update(self.waba_id, value, webhook)

        # Verify apps were not updated
        self.app1.refresh_from_db()
        self.app2.refresh_from_db()

        self.assertNotIn("mmlite_status", self.app1.config)
        self.assertNotIn("mmlite_status", self.app2.config)

    def test_process_account_update_existing_config_preserved(self):
        """Test process_account_update preserves existing config"""
        # Set existing config
        self.app1.config["existing_key"] = "existing_value"
        self.app1.save()

        value = {"event": "MM_LITE_TERMS_SIGNED"}
        webhook = {"test": "data"}

        self.processor.process_account_update(self.waba_id, value, webhook)

        # Verify existing config is preserved and new config is added
        self.app1.refresh_from_db()

        self.assertEqual(self.app1.config["existing_key"], "existing_value")
        self.assertEqual(self.app1.config["mmlite_status"], "active")

    def test_process_event_with_account_update(self):
        """Test process_event calls process_account_update for account_update events"""
        waba_id = self.waba_id
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        event_type = "account_update"
        webhook = {"test": "data"}

        with patch.object(self.processor, "process_account_update") as mock_process:
            self.processor.process_event(waba_id, value, event_type, webhook)

            mock_process.assert_called_once_with(waba_id, value, webhook)

    def test_process_event_with_other_event_type(self):
        """Test process_event ignores non-account_update events"""
        waba_id = self.waba_id
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        event_type = "other_event"
        webhook = {"test": "data"}

        with patch.object(self.processor, "process_account_update") as mock_process:
            self.processor.process_event(waba_id, value, event_type, webhook)

            mock_process.assert_not_called()

    def test_process_event_with_empty_event_type(self):
        """Test process_event ignores empty event types"""
        waba_id = self.waba_id
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        event_type = ""
        webhook = {"test": "data"}

        with patch.object(self.processor, "process_account_update") as mock_process:
            self.processor.process_event(waba_id, value, event_type, webhook)

            mock_process.assert_not_called()

    def test_process_event_with_none_event_type(self):
        """Test process_event ignores None event types"""
        waba_id = self.waba_id
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        event_type = None
        webhook = {"test": "data"}

        with patch.object(self.processor, "process_account_update") as mock_process:
            self.processor.process_event(waba_id, value, event_type, webhook)

            mock_process.assert_not_called()

    def test_get_apps_by_waba_id_with_different_config_structures(self):
        """Test get_apps_by_waba_id with different config structures"""
        # Create app with nested waba_id
        app3 = App.objects.create(
            code="wpp-cloud",
            config={"nested": {"wa_waba_id": self.waba_id}},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        # Create app without waba_id
        app4 = App.objects.create(
            code="wpp-cloud",
            config={"other_field": "value"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        apps = self.processor.get_apps_by_waba_id(self.waba_id)

        # Should only return apps with direct wa_waba_id match
        self.assertEqual(apps.count(), 2)
        self.assertIn(self.app1, apps)
        self.assertIn(self.app2, apps)
        self.assertNotIn(app3, apps)
        self.assertNotIn(app4, apps)
