from rest_framework import status
from rest_framework.exceptions import APIException


class FileNotSendValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The file couldn't be sent. Please try again."
    default_code = "file_not_be_sent"
