from uuid import uuid4
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.core.pacing.constants import TTL_WHATSAPP_CLOUD_WABAS
from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp.usecases.waba_sync import WABASyncUseCase


User = get_user_model()

WABA_PAYLOAD = {"id": "waba-123", "name": "Acme", "currency": "USD"}


class WABASyncUseCaseTestCase(TestCase):
    def setUp(self) -> None:
        self.admin_user = User.objects.get_admin_user()
        self.wpp_cloud_type = APPTYPES.get("wpp-cloud")
        self.waba_id = "waba-123"

        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        self.api_mock = MagicMock()
        self.api_mock.get_waba.return_value = WABA_PAYLOAD
        self.api_factory = MagicMock(return_value=self.api_mock)

        return super().setUp()

    def _build_use_case(self, app=None) -> WABASyncUseCase:
        return WABASyncUseCase(
            app=app,
            redis_conn=self.redis_mock,
            api_factory=self.api_factory,
            token_factory=lambda _app: "token",
        )

    def _create_app(self, waba_id=None, extra_config=None, configured=True):
        config = {}
        if waba_id is not None:
            config["wa_waba_id"] = waba_id
        if extra_config:
            config.update(extra_config)

        return self.wpp_cloud_type.create_app(
            config=config,
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=self.admin_user,
            configured=configured,
        )

    def test_sync_waba_fetches_once_and_updates_all_siblings(self):
        app_one = self._create_app(waba_id=self.waba_id)
        app_two = self._create_app(waba_id=self.waba_id)
        other = self._create_app(waba_id="waba-other")

        result = self._build_use_case().sync_waba(self.waba_id)

        self.assertEqual(result["status"], "synced")
        self.assertEqual(result["updated"], 2)
        self.api_mock.get_waba.assert_called_once_with(self.waba_id)

        app_one.refresh_from_db()
        app_two.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(app_one.config["waba"], WABA_PAYLOAD)
        self.assertEqual(app_two.config["waba"], WABA_PAYLOAD)
        self.assertNotIn("waba", other.config)

        self.redis_mock.set.assert_called_once_with(
            TTL_WHATSAPP_CLOUD_WABAS.format(waba_id=self.waba_id),
            "synced",
            ex=settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS,
        )

    def test_sync_waba_skips_ignores_meta_sync_app(self):
        eligible = self._create_app(waba_id=self.waba_id)
        ignored = self._create_app(
            waba_id=self.waba_id, extra_config={"ignores_meta_sync": "err"}
        )

        result = self._build_use_case().sync_waba(self.waba_id)

        self.assertEqual(result["status"], "synced")
        self.assertEqual(result["updated"], 1)
        self.api_mock.get_waba.assert_called_once_with(self.waba_id)

        eligible.refresh_from_db()
        ignored.refresh_from_db()
        self.assertEqual(eligible.config["waba"], WABA_PAYLOAD)
        self.assertNotIn("waba", ignored.config)

    def test_sync_waba_skips_when_no_eligible_apps(self):
        result = self._build_use_case().sync_waba(self.waba_id)

        self.assertEqual(result, {"status": "skipped", "reason": "no_eligible_apps"})
        self.api_mock.get_waba.assert_not_called()
        self.redis_mock.set.assert_not_called()

    def test_sync_waba_does_not_mark_ttl_on_meta_error(self):
        self._create_app(waba_id=self.waba_id)
        self.api_mock.get_waba.side_effect = Exception("graph down")

        result = self._build_use_case().sync_waba(self.waba_id)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "graph down")
        self.redis_mock.set.assert_not_called()

    def test_create_path_copies_sibling_cache_when_ttl_is_fresh(self):
        sibling = self._create_app(
            waba_id=self.waba_id, extra_config={"waba": WABA_PAYLOAD}
        )
        new_app = self._create_app(waba_id=self.waba_id)
        self.redis_mock.get.return_value = b"synced"

        result = self._build_use_case(app=new_app).sync_whatsapp_cloud_waba()

        self.assertEqual(result["status"], "copied")
        self.api_mock.get_waba.assert_not_called()
        new_app.refresh_from_db()
        sibling.refresh_from_db()
        self.assertEqual(new_app.config["waba"], WABA_PAYLOAD)
        self.assertEqual(sibling.config["waba"], WABA_PAYLOAD)

    def test_create_path_fetches_when_ttl_is_stale(self):
        sibling = self._create_app(waba_id=self.waba_id)
        new_app = self._create_app(waba_id=self.waba_id)
        self.redis_mock.get.return_value = None

        result = self._build_use_case(app=new_app).sync_whatsapp_cloud_waba()

        self.assertEqual(result["status"], "synced")
        self.api_mock.get_waba.assert_called_once_with(self.waba_id)
        sibling.refresh_from_db()
        new_app.refresh_from_db()
        self.assertEqual(sibling.config["waba"], WABA_PAYLOAD)
        self.assertEqual(new_app.config["waba"], WABA_PAYLOAD)

    def test_create_path_fetches_when_ttl_is_fresh_but_no_sibling_cache(self):
        new_app = self._create_app(waba_id=self.waba_id)
        self.redis_mock.get.return_value = b"synced"

        result = self._build_use_case(app=new_app).sync_whatsapp_cloud_waba()

        self.assertEqual(result["status"], "synced")
        self.api_mock.get_waba.assert_called_once_with(self.waba_id)
        new_app.refresh_from_db()
        self.assertEqual(new_app.config["waba"], WABA_PAYLOAD)

    def test_create_path_skips_when_wa_waba_id_missing(self):
        app = self._create_app()

        result = self._build_use_case(app=app).sync_whatsapp_cloud_waba()

        self.assertEqual(result, {"status": "skipped", "reason": "missing_wa_waba_id"})
        self.api_mock.get_waba.assert_not_called()

    def test_create_path_skips_ignores_meta_sync(self):
        app = self._create_app(
            waba_id=self.waba_id, extra_config={"ignores_meta_sync": "err"}
        )

        result = self._build_use_case(app=app).sync_whatsapp_cloud_waba()

        self.assertEqual(
            result, {"status": "skipped", "reason": "ignores_meta_sync_flag"}
        )
        self.api_mock.get_waba.assert_not_called()

    def test_create_path_requires_app(self):
        result = self._build_use_case(app=None).sync_whatsapp_cloud_waba()

        self.assertEqual(result, {"status": "error", "error": "app is required"})
        self.api_mock.get_waba.assert_not_called()

    def test_create_path_skips_unusable_siblings_before_copying_cache(self):
        self._create_app(
            waba_id=self.waba_id,
            extra_config={"ignores_meta_sync": "err", "waba": WABA_PAYLOAD},
        )
        self._create_app(waba_id=self.waba_id)
        self._create_app(waba_id=self.waba_id, extra_config={"waba": WABA_PAYLOAD})
        new_app = self._create_app(waba_id=self.waba_id)
        self.redis_mock.get.return_value = b"synced"

        result = self._build_use_case(app=new_app).sync_whatsapp_cloud_waba()

        self.assertEqual(result["status"], "copied")
        self.api_mock.get_waba.assert_not_called()
        new_app.refresh_from_db()
        self.assertEqual(new_app.config["waba"], WABA_PAYLOAD)

    def test_sync_waba_errors_when_no_access_token(self):
        self._create_app(waba_id=self.waba_id)

        result = WABASyncUseCase(
            redis_conn=self.redis_mock,
            api_factory=self.api_factory,
            token_factory=lambda _app: "",
        ).sync_waba(self.waba_id)

        self.assertEqual(result, {"status": "error", "error": "no_access_token"})
        self.api_factory.assert_not_called()
        self.redis_mock.set.assert_not_called()

    def test_sync_waba_skips_apps_without_usable_token(self):
        failing_app = self._create_app(waba_id=self.waba_id)
        empty_token_app = self._create_app(waba_id=self.waba_id)
        good_app = self._create_app(waba_id=self.waba_id)

        def token_factory(app):
            if app.uuid == failing_app.uuid:
                raise Exception("token lookup failed")
            if app.uuid == empty_token_app.uuid:
                return ""
            if app.uuid == good_app.uuid:
                return "token"
            return None

        result = WABASyncUseCase(
            redis_conn=self.redis_mock,
            api_factory=self.api_factory,
            token_factory=token_factory,
        ).sync_waba(self.waba_id)

        self.assertEqual(result["status"], "synced")
        self.api_factory.assert_called_once_with("token")
        self.api_mock.get_waba.assert_called_once_with(self.waba_id)

    def test_default_factories_build_token_and_api(self):
        app = MagicMock()
        app.apptype.get_access_token.return_value = "access-token"

        self.assertEqual(WABASyncUseCase._default_token_factory(app), "access-token")

        with patch(
            "marketplace.core.types.channels.whatsapp.usecases.waba_sync.FacebookWABAApi"
        ) as mock_api:
            WABASyncUseCase._default_api_factory("access-token")
            mock_api.assert_called_once_with("access-token")
