from marketplace.clients.base import RequestClient


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
    def check_domain(self, domain):
        try:
            url = f"https://{domain}/api/catalog_system/pub/products/search/"
            response = self.make_request(url, method="GET")
            return response.status_code == 206
        except Exception:
            return False


class VtexPublicClient(VtexCommonClient):
    def search_product_by_sku_id(self, skuid, domain, sellerid=1):
        url = f"https://{domain}/api/catalog_system/pub/products/search?fq=skuId:{skuid}&sellerId={sellerid}"
        response = self.make_request(url, method="GET")
        return response


class VtexPrivateClient(VtexAuthorization, VtexCommonClient):
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

    def list_all_products_sku_ids(self, domain, page_size=1000):
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

    def list_active_sellers(self, domain):
        url = f"https://{domain}/api/seller-register/pvt/sellers"
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        sellers_data = response.json()
        return [seller["id"] for seller in sellers_data["items"] if seller["isActive"]]

    def get_product_details(self, sku_id, domain):
        url = (
            f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        )
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

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
