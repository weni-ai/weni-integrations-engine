"""Client for connection with Retail Commerce"""

from django.conf import settings

from marketplace.clients.base import InternalAuthentication, RequestClient
from marketplace.interfaces.commerce.interfaces import CommerceClientInterface


class CommerceClient(RequestClient, CommerceClientInterface):
    def __init__(self):
        self.base_url = settings.COMMERCE_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def send_template_library_status_update(self, data):
        url = f"{self.base_url}/api/v1/webhook/template-library-status/notification"

        response = self.make_request(
            url, method="POST", headers=self.authentication_instance.headers, json=data
        )
        return response.json()
