from rest_framework.exceptions import APIException


class TemplateMetricsException(APIException):
    status_code = 400
    default_detail = "A template metrics error occurred."
    default_code = "bad_request"

    def __init__(self, detail: str):
        super().__init__(detail=str(detail))
