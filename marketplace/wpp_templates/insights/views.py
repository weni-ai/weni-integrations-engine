from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from marketplace.wpp_templates.insights.dto import TemplateInsightsDTO
from marketplace.wpp_templates.insights.serializers import TemplateVersionDataSerializer
from marketplace.wpp_templates.insights.usecases.template_insights import (
    TemplateInsightsUseCase,
)


class TemplateVersionDataView(APIView):
    """
    View responsible for retrieving template insight data
    based on gallery versions and a specified time range.
    """

    def post(self, request: Request, app_uuid: str) -> Response:
        """
        Handles POST requests for retrieving template insights.

        Path param:
            app_uuid (str): UUID of the application

        Expected body:
            {
                "template_versions": [...],
                "start": "YYYY-MM-DD",
                "end": "YYYY-MM-DD"
            }

        Returns:
            Response with status 200 and insight data.
        """
        serializer = TemplateVersionDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = TemplateInsightsDTO(app_uuid=app_uuid, **serializer.validated_data)

        use_case = TemplateInsightsUseCase()
        result = use_case.execute(dto)

        return Response(result, status=status.HTTP_200_OK)
