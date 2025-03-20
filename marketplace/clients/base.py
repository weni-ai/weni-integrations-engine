import requests
import logging

from django.conf import settings

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
        timeout=60,
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
                timeout=timeout,
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
        if response is None:
            logger.error("Response object is None, request failed.")
            return

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
            f"Response:[{str(response.status_code)}] Error on request url {url}",
            stack_info=False,
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
            stack_info=False,
            extra={
                "request_details": request_details,
                "exception_details": exception_details,
            },
        )


class InternalAuthentication(RequestClient):
    def __get_module_token(self):
        data = {
            "client_id": settings.OIDC_RP_CLIENT_ID,
            "client_secret": settings.OIDC_RP_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        request = self.make_request(
            url=settings.OIDC_OP_TOKEN_ENDPOINT, method="POST", data=data
        )

        token = request.json().get("access_token")

        return f"Bearer {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }
