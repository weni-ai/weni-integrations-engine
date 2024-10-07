import uuid

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from marketplace.wpp_products.models import UploadProduct, Catalog, ProductFeed
from marketplace.wpp_products.utils import ProductBatchFetcher
from marketplace.applications.models import App


User = get_user_model()


class ProductBatchFetcherTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.catalog = Catalog.objects.create(
            name="Test Catalog", facebook_catalog_id="123", app=self.app
        )

        self.feed = ProductFeed.objects.create(name="Test Feed", catalog=self.catalog)

    def test_fetch_most_recent_products(self):
        # Create duplicate products with different modified_on dates
        product_older = UploadProduct.objects.create(
            facebook_product_id="prod_1",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Product 1"},
            modified_on=timezone.now() - timezone.timedelta(days=2),
            status="pending",
        )
        product_newer = UploadProduct.objects.create(
            facebook_product_id="prod_1",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Product 1 Updated"},
            modified_on=timezone.now() - timezone.timedelta(days=1),
            status="pending",
        )

        # Create another set of products
        product_2 = UploadProduct.objects.create(
            facebook_product_id="prod_2",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Product 2"},
            modified_on=timezone.now(),
            status="pending",
        )

        # Initialize the ProductBatchFetcher
        batch_fetcher = ProductBatchFetcher(self.catalog, batch_size=10)

        # Fetch products
        latest_products, product_ids = next(batch_fetcher)

        # Ensure only the most recent product is returned for prod_1
        self.assertEqual(len(latest_products), 2)
        self.assertIn(product_newer, latest_products)
        self.assertNotIn(product_older, latest_products)
        self.assertIn(product_2, latest_products)

        # Ensure that product_ids contains only the latest facebook_product_id values
        self.assertEqual(set(product_ids), {"prod_1", "prod_2"})

    def test_no_pending_products(self):
        # Create non-pending products
        UploadProduct.objects.create(
            facebook_product_id="prod_1",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Product 1"},
            modified_on=timezone.now(),
            status="processing",
        )

        # Initialize the ProductBatchFetcher
        batch_fetcher = ProductBatchFetcher(self.catalog, batch_size=10)

        # Attempt to fetch products and expect StopIteration
        with self.assertRaises(StopIteration):
            next(batch_fetcher)
