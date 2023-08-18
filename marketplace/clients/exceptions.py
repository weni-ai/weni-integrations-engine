from rest_framework.exceptions import APIException


class CustomAPIException(APIException):
    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail, code)
        self.status_code = status_code or self.status_code
