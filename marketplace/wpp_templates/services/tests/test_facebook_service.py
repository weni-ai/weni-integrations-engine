import uuid
from django.test import TestCase

from marketplace.wpp_templates.services.facebook import FacebookService

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation
from django.contrib.auth import get_user_model


User = get_user_model()


class MockFacebookClient:
    def get_template_analytics(self, waba_id, fields):
        return {
            "data": {
                "data_points": [
                    {
                        "template_id": "831797345020910",
                        "start": 1695859200,
                        "end": 1695945600,
                        "sent": 3,
                        "delivered": 3,
                        "read": 1,
                    },
                    {
                        "template_id": "831797345020911",
                        "start": 1695859200,
                        "end": 1695945600,
                        "sent": 0,
                        "delivered": 0,
                        "read": 0,
                    },
                    {
                        "template_id": "831797345020909",
                        "start": 1695859200,
                        "end": 1695945600,
                        "sent": 0,
                        "delivered": 0,
                        "read": 0,
                    },
                ],
            },
            "paging": {"cursors": {"before": "MAZDZD", "after": "MjQZD"}},
        }


class MockFacebookClientWithMultipleDataPoints:
    def get_template_analytics(self, waba_id, fields):
        return {
            "data": {
                "data_points": [
                    {
                        "template_id": "831797345020910",
                        "start": 1695859200,
                        "end": 1695945600,
                        "sent": 3,
                        "delivered": 3,
                        "read": 1,
                    },
                    {
                        "template_id": "831797345020910",
                        "start": 1695945600,
                        "end": 1696032000,
                        "sent": 2,
                        "delivered": 2,
                        "read": 1,
                    },
                ],
            },
            "paging": {"cursors": {"before": "MAZDZD", "after": "MjQZD"}},
        }


class SetUpBaseService(TestCase):
    def setUp(self):
        user, _bool = User.objects.get_or_create(email="user-fbaservice@marketplace.ai")
        self.service = FacebookService(client=MockFacebookClient())
        config = {
            "wa_business_id": "101010101010",
            "wa_waba_id": "10203040",
            "wa_phone_number_id": "012345678910",
        }
        self.app = App.objects.create(
            code="wpp-cloud",
            config=config,
            created_by=user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.template_message_1 = TemplateMessage.objects.create(
            name="test_template1",
            app=self.app,
            category="UTILITY",
            template_type="TEXT",
            created_by=user,
        )
        self.template_message_2 = TemplateMessage.objects.create(
            name="test_template2",
            app=self.app,
            category="UTILITY",
            template_type="TEXT",
            created_by=user,
        )
        self.template_translation_1 = TemplateTranslation.objects.create(
            template=self.template_message_1,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            message_template_id="831797345020910",
        )
        self.template_translation_2 = TemplateTranslation.objects.create(
            template=self.template_message_2,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            message_template_id="831797345020911",
        )


class TestFacebookServiceAnalytics(SetUpBaseService):
    def test_get_template_analytics(self):
        validated_data = {
            "start": 1695772800,
            "end": 1695945599,
            "fba_template_ids": [
                "831797345020910",
                "831797345020911",
                "831797345020909",
            ],
        }
        expected_data = {
            "data": [
                {
                    "template_id": "831797345020910",
                    "template_name": "test_template1",
                    "totals": {"sent": 3, "delivered": 3, "read": 1},
                    "dates": [
                        {"start": "2023-09-28", "sent": 3, "delivered": 3, "read": 1}
                    ],
                },
                {
                    "template_id": "831797345020911",
                    "template_name": "test_template2",
                    "totals": {"sent": 0, "delivered": 0, "read": 0},
                    "dates": [
                        {"start": "2023-09-28", "sent": 0, "delivered": 0, "read": 0}
                    ],
                },
                {
                    "template_id": "831797345020909",
                    "template_name": None,
                    "totals": {"sent": 0, "delivered": 0, "read": 0},
                    "dates": [
                        {"start": "2023-09-28", "sent": 0, "delivered": 0, "read": 0}
                    ],
                },
            ],
            "grand_totals": {"sent": 3, "delivered": 3, "read": 1},
        }
        response = self.service.template_analytics(self.app, validated_data)
        self.assertEqual(response, expected_data)

    def test_raise_value_error(self):
        self.app.config = {
            "wa_business_id": "101010101010",
            "wa_phone_number_id": "012345678910",
        }
        self.app.save()

        validated_data = {
            "start": 1695772800,
            "end": 1695945599,
            "fba_template_ids": [
                "831797345020910",
                "831797345020911",
                "831797345020909",
            ],
        }
        with self.assertRaisesMessage(
            ValueError, "Not found 'wa_waba_id' in app.config"
        ):
            self.service.template_analytics(self.app, validated_data)

    def test_multiple_data_points(self):
        self.service = FacebookService(
            client=MockFacebookClientWithMultipleDataPoints()
        )

        validated_data = {
            "start": 1695772800,
            "end": 1695945599,
            "fba_template_ids": [
                "831797345020910",
                "831797345020911",
                "831797345020909",
            ],
        }
        expected_data = {
            "data": [
                {
                    "template_id": "831797345020910",
                    "template_name": "test_template1",
                    "totals": {"sent": 5, "delivered": 5, "read": 2},
                    "dates": [
                        {"start": "2023-09-28", "sent": 3, "delivered": 3, "read": 1},
                        {"start": "2023-09-29", "sent": 2, "delivered": 2, "read": 1},
                    ],
                }
            ],
            "grand_totals": {"sent": 5, "delivered": 5, "read": 2},
        }
        response = self.service.template_analytics(self.app, validated_data)

        self.service = FacebookService(client=MockFacebookClient())
        self.assertEqual(response, expected_data)
