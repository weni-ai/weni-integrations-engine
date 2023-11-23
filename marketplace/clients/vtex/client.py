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
    def get_products_sku_ids(self, domain):
        all_skus = []
        page_size = 250
        _from = 1
        _to = page_size

        while True:
            url = f"https://{domain}/api/catalog_system/pvt/products/GetProductAndSkuIds?_from={_from}&_to={_to}"
            headers = self._get_headers()
            response = self.make_request(url, method="GET", headers=headers)

            data = response.json().get("data")
            if data:
                for sku_ids in data.values():
                    all_skus.extend(sku_ids)

                total_products = response.json().get("range", {}).get("total", 0)
                if _to >= total_products:
                    break
                _from += page_size
                _to += page_size
                _to = min(_to, total_products)  # To avoid overshooting the total count
            else:
                break

        return all_skus
