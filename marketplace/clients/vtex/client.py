from marketplace.clients.base import RequestClient
from marketplace.clients.decorators import retry_on_exception
from marketplace.clients.vtex.decorator import rate_limit_and_retry_on_exception


class VtexAuthorization(RequestClient):
    def __init__(self, app_key, app_token):
        self.app_key = app_key
        self.app_token = app_token

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-VTEX-API-AppKey": self.app_key,
            "X-VTEX-API-AppToken": self.app_token,
        }
        return headers


class VtexCommonClient(RequestClient):
    @retry_on_exception()
    def check_domain(self, domain):
        try:
            url = f"https://{domain}/api/catalog_system/pub/products/search/"
            response = self.make_request(url, method="GET")
            return 200 <= response.status_code <= 299
        except Exception:
            return False


class VtexPublicClient(VtexCommonClient):
    def search_product_by_sku_id(self, skuid, domain, sellerid=1):
        url = f"https://{domain}/api/catalog_system/pub/products/search?fq=skuId:{skuid}&sellerId={sellerid}"
        response = self.make_request(url, method="GET")
        return response


class VtexPrivateClient(VtexAuthorization, VtexCommonClient):
    # API throttling, expects the domain to be the last parameter
    def get_domain_from_args(self, *args, **kwargs):
        domain = kwargs.get("domain")
        if domain is None and args:
            domain = args[-1]
        return domain

    @retry_on_exception()
    def is_valid_credentials(self, domain):
        try:
            url = (
                f"https://{domain}/api/catalog_system/pvt/products/GetProductAndSkuIds"
            )
            headers = self._get_headers()
            response = self.make_request(url, method="GET", headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    @retry_on_exception()
    def list_all_products_sku_ids(self, domain, page_size=100000):
        all_skus = []
        page = 1

        while True:
            url = f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitids?page={page}&pagesize={page_size}"
            headers = self._get_headers()
            response = self.make_request(url, method="GET", headers=headers)

            sku_ids = response.json()
            if not sku_ids:
                break

            all_skus.extend(sku_ids)
            page += 1

        return all_skus

    @retry_on_exception()
    def list_active_sellers(self, domain):
        from_index = 0
        batch_size = 100
        total_sellers = float("inf")
        active_sellers = []

        while from_index < total_sellers:
            url = f"https://{domain}/api/seller-register/pvt/sellers?from={from_index}&to={from_index + batch_size}"
            headers = self._get_headers()
            response = self.make_request(url, method="GET", headers=headers)
            sellers_data = response.json()

            if total_sellers == float("inf"):
                total_sellers = sellers_data["paging"]["total"]

            active_sellers.extend(
                [
                    seller["id"]
                    for seller in sellers_data["items"]
                    if seller.get("isActive", False)
                ]
            )
            from_index += batch_size

        return active_sellers

    # API throttling, params:(second, minute, domain)
    @rate_limit_and_retry_on_exception(10, 40, get_domain_from_args)
    def get_product_details(self, sku_id, domain):
        url = (
            f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        )
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    # API throttling, params:(second, minute, domain)
    @rate_limit_and_retry_on_exception(10, 40, get_domain_from_args)
    def pub_simulate_cart_for_seller(self, sku_id, seller_id, domain):
        cart_simulation_url = f"https://{domain}/api/checkout/pub/orderForms/simulation"
        payload = {"items": [{"id": sku_id, "quantity": 1, "seller": seller_id}]}

        response = self.make_request(cart_simulation_url, method="POST", json=payload)
        simulation_data = response.json()

        if simulation_data["items"]:
            item_data = simulation_data["items"][0]
            return {
                "is_available": item_data["availability"] == "available",
                "price": item_data["price"],
                "list_price": item_data["listPrice"],
            }
        else:
            return {
                "is_available": False,
                "price": 0,
                "list_price": 0,
            }
