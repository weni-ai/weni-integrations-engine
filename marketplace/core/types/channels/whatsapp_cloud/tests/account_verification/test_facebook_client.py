"""Tests for the BusinessVerificationRequests mixin in FacebookClient."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from marketplace.clients.facebook.client import (
    BusinessVerificationRequests,
    FacebookClient,
)
from marketplace.services.facebook.service import BusinessVerificationService


class FacebookClientBusinessVerificationTestCase(TestCase):
    def setUp(self):
        self.client = FacebookClient("token")

    def test_facebook_client_exposes_business_verification_methods(self):
        self.assertIsInstance(self.client, BusinessVerificationRequests)
        self.assertTrue(hasattr(self.client, "submit_self_certify_whatsapp_business"))
        self.assertTrue(
            hasattr(self.client, "list_self_certified_whatsapp_business_submissions")
        )

    def test_submit_sends_multipart_documents(self):
        document = MagicMock()
        document.name = "a.pdf"
        document.read.return_value = b"%PDF"
        document.content_type = "application/pdf"

        with patch.object(self.client, "make_request") as mock_request:
            mock_request.return_value.json.return_value = {
                "success": True,
                "verification_attempts": 1,
            }

            result = self.client.submit_self_certify_whatsapp_business(
                partner_business_id="partner_123",
                end_business_id="client_456",
                documents=[document],
            )

        self.assertEqual(result["verification_attempts"], 1)
        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["data"], {"end_business_id": "client_456"})
        self.assertEqual(len(kwargs["files"]), 1)
        self.assertEqual(kwargs["files"][0][0], "business_documents[]")
        self.assertIn(
            "partner_123/self_certify_whatsapp_business", mock_request.call_args.args[0]
        )

    def test_list_submissions_filters_by_end_business_id(self):
        with patch.object(self.client, "make_request") as mock_request:
            mock_request.return_value.json.return_value = {"data": []}

            self.client.list_self_certified_whatsapp_business_submissions(
                partner_business_id="partner_123", end_business_id="client_456"
            )

        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["method"], "GET")
        self.assertEqual(kwargs["params"], {"end_business_id": "client_456"})

    def test_list_submissions_without_filter_omits_params(self):
        with patch.object(self.client, "make_request") as mock_request:
            mock_request.return_value.json.return_value = {"data": []}

            self.client.list_self_certified_whatsapp_business_submissions(
                partner_business_id="partner_123"
            )

        self.assertIsNone(mock_request.call_args.kwargs["params"])


class BusinessVerificationServiceTestCase(TestCase):
    def test_service_delegates_to_client(self):
        client = MagicMock()
        client.submit_self_certify_whatsapp_business.return_value = {"success": True}
        client.list_self_certified_whatsapp_business_submissions.return_value = {
            "data": []
        }

        service = BusinessVerificationService(client=client)
        service.submit(partner_business_id="p", end_business_id="c", documents=["doc"])
        service.list_submissions(partner_business_id="p", end_business_id="c")

        client.submit_self_certify_whatsapp_business.assert_called_once_with(
            partner_business_id="p", end_business_id="c", documents=["doc"]
        )
        client.list_self_certified_whatsapp_business_submissions.assert_called_once_with(
            partner_business_id="p", end_business_id="c"
        )
