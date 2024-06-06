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
            exc_info=1,
            extra={
                "request_details": request_details,
                "response_details": response_details,
            },
        )
