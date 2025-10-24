import time
import logging

from django.conf import settings

from marketplace.clients.base import RequestClient
from marketplace.clients.decorators import retry_on_exception


logger = logging.getLogger(__name__)


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
    VTEX_CALLS_PER_PERIOD = settings.VTEX_CALLS_PER_PERIOD
    VTEX_PERIOD = settings.VTEX_PERIOD

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

    def list_all_products_sku_ids(self, domain, page_size=100000, sales_channel=None):
        """Retrieves all SKU IDs of active products from VTEX with progress tracking."""
        all_skus = []
        page = 1
        total_processed = 0
        print_interval = 10_000  # Interval for progress updates

        headers = self._get_headers()

        while True:
            # Fetch product batch with retry mechanism
            sku_ids = self._fetch_sku_batch_with_retry(
                domain, page, page_size, headers, sales_channel
            )

            if not sku_ids:
                break

            batch_sku_count = len(sku_ids)
            total_processed += batch_sku_count
            all_skus.extend(sku_ids)

            # Progress tracking
            if (total_processed // print_interval) > (
                (total_processed - batch_sku_count) // print_interval
            ):
                logger.info(
                    f"Processed {print_interval * (total_processed // print_interval):,} SKUs..."
                )

            page += 1

        logger.info(f"Total SKUs processed: {total_processed:,}")
        return all_skus

    @retry_on_exception()
    def _fetch_sku_batch_with_retry(
        self, domain, page, page_size, headers, sales_channel=None
    ):
        """Fetches a batch of product SKUs from VTEX with automatic retries in case of failure."""
        if sales_channel:
            url = f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitidsbysaleschannel?sc={sales_channel}&page={page}&pagesize={page_size}"  # noqa: E501
        else:
            url = f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitids?page={page}&pagesize={page_size}"
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    @retry_on_exception()
    def list_active_sellers(self, domain, sales_channel=None):
        if sales_channel:
            # Use sales channel specific endpoint
            url = f"https://{domain}/api/catalog_system/pvt/seller/list?sc={sales_channel}&sellerType=1"
            headers = self._get_headers()
            response = self.make_request(url, method="GET", headers=headers)
            sellers_data = response.json()

            # Extract seller IDs from the response
            # The API returns a list directly, not an object with "items" property
            active_sellers = [
                seller["SellerId"]
                for seller in sellers_data
                if isinstance(seller, dict) and seller.get("IsActive", False)
            ]
            return active_sellers
        else:
            # Use original endpoint for backward compatibility
            from_index = 0
            batch_size = 100
            total_sellers = float("inf")
            active_sellers = []

            while from_index < total_sellers:
                url = f"https://{domain}/api/seller-register/pvt/sellers?from={from_index}&to={from_index + batch_size}"  # noqa: E501
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

    @retry_on_exception()
    def get_product_details(self, sku_id, domain):
        url = (
            f"https://{domain}/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        )
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    @retry_on_exception()
    def pub_simulate_cart_for_seller(
        self, sku_id: str, seller_id: str, domain: str, sales_channel: str = None
    ):
        cart_simulation_url = f"https://{domain}/api/checkout/pub/orderForms/simulation"
        payload = {"items": [{"id": sku_id, "quantity": 1, "seller": seller_id}]}

        time.sleep(1)  # The best performance needed this 'sleep'

        # Set params based on sales channel
        params = {"sc": sales_channel} if sales_channel else None

        response = self.make_request(
            cart_simulation_url,
            method="POST",
            json=payload,
            params=params,
            ignore_error_logs=True,
        )
        simulation_data = response.json()

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
            "data": simulation_data,
        }

    def list_all_active_products(self, domain):
        """Retrieves all active product SKUs from VTEX catalog with progress tracking."""
        unique_skus = set()
        step = 250
        current_from = 1
        total_processed = 0  # Tracks cumulative processed SKUs
        print_interval = 10_000  # Progress update interval

        headers = self._get_headers()

        while True:
            current_to = current_from + step - 1
            url = (
                f"https://{domain}/api/catalog_system/pvt/products/"
                f"GetProductAndSkuIds?_from={current_from}&_to={current_to}&status=1"
            )

            # Fetch product batch with retry mechanism
            response = self._fetch_product_batch_with_retry(url, headers)

            data = response.json().get("data", {})
            if not data:
                break

            # Process batch
            batch_sku_count = sum(len(skus) for _, skus in data.items())
            total_processed += batch_sku_count

            # Progress tracking
            if (total_processed // print_interval) > (
                (total_processed - batch_sku_count) // print_interval
            ):
                logger.info(
                    f"Processed {print_interval * (total_processed // print_interval):,} SKUs..."
                )

            for _, skus in data.items():
                unique_skus.update(skus)

            current_from += step  # Move to the next batch

        logger.info(f"Total SKUs processed: {total_processed:,}")
        return list(unique_skus)

    @retry_on_exception()
    def _fetch_product_batch_with_retry(self, url, headers):
        """Fetches a batch of product SKUs from VTEX with automatic retries on failure."""
        return self.make_request(url, method="GET", headers=headers)

    @retry_on_exception()
    def get_product_specification(self, product_id, domain):
        url = f"https://{domain}/api/catalog_system/pvt/products/{product_id}/specification"
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    @retry_on_exception()
    def simulate_cart_for_multiple_sellers(
        self, sku_id, sellers, domain, sales_channel: str = None
    ):
        """
        Simulate cart for a SKU across multiple sellers in a single request.
        """
        cart_simulation_url = f"https://{domain}/api/checkout/pub/orderForms/simulation"
        items = [{"id": sku_id, "quantity": 1, "seller": seller} for seller in sellers]
        payload = {"items": items}

        # Set params based on sales channel
        params = {"sc": sales_channel} if sales_channel else None

        response = self.make_request(
            cart_simulation_url,
            method="POST",
            json=payload,
            params=params,
            ignore_error_logs=True,
        )
        simulation_data = response.json()

        results = {}
        for item in simulation_data.get("items", []):
            seller_id = item.get("seller")
            results[seller_id] = {
                "is_available": item.get("availability") == "available",
                "price": item.get("price", 0),
                "list_price": item.get("listPrice", 0),
                "data": simulation_data,
            }

        return results
