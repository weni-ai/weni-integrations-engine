from unittest import TestCase
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timezone
from uuid import uuid4

from marketplace.services.insights.service import InsightsService
from marketplace.wpp_templates.metrics.usecases.template_metrics import (
    TemplateMetricsUseCase,
)
from marketplace.wpp_templates.metrics.dto import TemplateMetricsDTO
from marketplace.wpp_templates.metrics.exceptions import TemplateMetricsException


class TestTemplateMetricsUseCase(TestCase):
    def setUp(self):
        self.mock_insights_service = MagicMock(spec=InsightsService)
        self.use_case = TemplateMetricsUseCase(
            insights_service=self.mock_insights_service
        )
        self.start_date = date(2024, 6, 1)
        self.end_date = date(2024, 6, 5)
        self.app_uuid = str(uuid4())
        self.gallery_versions = [str(uuid4()), str(uuid4())]
        self.metrics_dto = TemplateMetricsDTO(
            template_versions=self.gallery_versions,
            start=self.start_date,
            end=self.end_date,
            app_uuid=self.app_uuid,
        )

    @patch(
        "marketplace.wpp_templates.metrics.usecases.template_metrics.TemplateMetricsUseCase._get_template_versions"
    )
    @patch(
        "marketplace.wpp_templates.metrics.usecases.template_metrics.TemplateMetricsUseCase._get_waba_id"
    )
    def test_execute_success(self, mock_get_waba_id, mock_get_template_versions):
        """Should call InsightsService with correct params and return its result."""
        mock_get_waba_id.return_value = "123456"
        mock_get_template_versions.return_value = ["templ1", "templ2"]
        self.mock_insights_service.get_template_metrics.return_value = {"result": "ok"}

        result = self.use_case.execute(self.metrics_dto)

        start_dt, end_dt = self.use_case._normalize_period(
            self.start_date, self.end_date
        )
        expected_params = {
            "waba_id": "123456",
            "start_date": self.use_case.isoformat_z(start_dt),
            "end_date": self.use_case.isoformat_z(end_dt),
        }
        expected_payload = {"template_ids": ["templ1", "templ2"]}

        self.mock_insights_service.get_template_metrics.assert_called_once_with(
            params=expected_params, payload=expected_payload
        )
        self.assertEqual(result, {"result": "ok"})

    @patch(
        "marketplace.wpp_templates.metrics.usecases.template_metrics.TemplateMetricsUseCase._get_template_versions"
    )
    @patch(
        "marketplace.wpp_templates.metrics.usecases.template_metrics.TemplateMetricsUseCase._get_waba_id"
    )
    def test_execute_no_templates_found(
        self, mock_get_waba_id, mock_get_template_versions
    ):
        """Should return an empty list if no template ids are found."""
        mock_get_waba_id.return_value = "123456"
        mock_get_template_versions.return_value = []
        result = self.use_case.execute(self.metrics_dto)
        self.assertEqual(result, [])
        self.mock_insights_service.get_template_metrics.assert_not_called()

    def test_normalize_period(self):
        """Should convert dates to full-day UTC datetimes."""
        start_dt, end_dt = self.use_case._normalize_period(
            self.start_date, self.end_date
        )
        self.assertIsInstance(start_dt, datetime)
        self.assertIsInstance(end_dt, datetime)
        self.assertEqual(start_dt.hour, 0)
        self.assertEqual(end_dt.hour, 23)
        self.assertEqual(start_dt.tzinfo, timezone.utc)
        self.assertEqual(end_dt.tzinfo, timezone.utc)

    def test_isoformat_z_with_utc(self):
        """Should return ISO format with Z for UTC datetimes."""
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = self.use_case.isoformat_z(dt)
        self.assertEqual(result, "2024-06-01T12:00:00Z")

    def test_isoformat_z_with_naive(self):
        """Should return ISO format without Z for non-UTC datetimes."""
        dt = datetime(2024, 6, 1, 12, 0, 0)  # naive datetime
        result = self.use_case.isoformat_z(dt)
        self.assertEqual(result, "2024-06-01T12:00:00")

    @patch(
        "marketplace.wpp_templates.metrics.usecases.template_metrics.TemplateTranslation"
    )
    def test_get_template_versions_success(self, mock_template_translation):
        """Should return distinct template ids from gallery versions."""
        mock_qs = MagicMock()
        mock_qs.values_list.return_value.distinct.return_value = ["id1", "id2"]
        mock_template_translation.objects.filter.return_value = mock_qs

        result = self.use_case._get_template_versions(["ver1", "ver2"])
        mock_template_translation.objects.filter.assert_called_once_with(
            template__gallery_version__in=["ver1", "ver2"]
        )
        self.assertEqual(result, ["id1", "id2"])

    @patch("marketplace.wpp_templates.metrics.usecases.template_metrics.App")
    def test_get_waba_id_success(self, mock_app_model):
        """Should return waba_id from app config."""
        mock_app = MagicMock()
        mock_app.config = {"wa_waba_id": "waba-123"}
        mock_app_model.objects.get.return_value = mock_app

        result = self.use_case._get_waba_id(self.app_uuid)
        mock_app_model.objects.get.assert_called_once_with(uuid=self.app_uuid)
        self.assertEqual(result, "waba-123")

    @patch("marketplace.wpp_templates.metrics.usecases.template_metrics.App")
    def test_get_waba_id_missing(self, mock_app_model):
        """Should raise TemplateMetricsException if waba_id not in app config."""
        mock_app = MagicMock()
        mock_app.config = {}
        mock_app_model.objects.get.return_value = mock_app

        with self.assertRaises(TemplateMetricsException) as context:
            self.use_case._get_waba_id(self.app_uuid)
        self.assertIn("WABA ID not found in app config", str(context.exception))
