import logging

from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp.tasks import sync_whatsapp_apps
from marketplace.core.types.channels.whatsapp.tasks import sync_whatsapp_cloud_wabas
from marketplace.core.types.channels.whatsapp.tasks import sync_whatsapp_wabas
from marketplace.core.types.channels.whatsapp.tasks import sync_whatsapp_phone_numbers
from marketplace.core.types.channels.whatsapp.tasks import (
    sync_whatsapp_cloud_phone_numbers,
)

from marketplace.applications.models import App

from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)

from unittest.mock import MagicMock

from marketplace.wpp_templates.models import TemplateMessage


User = get_user_model()
logger = logging.getLogger(__name__)


class SyncWhatsAppAppsTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        wpp_type = APPTYPES.get("wpp")
        wpp_cloud_type = APPTYPES.get("wpp-cloud")

        self.wpp_app = wpp_type.create_app(
            config={"auth_token": "12345"},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        self.wpp_cloud_app = wpp_cloud_type.create_app(
            config={},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        return super().setUp()

    def _get_mock_value(
        self, project_uuid: str, flow_object_uuid: str, config: dict = {}
    ) -> list:
        return [
            {
                "uuid": flow_object_uuid,
                "name": "teste",
                "config": config,
                "address": "f234234",
                "project_uuid": project_uuid,
                "is_active": True,
            }
        ]

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_create_new_whatsapp_app(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        list_channel_mock.return_value = self._get_mock_value(
            project_uuid, flow_object_uuid
        )

        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        self.assertTrue(App.objects.filter(flow_object_uuid=flow_object_uuid).exists())
        self.assertTrue(App.objects.filter(project_uuid=project_uuid).exists())

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_update_app_auth_token(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            self.wpp_app.project_uuid,
            self.wpp_app.flow_object_uuid,
            config={"auth_token": "54321"},
        )
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        app = App.objects.get(uuid=self.wpp_app.uuid)
        self.assertEqual(app.config.get("auth_token"), "54321")

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_channel_migration_from_wpp_cloud_to_wpp(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            self.wpp_cloud_app.project_uuid, self.wpp_cloud_app.flow_object_uuid
        )
        mock_redis.return_value = self.redis_mock
        sync_whatsapp_apps()

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_task_that_was_executed(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            self.wpp_cloud_app.project_uuid, self.wpp_cloud_app.flow_object_uuid
        )
        mock_redis.get.return_value = "sync-whatsapp-lock"
        sync_whatsapp_apps()

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_skipping_wpp_demo(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        data = [
            {
                "uuid": self.wpp_app.flow_object_uuid,
                "name": "teste",
                "config": {"address": "558231420933"},
                "address": "558231420933",
                "project_uuid": self.wpp_app.project_uuid,
                "is_active": True,
            }
        ]

        list_channel_mock.return_value = data
        mock_redis.return_value = self.redis_mock
        sync_whatsapp_apps()

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    @patch("marketplace.core.types.channels.whatsapp.tasks.logger")
    def test_skip_channel_with_none_uuid(
        self, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = None

        list_channel_mock.return_value = self._get_mock_value(
            project_uuid, flow_object_uuid
        )

        mock_redis.return_value = self.redis_mock
        sync_whatsapp_apps()
        logger_mock.info.assert_called_with("Skipping channel with None UUID.")

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    @patch("marketplace.core.types.channels.whatsapp.tasks.logger")
    def test_skip_inactive_channel_and_delete_apps(
        self, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = False
        list_channel_mock.return_value = channel_value
        wpp_type = APPTYPES.get("wpp")

        self.wpp_app = wpp_type.create_app(
            config={"auth_token": "12345"},
            project_uuid=project_uuid,
            flow_object_uuid=flow_object_uuid,
            created_by=User.objects.get_admin_user(),
        )
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()
        logger_mock.info.assert_called_with(
            f"Skipping channel {flow_object_uuid} is inactive."
        )

        self.assertFalse(App.objects.filter(flow_object_uuid=flow_object_uuid).exists())

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    @patch("marketplace.core.types.channels.whatsapp.tasks.logger")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES.get")
    def test_app_creation_error(
        self, apptype_mock, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = True

        list_channel_mock.return_value = channel_value

        apptype_mock.return_value.create_app.side_effect = Exception()
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        logger_mock.error.assert_called_with(
            "An error occurred while creating the app: "
        )

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_skip_inactive_channel_and_delete_apps_with_templates(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = False
        list_channel_mock.return_value = channel_value
        wpp_type = APPTYPES.get("wpp")

        self.wpp_app = wpp_type.create_app(
            config={"auth_token": "12345"},
            project_uuid=project_uuid,
            flow_object_uuid=flow_object_uuid,
            created_by=User.objects.get_admin_user(),
        )
        TemplateMessage.objects.create(
            app=self.wpp_app,
            name="TestTemplate",
            created_by=User.objects.get_admin_user(),
        )

        app_template_count = self.wpp_app.template.all().count()
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        app_template_after_task = self.wpp_app.template.all().count()
        self.assertNotEqual(app_template_count, app_template_after_task)

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    @patch("marketplace.core.types.channels.whatsapp.tasks.logger")
    @patch("django.db.models.query.QuerySet.delete", Exception)
    def test_skip_inactive_channel_and_delete_exception(
        self, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = False
        list_channel_mock.return_value = channel_value
        wpp_type = APPTYPES.get("wpp")

        self.wpp_app = wpp_type.create_app(
            config={"auth_token": "12345"},
            project_uuid=project_uuid,
            flow_object_uuid=flow_object_uuid,
            created_by=User.objects.get_admin_user(),
        )
        TemplateMessage.objects.create(
            app=self.wpp_app,
            name="TestTemplate",
            created_by=User.objects.get_admin_user(),
        )

        app_template_count = self.wpp_app.template.all().count()
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        app_template_after_task = self.wpp_app.template.all().count()
        self.assertIn(
            "Cannot delete some instances of model", str(logger_mock.error.call_args)
        )
        self.assertEqual(app_template_count, app_template_after_task)


class SyncWhatsappCloudWabaViewTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        self.type = APPTYPES.get("wpp-cloud")

        return super().setUp()

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_cloud_wabas_without_waba_id(self, mock_redis, apptypes_mock):
        mock_redis.return_value = self.redis_mock

        mock_app = MagicMock()
        mock_app.uuid = uuid4()
        mock_app.config = {
            "fb_access_token": "1234-5678-90",
            "fb_business_id": "1234-5678-90",
        }

        apptypes_mock.get.return_value = MagicMock(apps=[mock_app])
        sync_whatsapp_cloud_wabas()

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_cloud_wabas(
        self, mock_redis, apptypes_mock, facebook_waba_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {"wa_waba_id": "0123456789"}
        wpp_cloud_type = APPTYPES.get("wpp-cloud")

        app = wpp_cloud_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        before_config = app.config.copy()

        apptypes_mock.get.return_value = MagicMock(apps=[app])

        facebook_waba_api_mock.return_value = MagicMock(get_waba=lambda x: "0123456789")
        sync_whatsapp_cloud_wabas()
        self.assertNotEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_cloud_wabas_with_exception(
        self, mock_redis, apptypes_mock, facebook_waba_api_mock
    ):
        mock_redis.return_value = self.redis_mock
        data = {"wa_waba_id": "0123456789"}
        wpp_cloud_type = self.type

        app = wpp_cloud_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        before_config = app.config.copy()

        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_waba_api_mock.return_value.get_waba.side_effect = FacebookApiException(
            "Something wrong"
        )

        sync_whatsapp_cloud_wabas()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    def test_skipp_synced_whatsapp_cloud_app(
        self, facebook_waba_api_mock, apptypes_mock, redis_mock
    ):
        redis = redis_mock.return_value
        redis.ttl.return_value = timedelta(hours=1).seconds

        data = {"wa_waba_id": "0123456789", "waba": "0123456789"}
        wpp_cloud_type = self.type
        app = wpp_cloud_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        key = f"wpp:{app.uuid}"
        redis.set(key, "synced", timedelta(minutes=30).seconds)

        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_waba_api_mock.return_value = MagicMock(get_waba=lambda x: "0123456789")

        sync_whatsapp_cloud_wabas()
        # Simulates situation where the application has already been synchronized
        self.assertEqual(before_config, app.config)


class SyncWhatsappWabaViewTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        self.type = APPTYPES.get("wpp")

        return super().setUp()

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_wabas_without_access_token(self, mock_redis, apptypes_mock):
        mock_redis.return_value = self.redis_mock

        mock_app = MagicMock()
        mock_app.uuid = uuid4()
        mock_app.config = {
            "fb_business_id": "1234-5678-90",
        }

        apptypes_mock.get.return_value = MagicMock(apps=[mock_app])
        sync_whatsapp_wabas()

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_wabas_without_business_id(self, mock_redis, apptypes_mock):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "1234-5678-90",
        }
        wpp_type = self.type
        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()

        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_wabas()
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_wabas_success(
        self, mock_redis, apptypes_mock, facebook_waba_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_waba_api_mock.return_value = MagicMock(get_waba=lambda x: "0123456789")
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_wabas()
        # Assert the app has modifiedy after runing sync task
        self.assertNotEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_wabas_with_exception(
        self, mock_redis, apptypes_mock, facebook_waba_api_mock
    ):
        mock_redis.return_value = self.redis_mock
        data = {
            "wa_waba_id": "0123456789",
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        before_config = app.config.copy()

        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_waba_api_mock.return_value.get_waba.side_effect = FacebookApiException(
            "Something wrong"
        )

        sync_whatsapp_wabas()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookWABAApi")
    def test_skip_synced_whatsapp_app(
        self, facebook_waba_api_mock, apptypes_mock, redis_mock
    ):
        redis = redis_mock.return_value
        redis.ttl.return_value = timedelta(hours=1).seconds

        data = {
            "wa_waba_id": "0123456789",
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
        }
        wpp_type = self.type
        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        key = f"wpp:{app.uuid}"
        redis.set(key, "synced", timedelta(minutes=30).seconds)

        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_waba_api_mock.return_value = MagicMock(get_waba=lambda x: "0123456789")

        sync_whatsapp_wabas()
        # Simulates situation where the application has already been synchronized
        self.assertEqual(before_config, app.config)


class SyncWhatsappPhoneNumberViewTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        self.type = APPTYPES.get("wpp")

        return super().setUp()

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_success(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
            "phone_number": {"id": "0123456789"},
        }

        phone_number_data = {
            "id": "0123456789",
            "display_phone_number": "+5584999999999",
            "verified_name": "Verified Name Mock Test",
            "cert_status": "Status Mock Test",
            "certificate": "Certificate Mock Test",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_get_phone_number_api_mock.return_value = MagicMock(
            get_phone_number=lambda x: phone_number_data
        )
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_phone_numbers()
        # Assert the app has modifiedy after runing sync task
        self.assertNotEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_without_access_token(
        self, mock_redis, apptypes_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_business_id": "0123456789",
            "phone_number": {"id": "0123456789"},
        }

        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_without_business(
        self, mock_redis, apptypes_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "phone_number": {"id": "0123456789"},
        }

        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_with_title_success(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
            "title": "+5584999999999",
        }

        phone_number_data = {
            "id": "0123456789",
            "display_phone_number": "+5584999999999",
            "verified_name": "Verified Name Mock Test",
            "cert_status": "Status Mock Test",
            "certificate": "Certificate Mock Test",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_get_phone_number_api_mock.return_value = MagicMock(
            get_phone_numbers=lambda x: [phone_number_data]
        )
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_phone_numbers()
        # Assert the app has modifiedy after runing sync task
        self.assertNotEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_with_exception(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
            "phone_number": {"id": "0123456789"},
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_get_phone_number_api_mock.return_value.get_phone_number.side_effect = (
            FacebookApiException("Something wrong")
        )

        sync_whatsapp_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_whatsapp_phone_number_with_parse_exception(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
            "title": "+invalid test",
        }

        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    def test_skipp_sync_whatsapp_phone_number(
        self, facebook_get_phone_number_api_mock, apptypes_mock, mock_redis
    ):
        redis = mock_redis.return_value
        redis.ttl.return_value = timedelta(hours=1).seconds

        data = {
            "fb_access_token": "0123456789",
            "fb_business_id": "0123456789",
            "phone_number": {"id": "0123456789"},
        }

        phone_number_data = {
            "id": "0123456789",
            "display_phone_number": "+5584999999999",
            "verified_name": "Verified Name Mock Test",
            "cert_status": "Status Mock Test",
            "certificate": "Certificate Mock Test",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_get_phone_number_api_mock.return_value = MagicMock(
            get_phone_number=lambda x: phone_number_data
        )
        apptypes_mock.get.return_value = MagicMock(apps=[app])

        key = f"sync-whatsapp-phone-number-lock-app:{app.uuid}"
        redis.set(key, "synced", timedelta(minutes=30).seconds)

        sync_whatsapp_phone_numbers()

        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)


class SyncWhatsappCloudPhoneNumberViewTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        self.type = APPTYPES.get("wpp-cloud")

        return super().setUp()

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_wpp_cloud_phone_number_success(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "wa_phone_number_id": "0123456789",
        }
        phone_number_data = {
            "id": "0123456789",
            "display_phone_number": "+5584999999999",
            "verified_name": "Verified Name Mock Test",
            "cert_status": "Status Mock Test",
            "certificate": "Certificate Mock Test",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_get_phone_number_api_mock.return_value = MagicMock(
            get_phone_number=lambda x: phone_number_data
        )
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_cloud_phone_numbers()
        # Assert the app has modifiedy after runing sync task
        self.assertNotEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_wpp_cloud_phone_number_without_phone_number_id(
        self, mock_redis, apptypes_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {}

        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        sync_whatsapp_cloud_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    def test_sync_wpp_cloud_phone_number_with_exception(
        self, mock_redis, apptypes_mock, facebook_get_phone_number_api_mock
    ):
        mock_redis.return_value = self.redis_mock

        data = {
            "wa_phone_number_id": "0123456789",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        apptypes_mock.get.return_value = MagicMock(apps=[app])
        facebook_get_phone_number_api_mock.return_value.get_phone_number.side_effect = (
            FacebookApiException("Something wrong")
        )

        sync_whatsapp_cloud_phone_numbers()
        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.core.types.channels.whatsapp.tasks.APPTYPES")
    @patch("marketplace.core.types.channels.whatsapp.tasks.FacebookPhoneNumbersAPI")
    def test_skipp_sync_wpp_cloud_phone_number(
        self, facebook_get_phone_number_api_mock, apptypes_mock, mock_redis
    ):
        redis = mock_redis.return_value
        redis.ttl.return_value = timedelta(hours=1).seconds

        data = {
            "wa_phone_number_id": "0123456789",
        }

        phone_number_data = {
            "id": "0123456789",
            "display_phone_number": "+5584999999999",
            "verified_name": "Verified Name Mock Test",
            "cert_status": "Status Mock Test",
            "certificate": "Certificate Mock Test",
        }
        wpp_type = self.type

        app = wpp_type.create_app(
            config=data,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )
        before_config = app.config.copy()
        facebook_get_phone_number_api_mock.return_value = MagicMock(
            get_phone_number=lambda x: phone_number_data
        )
        apptypes_mock.get.return_value = MagicMock(apps=[app])

        key = f"sync-whatsapp-phone-number-lock-app:{app.uuid}"
        redis.set(key, "synced", timedelta(minutes=30).seconds)

        sync_whatsapp_cloud_phone_numbers()

        # Assert the app has not modifiedy after runing sync task
        self.assertEqual(before_config, app.config)
