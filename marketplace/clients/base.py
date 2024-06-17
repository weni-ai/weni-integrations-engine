import requests
import logging

from marketplace.clients.exceptions import CustomAPIException


logger = logging.getLogger(__name__)


class RequestClient:
    def make_request(
        self,
        url: str,
        method: str,
        headers=None,
        data=None,
        params=None,
        files=None,
        json=None,
    ):
        if data and json:
            raise ValueError(
                "Cannot use both 'data' and 'json' arguments simultaneously."
            )
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                data=data,
                timeout=60,
                params=params,
                files=files,
            )
        except Exception as e:
            self._log_request_exception(
                exception=e,
                url=url,
                method=method,
                headers=headers,
                json=json,
                data=data,
                params=params,
                files=files,
            )
            raise CustomAPIException(
                detail=f"Base request error: {str(e)}",
                status_code=getattr(e.response, "status_code", None),
            ) from e

        if response.status_code >= 400:
            detail = ""
            self._generate_log(
                response, url, method, headers, json, data, params, files
            )
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise CustomAPIException(detail=detail, status_code=response.status_code)

        return response

    def _generate_log(self, response, url, method, headers, json, data, params, files):
        request_details = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
            "data": data,
            "params": params,
            "files": files,
        }
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "url": response.url,
        }
        logger.error(
            f"Error on request url {url}",
            exc_info=True,
            stack_info=True,
            extra={
                "request_details": request_details,
                "response_details": response_details,
            },
        )

    def _log_request_exception(
        self, exception, url, method, headers, json, data, params, files
    ):
        request_details = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
            "data": data,
            "params": params,
            "files": files,
        }
        exception_details = {
            "type": type(exception).__name__,
            "message": str(exception),
            "args": exception.args,
        }
        # Check if the exception has a response attribute (specific to requests exceptions)
        if hasattr(exception, "response") and exception.response is not None:
            exception_details.update(
                {
                    "response_status_code": exception.response.status_code,
                    "response_headers": dict(exception.response.headers),
                    "response_body": exception.response.text,
                }
            )

        logger.error(
            f"Request exception for URL {url}",
            exc_info=True,
            stack_info=True,
            extra={
                "request_details": request_details,
                "exception_details": exception_details,
            },
        )
