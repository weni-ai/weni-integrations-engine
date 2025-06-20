from datetime import date, datetime, timezone
from typing import List, Dict

from marketplace.services.insights.service import InsightsService
from marketplace.applications.models import App
from marketplace.wpp_templates.metrics.exceptions import TemplateMetricsException
from marketplace.wpp_templates.models import TemplateTranslation
from marketplace.wpp_templates.metrics.dto import TemplateMetricsDTO


class TemplateMetricsUseCase:
    """
    Use case responsible for retrieving template metrics data
    based on gallery versions, period, and application context.
    """

    def __init__(self):
        self.insights_service = InsightsService()

    def execute(self, metrics_dto: TemplateMetricsDTO) -> Dict:
        """
        Executes the use case to retrieve insights for given templates.

        Args:
            insights_dto (TemplateInsightsDTO): Input data containing versions, time window, and app.

        Returns:
            dict: Response from Insights service.
        """
        start_dt, end_dt = self._normalize_period(metrics_dto.start, metrics_dto.end)

        params = {
            "waba_id": self._get_waba_id(metrics_dto.app_uuid),
            "start_date": self.isoformat_z(start_dt),
            "end_date": self.isoformat_z(end_dt),
        }

        payload = {
            "template_ids": self._get_template_versions(metrics_dto.template_versions),
        }

        return self.insights_service.get_template_metrics(
            params=params, payload=payload
        )

    def isoformat_z(self, dt: datetime) -> str:
        """
        Return ISO 8601 format with 'Z' instead of '+00:00' for UTC.
        Ex: '2025-06-12T00:00:00Z'
        """
        if dt.tzinfo == timezone.utc:
            return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        return dt.isoformat(timespec="seconds")

    def _normalize_period(
        self, start_date: date, end_date: date
    ) -> tuple[datetime, datetime]:
        """
        Converts date objects to full-day datetime range in UTC.
        """
        start_dt = datetime.combine(
            start_date, datetime.min.time(), tzinfo=timezone.utc
        )
        end_dt = datetime.combine(
            end_date, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc
        )
        return start_dt, end_dt

    def _get_template_versions(self, gallery_versions: List[str]) -> List[str]:
        """
        Retrieves all `message_template_id`s linked to the given gallery versions.

        Args:
            gallery_versions (List[str]): List of gallery_version UUIDs from TemplateMessage.

        Returns:
            List[str]: Distinct list of message_template_ids.

        Raises:
            TemplateMetricsException: If no templates are found for the provided gallery versions.
        """
        template_ids = list(
            TemplateTranslation.objects.filter(
                template__gallery_version__in=gallery_versions
            )
            .values_list("message_template_id", flat=True)
            .distinct()
        )
        if not template_ids:
            raise TemplateMetricsException(
                "No templates found for the provided gallery versions."
            )

        return template_ids

    def _get_waba_id(self, app_uuid: str) -> str:
        """
        Retrieves the WABA ID from the App config.

        Args:
            app_uuid (str): UUID of the application.

        Returns:
            str: The WABA ID.

        Raises:
            TemplateMetricsException: If the WABA ID is not found in the app config.
        """
        app = App.objects.get(uuid=app_uuid)
        waba_id = app.config.get("wa_waba_id")
        if not waba_id:
            raise TemplateMetricsException(
                f"WABA ID not found in app config for app_uuid={app_uuid}"
            )
        return waba_id
