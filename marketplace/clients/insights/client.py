"""Client for connection with insights"""

from django.conf import settings

from marketplace.clients.base import RequestClient, InternalAuthentication


class InsightsClient(RequestClient):
    def __init__(self):
        self.base_url = settings.INSIGHTS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()
    
    def create_whatsapp_integration(self, whatsapp_data):
    url = f"{self.base_url}/v1/metrics/meta/internal/whatsapp-integration/"
    response = self.make_request(
        url,
        method="POST",
        headers=self.authentication_instance.headers,
        json=whatsapp_data
    )
    return response.json()
