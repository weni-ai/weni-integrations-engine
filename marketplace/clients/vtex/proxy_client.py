import time
import logging
import jwt

from datetime import datetime, timedelta, timezone

from django.conf import settings

from marketplace.clients.base import RequestClient
from marketplace.clients.decorators import retry_on_exception


logger = logging.getLogger(__name__)


class VtexProxyClient(RequestClient):
    """
    VTEX client that routes API calls through the retail-setup proxy.

    Instead of calling VTEX APIs directly with app_key/app_token,
    this client sends requests to the retail-setup /vtex/proxy/ endpoint,
    which handles VTEX IO authentication transparently.
    """

    def __init__(self, project_uuid: str):
        self.project_uuid = project_uuid
        self.proxy_url = settings.RETAIL_PROXY_URL.rstrip("/")

    def _generate_jwt_token(self) -> str:
        private_key = settings.JWT_PRIVATE_KEY
        if not private_key:
            raise ValueError("JWT_PRIVATE_KEY not configured in Django settings.")

        payload = {
            "project_uuid": self.project_uuid,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def _proxy_request(self, method: str, path: str, params=None, data=None):
        url = f"{self.proxy_url}/vtex/proxy/"
        token = self._generate_jwt_token()

        payload = {"method": method.upper(), "path": path}
        if params:
            payload["params"] = params
        if data:
            payload["data"] = data

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = self.make_request(url, method="POST", json=payload, headers=headers)
        return response.json()

    def check_domain(self, domain):
        try:
            self._proxy_request("GET", "/api/catalog_system/pub/products/search/")
            return True
        except Exception:
            return False

    def is_valid_credentials(self, domain):
        try:
            self._proxy_request(
                "GET", "/api/catalog_system/pvt/products/GetProductAndSkuIds"
            )
            return True
        except Exception:
            return False

    def list_all_products_sku_ids(self, domain, page_size=100000, sales_channel=None):
        all_skus = []
        page = 1

        while True:
            sku_ids = self._fetch_sku_batch(page, page_size, sales_channel)
            if not sku_ids:
                break

            all_skus.extend(sku_ids)
            logger.info(f"Proxy: fetched {len(all_skus)} SKUs so far (page {page})")
            page += 1

        logger.info(f"Proxy: total SKUs fetched: {len(all_skus)}")
        return all_skus

    @retry_on_exception()
    def _fetch_sku_batch(self, page, page_size, sales_channel=None):
        if sales_channel:
            path = "/api/catalog_system/pvt/sku/stockkeepingunitidsbysaleschannel"
            params = {"sc": sales_channel, "page": page, "pagesize": page_size}
        else:
            path = "/api/catalog_system/pvt/sku/stockkeepingunitids"
            params = {"page": page, "pagesize": page_size}

        return self._proxy_request("GET", path, params=params)

    @retry_on_exception()
    def list_active_sellers(self, domain, sales_channel=None):
        if sales_channel:
            path = "/api/catalog_system/pvt/seller/list"
            params = {"sc": sales_channel}
            result = self._proxy_request("GET", path, params=params)
            return [
                seller["SellerId"]
                for seller in result
                if isinstance(seller, dict) and seller.get("IsActive", False)
            ]

        from_index = 0
        batch_size = 100
        total_sellers = float("inf")
        active_sellers = []

        while from_index < total_sellers:
            path = "/api/seller-register/pvt/sellers"
            params = {"from": from_index, "to": from_index + batch_size}
            sellers_data = self._proxy_request("GET", path, params=params)

            if total_sellers == float("inf"):
                total_sellers = sellers_data["paging"]["total"]

            active_sellers.extend(
                seller["id"]
                for seller in sellers_data["items"]
                if seller.get("isActive", False)
            )
            from_index += batch_size

        return active_sellers

    @retry_on_exception()
    def get_product_details(self, sku_id, domain):
        path = f"/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        return self._proxy_request("GET", path)

    @retry_on_exception()
    def pub_simulate_cart_for_seller(
        self, sku_id: str, seller_id: str, domain: str, sales_channel: str = None
    ):
        path = "/api/checkout/pub/orderForms/simulation"
        data = {"items": [{"id": sku_id, "quantity": 1, "seller": seller_id}]}
        params = {"sc": sales_channel} if sales_channel else None

        time.sleep(1)

        simulation_data = self._proxy_request("POST", path, params=params, data=data)

        if not simulation_data.get("items"):
            return {
                "is_available": False,
                "price": 0,
                "list_price": 0,
            }

        item = simulation_data["items"][0]
        return {
            "is_available": item["availability"] == "available",
            "price": item.get("price", 0),
            "list_price": item.get("listPrice", 0),
            "selling_price": item.get("sellingPrice", 0),
            "data": simulation_data,
        }

    @retry_on_exception()
    def simulate_cart_for_multiple_sellers(
        self, sku_id, sellers, domain, sales_channel: str = None
    ):
        path = "/api/checkout/pub/orderForms/simulation"
        items = [{"id": sku_id, "quantity": 1, "seller": seller} for seller in sellers]
        data = {"items": items}
        params = {"sc": sales_channel} if sales_channel else None

        simulation_data = self._proxy_request("POST", path, params=params, data=data)

        results = {}
        for item in simulation_data.get("items", []):
            seller_id = item.get("seller")
            results[seller_id] = {
                "is_available": item.get("availability") == "available",
                "price": item.get("price", 0),
                "selling_price": item.get("sellingPrice", 0),
                "list_price": item.get("listPrice", 0),
                "data": simulation_data,
            }

        return results

    @retry_on_exception()
    def get_product_specification(self, product_id, domain):
        path = f"/api/catalog_system/pvt/products/{product_id}/specification"
        return self._proxy_request("GET", path)
