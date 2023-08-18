import requests

from marketplace.clients.exceptions import CustomAPIException


class RequestClient:
    def make_request(
        self, url: str, method: str, headers=None, data=None, params=None, files=None
    ):
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=60,
            params=params,
            files=files,
        )
        if response.status_code >= 500:
            raise CustomAPIException(status_code=response.status_code)
        elif response.status_code >= 400:
            raise CustomAPIException(
                detail=response.json() if response.text else response.text,
                status_code=response.status_code,
            )

        return response
