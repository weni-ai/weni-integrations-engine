"""Tests for AccountVerificationView (POST + GET)."""

import json
import uuid
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status

from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    UIState,
    VerificationStatus,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.views import (
    AccountVerificationView,
)


@override_settings(WHATSAPP_BSP_BUSINESS_ID="partner_123")
class AccountVerificationViewTestCase(APIBaseTestCase):
    view_class = AccountVerificationView

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            code="wpp-cloud",
            config={"wa_business_id": "client_456", "wa_waba_id": "waba_999"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

    @property
    def view(self):
        return self.view_class.as_view()

    def _post_documents(self, documents):
        from rest_framework.test import force_authenticate

        url = f"/api/v1/apptypes/wpp-cloud/apps/{self.app.uuid}/account-verification/"
        request = self.request.factory.post(
            url, data={"documents": documents}, format="multipart"
        )
        force_authenticate(request, user=self.user)
        return self.view(request, app_uuid=self.app.uuid)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.account_verification.views.SubmitAccountVerificationUseCase"
    )
    def test_post_submits_and_returns_pending_state(self, use_case_class):
        instance = use_case_class.return_value
        instance.execute.return_value = type(
            "Fake",
            (),
            {
                "to_dict": lambda self: {
                    "ui_state": UIState.PENDING,
                    "status": VerificationStatus.PENDING,
                    "submission_id": None,
                    "verification_attempts": 1,
                    "rejection_reasons": [],
                    "submitted_at": "2026-05-25T17:00:00+00:00",
                    "updated_at_meta": None,
                    "last_synced_at": None,
                    "can_submit": False,
                }
            },
        )()

        document = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4", content_type="application/pdf"
        )
        response = self._post_documents([document])
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = json.loads(response.content)
        self.assertEqual(content["ui_state"], UIState.PENDING)
        self.assertEqual(content["status"], VerificationStatus.PENDING)
        instance.execute.assert_called_once()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.account_verification.views.GetAccountVerificationStatusUseCase"
    )
    def test_get_returns_current_state(self, use_case_class):
        instance = use_case_class.return_value
        instance.execute.return_value = type(
            "Fake",
            (),
            {
                "to_dict": lambda self: {
                    "ui_state": UIState.APPROVED,
                    "status": VerificationStatus.APPROVED,
                    "submission_id": "sub_1",
                    "verification_attempts": 1,
                    "rejection_reasons": [],
                    "submitted_at": "2026-05-25T17:00:00+00:00",
                    "updated_at_meta": "2026-05-25T17:05:00+00:00",
                    "last_synced_at": "2026-05-25T17:05:01+00:00",
                    "can_submit": False,
                }
            },
        )()

        url = f"/api/v1/apptypes/wpp-cloud/apps/{self.app.uuid}/account-verification/"
        response = self.request.get(url, app_uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["ui_state"], UIState.APPROVED)
        instance.execute.assert_called_once_with(app_uuid=str(self.app.uuid))

    def test_post_validates_documents_format(self):
        bad = SimpleUploadedFile("bad.gif", b"GIF89a", content_type="image/gif")
        response = self._post_documents([bad])
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
