from rest_framework.exceptions import APIException


class TemplateMetricsException(APIException):
    status_code = 400
    default_code = "template_metrics_error"

    def __init__(self, detail=None):
        super().__init__(detail)

    def __str__(self):
        return str(self.detail)
