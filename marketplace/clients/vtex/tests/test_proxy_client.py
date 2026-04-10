import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from marketplace.clients.vtex.proxy_client import VtexProxyClient


MOCK_PRIVATE_KEY = b"""-----BEGIN RSA PRIVATE KEY-----
MIIBogIBAAJBALRiMLAHudeSA/x3hB2f+2NRkJLA/Gy8/CYjlS/rLDEBzVJn0fH
hMDcIPhNBn9PpKHNMKnMXxEyVdDK1m0F3QcCAwEAAQJAI4+oaVpWlMsa0F8VHarh
NxVm16YjIEfjG1exLQdthGwzbFuV1kfNbRfAHwqmQGMx0uIpf5z0oHaOFqL8GGMu
YQIhAOIRp4j9PVm67NNqMAt4+mfL6tL1fYbPa2TbVR/CNnbRAiEAzKm07Sp1sOPm
cJEmPlJRzWIKnOi2NKFjUMcufAQT0ycCIFxHXjPgPYfR9VNrCBccL/Lb92JQwWnR
LXiPT+A9MAxRAiEAyIjn/ZKRuXNZz3MbHDxEhNxM/PNtfHKJn+L2FAXByJcCIDKT
lOydiVmMJGJPXjORgVPCX2J/6BDzWj3bRuRH5VQw
-----END RSA PRIVATE KEY-----"""


@override_settings(
    RETAIL_PROXY_URL="https://retail-staging.example.com",
    JWT_PRIVATE_KEY=MOCK_PRIVATE_KEY,
)
class TestVtexProxyClient(TestCase):
    def setUp(self):
        self.project_uuid = str(uuid.uuid4())
        self.client = VtexProxyClient(project_uuid=self.project_uuid)

    def test_init_sets_project_uuid_and_proxy_url(self):
        self.assertEqual(self.client.project_uuid, self.project_uuid)
        self.assertEqual(self.client.proxy_url, "https://retail-staging.example.com")

    def test_generate_jwt_token_contains_project_uuid(self):
        import jwt

        token = self.client._generate_jwt_token()
        payload = jwt.decode(token, MOCK_PRIVATE_KEY, algorithms=["RS256"])
        self.assertEqual(payload["project_uuid"], self.project_uuid)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    @patch.object(VtexProxyClient, "make_request")
    def test_proxy_request_sends_correct_payload(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_make_request.return_value = mock_response

        result = self.client._proxy_request(
            "GET", "/api/catalog_system/pvt/seller/list", params={"sc": "1"}
        )

        mock_make_request.assert_called_once()
        call_kwargs = mock_make_request.call_args
        self.assertEqual(call_kwargs.kwargs["method"], "POST")
        self.assertIn("/vtex/proxy/", call_kwargs.args[0])

        payload = call_kwargs.kwargs["json"]
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["path"], "/api/catalog_system/pvt/seller/list")
        self.assertEqual(payload["params"], {"sc": "1"})
        self.assertNotIn("data", payload)

        self.assertEqual(result, {"data": "test"})

    @patch.object(VtexProxyClient, "make_request")
    def test_proxy_request_with_post_data(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_make_request.return_value = mock_response

        data = {"items": [{"id": "123", "quantity": 1, "seller": "1"}]}
        self.client._proxy_request(
            "POST",
            "/api/checkout/pub/orderForms/simulation",
            params={"sc": "1"},
            data=data,
        )

        payload = mock_make_request.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "POST")
        self.assertEqual(payload["data"], data)
        self.assertEqual(payload["params"], {"sc": "1"})

    @patch.object(VtexProxyClient, "make_request")
    def test_get_product_details(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Id": 123,
            "SkuName": "Test Product",
            "IsActive": True,
        }
        mock_make_request.return_value = mock_response

        result = self.client.get_product_details("123", "domain.vtex.com")

        payload = mock_make_request.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(
            payload["path"],
            "/api/catalog_system/pvt/sku/stockkeepingunitbyid/123",
        )
        self.assertEqual(result["Id"], 123)

    @patch.object(VtexProxyClient, "make_request")
    def test_pub_simulate_cart_for_seller_available(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "availability": "available",
                    "price": 1990,
                    "listPrice": 2490,
                    "sellingPrice": 1990,
                }
            ]
        }
        mock_make_request.return_value = mock_response

        result = self.client.pub_simulate_cart_for_seller(
            "123", "1", "domain.vtex.com", "1"
        )

        self.assertTrue(result["is_available"])
        self.assertEqual(result["price"], 1990)
        self.assertEqual(result["list_price"], 2490)
        self.assertEqual(result["selling_price"], 1990)

    @patch.object(VtexProxyClient, "make_request")
    def test_pub_simulate_cart_for_seller_unavailable(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_make_request.return_value = mock_response

        result = self.client.pub_simulate_cart_for_seller("123", "1", "domain.vtex.com")

        self.assertFalse(result["is_available"])
        self.assertEqual(result["price"], 0)

    @patch.object(VtexProxyClient, "make_request")
    def test_simulate_cart_for_multiple_sellers(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "seller": "1",
                    "availability": "available",
                    "price": 1990,
                    "sellingPrice": 1990,
                    "listPrice": 2490,
                },
                {
                    "seller": "2",
                    "availability": "unavailable",
                    "price": 0,
                    "sellingPrice": 0,
                    "listPrice": 0,
                },
            ]
        }
        mock_make_request.return_value = mock_response

        result = self.client.simulate_cart_for_multiple_sellers(
            "123", ["1", "2"], "domain.vtex.com"
        )

        self.assertTrue(result["1"]["is_available"])
        self.assertFalse(result["2"]["is_available"])

    @patch.object(VtexProxyClient, "make_request")
    def test_list_active_sellers_with_sales_channel(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"SellerId": "1", "IsActive": True},
            {"SellerId": "2", "IsActive": False},
            {"SellerId": "3", "IsActive": True},
        ]
        mock_make_request.return_value = mock_response

        result = self.client.list_active_sellers("domain.vtex.com", sales_channel="1")

        self.assertEqual(result, ["1", "3"])

    @patch.object(VtexProxyClient, "make_request")
    def test_check_domain_success(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_make_request.return_value = mock_response

        self.assertTrue(self.client.check_domain("domain.vtex.com"))

    @patch.object(VtexProxyClient, "make_request")
    def test_check_domain_failure(self, mock_make_request):
        mock_make_request.side_effect = Exception("Connection error")
        self.assertFalse(self.client.check_domain("domain.vtex.com"))

    @patch.object(VtexProxyClient, "make_request")
    def test_get_product_specification(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = [{"Name": "Color", "Value": "Red"}]
        mock_make_request.return_value = mock_response

        result = self.client.get_product_specification("456", "domain.vtex.com")

        payload = mock_make_request.call_args.kwargs["json"]
        self.assertEqual(
            payload["path"],
            "/api/catalog_system/pvt/products/456/specification",
        )
        self.assertEqual(result[0]["Name"], "Color")
