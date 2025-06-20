# marketplace/wpp_templates/exceptions.py

from rest_framework.exceptions import APIException
from rest_framework import status


class TemplateMetricsException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Template metrics processing error."
    default_code = "template_metrics_error"

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail=detail, code=code)
