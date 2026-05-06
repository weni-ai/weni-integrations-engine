from uuid import uuid4
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp_cloud.usecases.mmlite_status_sync import (
    SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY,
    SyncMmliteStatusUseCase,
)


User = get_user_model()


class SyncMmliteStatusUseCaseTestCase(TestCase):
    def setUp(self) -> None:
        self.admin_user = User.objects.get_admin_user()
        self.wpp_cloud_type = APPTYPES.get("wpp-cloud")
        self.waba_id = "waba-123"
        self.other_waba_id = "waba-456"

        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        self.business_service_mock = MagicMock()
        self.business_service_factory_mock = MagicMock(
            return_value=self.business_service_mock
        )

        self.flows_client_mock = MagicMock()
        self.flows_client_mock.detail_channel.return_value = {"config": {}}

        return super().setUp()

    def _build_use_case(self) -> SyncMmliteStatusUseCase:
        return SyncMmliteStatusUseCase(
            business_service_factory=self.business_service_factory_mock,
            flows_client=self.flows_client_mock,
            redis_connection=self.redis_mock,
        )

    _UNSET = object()

    def _create_app(
        self,
        waba_id=None,
        mmlite_status=None,
        flow_object_uuid=_UNSET,
        extra_config=None,
    ) -> App:
        config = {}
        if waba_id is not None:
            config["wa_waba_id"] = waba_id
        if mmlite_status is not None:
            config["mmlite_status"] = mmlite_status
        if extra_config:
            config.update(extra_config)

        if flow_object_uuid is self._UNSET:
            flow_object_uuid = uuid4()

        return self.wpp_cloud_type.create_app(
            config=config,
            project_uuid=uuid4(),
            flow_object_uuid=flow_object_uuid,
            created_by=self.admin_user,
        )

    def test_execute_returns_none_when_locked(self):
        self.redis_mock.get.return_value = "1"

        result = self._build_use_case().execute()

        self.assertIsNone(result)
        self.redis_mock.set.assert_not_called()
        self.business_service_factory_mock.assert_not_called()
        self.flows_client_mock.detail_channel.assert_not_called()
        self.flows_client_mock.update_config.assert_not_called()

    def test_execute_acquires_and_releases_lock(self):
        result = self._build_use_case().execute()

        self.assertIsNotNone(result)
        self.redis_mock.set.assert_called_once_with(
            SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY, "1", ex=600
        )
        self.redis_mock.delete.assert_called_once_with(
            SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY
        )

    def test_releases_lock_even_when_grouping_raises(self):
        use_case = self._build_use_case()

        with patch.object(
            use_case, "_group_candidates_by_waba", side_effect=Exception("boom")
        ):
            with self.assertRaises(Exception):
                use_case.execute()

        self.redis_mock.delete.assert_called_once_with(
            SYNC_WHATSAPP_CLOUD_MMLITE_STATUS_LOCK_KEY
        )

    def test_sibling_propagation_with_in_progress_status(self):
        active_app = self._create_app(waba_id=self.waba_id, mmlite_status="active")
        in_progress_app = self._create_app(
            waba_id=self.waba_id, mmlite_status="in_progress"
        )
        self.flows_client_mock.detail_channel.return_value = {
            "config": {"existing_key": "existing_value"}
        }

        summary = self._build_use_case().execute()

        in_progress_app.refresh_from_db()
        active_app.refresh_from_db()

        self.assertEqual(in_progress_app.config["mmlite_status"], "active")
        self.assertEqual(active_app.config["mmlite_status"], "active")

        self.business_service_factory_mock.assert_not_called()
        self.business_service_mock.get_mmlite_status.assert_not_called()

        self.flows_client_mock.detail_channel.assert_called_once_with(
            in_progress_app.flow_object_uuid
        )
        self.flows_client_mock.update_config.assert_called_once_with(
            data={"existing_key": "existing_value", "mmlite": True},
            flow_object_uuid=in_progress_app.flow_object_uuid,
        )
        self.assertEqual(summary["propagated"], 1)
        self.assertEqual(summary["activated_via_meta"], 0)

    def test_sibling_propagation_with_unset_status(self):
        self._create_app(waba_id=self.waba_id, mmlite_status="active")
        unset_app = self._create_app(waba_id=self.waba_id)

        summary = self._build_use_case().execute()

        unset_app.refresh_from_db()
        self.assertEqual(unset_app.config["mmlite_status"], "active")
        self.business_service_mock.get_mmlite_status.assert_not_called()
        self.flows_client_mock.update_config.assert_called_once()
        self.assertEqual(summary["propagated"], 1)

    def test_meta_returns_onboarded_flips_all_apps_in_group(self):
        app1 = self._create_app(waba_id=self.waba_id, mmlite_status="in_progress")
        app2 = self._create_app(waba_id=self.waba_id)

        self.business_service_mock.get_mmlite_status.return_value = {
            "marketing_messages_onboarding_status": "ONBOARDED"
        }

        summary = self._build_use_case().execute()

        app1.refresh_from_db()
        app2.refresh_from_db()
        self.assertEqual(app1.config["mmlite_status"], "active")
        self.assertEqual(app2.config["mmlite_status"], "active")

        self.business_service_factory_mock.assert_called_once()
        self.business_service_mock.get_mmlite_status.assert_called_once_with(
            self.waba_id
        )
        self.assertEqual(self.flows_client_mock.update_config.call_count, 2)
        self.assertEqual(summary["activated_via_meta"], 2)
        self.assertEqual(summary["propagated"], 0)
        self.assertEqual(summary["skipped_not_onboarded"], 0)

    def test_meta_returns_not_onboarded_does_not_flip(self):
        app = self._create_app(waba_id=self.waba_id, mmlite_status="in_progress")
        self.business_service_mock.get_mmlite_status.return_value = {
            "marketing_messages_onboarding_status": "NOT_ONBOARDED"
        }

        summary = self._build_use_case().execute()

        app.refresh_from_db()
        self.assertEqual(app.config["mmlite_status"], "in_progress")
        self.flows_client_mock.update_config.assert_not_called()
        self.assertEqual(summary["skipped_not_onboarded"], 1)
        self.assertEqual(summary["activated_via_meta"], 0)
        self.assertEqual(summary["propagated"], 0)

    def test_meta_call_raises_captures_and_continues(self):
        app_failing = self._create_app(
            waba_id=self.waba_id, mmlite_status="in_progress"
        )
        app_success = self._create_app(
            waba_id=self.other_waba_id, mmlite_status="in_progress"
        )

        def fake_get_status(waba_id):
            if waba_id == self.waba_id:
                raise Exception("meta down")
            return {"marketing_messages_onboarding_status": "ONBOARDED"}

        self.business_service_mock.get_mmlite_status.side_effect = fake_get_status

        with patch(
            "marketplace.core.types.channels.whatsapp_cloud."
            "usecases.mmlite_status_sync.sentry_sdk.capture_exception"
        ) as mock_capture:
            summary = self._build_use_case().execute()

        app_failing.refresh_from_db()
        app_success.refresh_from_db()

        self.assertEqual(app_failing.config["mmlite_status"], "in_progress")
        self.assertEqual(app_success.config["mmlite_status"], "active")
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["activated_via_meta"], 1)
        mock_capture.assert_called_once()

    def test_app_without_flow_object_uuid_is_flipped_without_flows_call(self):
        app = self._create_app(
            waba_id=self.waba_id,
            mmlite_status="in_progress",
            flow_object_uuid=None,
        )
        self.business_service_mock.get_mmlite_status.return_value = {
            "marketing_messages_onboarding_status": "ONBOARDED"
        }

        summary = self._build_use_case().execute()

        app.refresh_from_db()
        self.assertEqual(app.config["mmlite_status"], "active")
        self.flows_client_mock.detail_channel.assert_not_called()
        self.flows_client_mock.update_config.assert_not_called()
        self.assertEqual(summary["activated_via_meta"], 1)

    def test_apps_without_waba_id_are_excluded(self):
        no_waba_app = self._create_app(waba_id=None, mmlite_status="in_progress")
        empty_waba_app = self._create_app(waba_id="", mmlite_status="in_progress")
        active_only_app = self._create_app(waba_id=self.waba_id, mmlite_status="active")

        summary = self._build_use_case().execute()

        no_waba_app.refresh_from_db()
        empty_waba_app.refresh_from_db()
        active_only_app.refresh_from_db()

        self.assertEqual(no_waba_app.config["mmlite_status"], "in_progress")
        self.assertEqual(empty_waba_app.config["mmlite_status"], "in_progress")
        self.assertEqual(active_only_app.config["mmlite_status"], "active")

        self.business_service_mock.get_mmlite_status.assert_not_called()
        self.assertEqual(summary["candidates"], 0)
        self.assertEqual(summary["wabas"], 0)

    def test_dedup_one_meta_call_per_waba(self):
        for _ in range(3):
            self._create_app(waba_id=self.waba_id, mmlite_status="in_progress")

        self.business_service_mock.get_mmlite_status.return_value = {
            "marketing_messages_onboarding_status": "NOT_ONBOARDED"
        }

        summary = self._build_use_case().execute()

        self.assertEqual(self.business_service_mock.get_mmlite_status.call_count, 1)
        self.business_service_mock.get_mmlite_status.assert_called_once_with(
            self.waba_id
        )
        self.assertEqual(summary["candidates"], 3)
        self.assertEqual(summary["wabas"], 1)
        self.assertEqual(summary["skipped_not_onboarded"], 3)

    def test_processes_multiple_wabas_independently(self):
        self._create_app(waba_id=self.waba_id, mmlite_status="in_progress")
        self._create_app(waba_id=self.other_waba_id, mmlite_status="in_progress")

        responses = {
            self.waba_id: {"marketing_messages_onboarding_status": "ONBOARDED"},
            self.other_waba_id: {
                "marketing_messages_onboarding_status": "NOT_ONBOARDED"
            },
        }
        self.business_service_mock.get_mmlite_status.side_effect = (
            lambda waba_id: responses[waba_id]
        )

        summary = self._build_use_case().execute()

        self.assertEqual(summary["wabas"], 2)
        self.assertEqual(summary["activated_via_meta"], 1)
        self.assertEqual(summary["skipped_not_onboarded"], 1)
        self.assertEqual(self.business_service_mock.get_mmlite_status.call_count, 2)

    def test_flows_failure_does_not_revert_local_flip(self):
        app = self._create_app(waba_id=self.waba_id, mmlite_status="in_progress")
        self.business_service_mock.get_mmlite_status.return_value = {
            "marketing_messages_onboarding_status": "ONBOARDED"
        }
        self.flows_client_mock.detail_channel.side_effect = Exception("flows down")

        with patch(
            "marketplace.core.types.channels.whatsapp_cloud."
            "usecases.mmlite_status_sync.sentry_sdk.capture_exception"
        ) as mock_capture:
            summary = self._build_use_case().execute()

        app.refresh_from_db()
        self.assertEqual(app.config["mmlite_status"], "active")
        self.assertEqual(summary["activated_via_meta"], 1)
        self.assertEqual(summary["errors"], 0)
        mock_capture.assert_called_once()

    def test_default_business_service_factory_uses_app_access_token(self):
        app = self._create_app(
            waba_id=self.waba_id,
            mmlite_status="in_progress",
            extra_config={"wa_user_token": "custom-token"},
        )

        with patch(
            "marketplace.core.types.channels.whatsapp_cloud."
            "usecases.mmlite_status_sync.FacebookClient"
        ) as mock_facebook_client_cls, patch(
            "marketplace.core.types.channels.whatsapp_cloud."
            "usecases.mmlite_status_sync.BusinessMetaService"
        ) as mock_business_service_cls:
            mock_business_service_cls.return_value.get_mmlite_status.return_value = {
                "marketing_messages_onboarding_status": "NOT_ONBOARDED"
            }

            use_case = SyncMmliteStatusUseCase(
                flows_client=self.flows_client_mock,
                redis_connection=self.redis_mock,
            )
            use_case.execute()

        mock_facebook_client_cls.assert_called_once_with("custom-token")
        mock_business_service_cls.assert_called_once_with(
            client=mock_facebook_client_cls.return_value
        )
        # ensure the app was fetched (sanity check)
        app.refresh_from_db()
        self.assertEqual(app.config["mmlite_status"], "in_progress")
