from marketplace.clients.base import RequestClient


class VtexPublicClient(RequestClient):
    def list_products(self, domain):
        url = f"https://{domain}/api/catalog_system/pub/products/search/"
        response = self.make_request(url, method="GET")  # TODO: list all paginate products
        return response

    def check_domain(self, domain):
        try:
            url = f"https://{domain}/api/catalog_system/pub/products/search/"
            response = self.make_request(url, method="GET")
            return response.status_code == 206
        except Exception:
            return False
