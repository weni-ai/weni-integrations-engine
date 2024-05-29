import requests

from marketplace.clients.exceptions import CustomAPIException


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
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise CustomAPIException(detail=detail, status_code=response.status_code)

        return response
