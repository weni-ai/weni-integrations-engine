import uuid

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from marketplace.wpp_products.models import UploadProduct, Catalog, ProductFeed
from marketplace.applications.models import App


User = get_user_model()


class UploadProductTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

        # Create an instance of App
        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        # Create a catalog for testing
        self.catalog = Catalog.objects.create(
            name="Test Catalog", facebook_catalog_id="123", app=self.app
        )

        # Create a product feed using the correct field "name"
        self.feed = ProductFeed.objects.create(name="Test Feed", catalog=self.catalog)

    def test_remove_duplicates_single_record(self):
        # Test when there is only one record, nothing should be deleted
        UploadProduct.objects.create(
            facebook_product_id="prod_1",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product"},
        )

        # Call remove_duplicates
        UploadProduct.remove_duplicates(self.catalog)

        # Ensure the product is still present
        self.assertEqual(
            UploadProduct.objects.filter(facebook_product_id="prod_1").count(), 1
        )

    def test_remove_duplicates_two_records(self):
        # Create two records with the same facebook_product_id but with different modified_on dates
        UploadProduct.objects.create(
            facebook_product_id="prod_2",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 2"},
            modified_on=timezone.now() - timezone.timedelta(days=2),
        )
        UploadProduct.objects.create(
            facebook_product_id="prod_2",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 2 Updated"},
            modified_on=timezone.now() - timezone.timedelta(days=1),
        )

        # Call remove_duplicates
        UploadProduct.remove_duplicates(self.catalog)

        # Ensure the most recent record is kept
        self.assertEqual(
            UploadProduct.objects.filter(facebook_product_id="prod_2").count(), 1
        )
        self.assertTrue(
            UploadProduct.objects.filter(
                facebook_product_id="prod_2", data={"name": "Test Product 2 Updated"}
            ).exists()
        )

    def test_remove_duplicates_three_records(self):
        # Create three duplicate records with different modified_on dates
        UploadProduct.objects.create(
            facebook_product_id="prod_3",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 3"},
            modified_on=timezone.now() - timezone.timedelta(days=3),
        )
        UploadProduct.objects.create(
            facebook_product_id="prod_3",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 3 Updated"},
            modified_on=timezone.now() - timezone.timedelta(days=2),
        )
        UploadProduct.objects.create(
            facebook_product_id="prod_3",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 3 Newest"},
            modified_on=timezone.now() - timezone.timedelta(days=1),
        )

        # Call remove_duplicates
        UploadProduct.remove_duplicates(self.catalog)

        # Ensure only the most recent record is kept
        self.assertEqual(
            UploadProduct.objects.filter(facebook_product_id="prod_3").count(), 1
        )
        self.assertTrue(
            UploadProduct.objects.filter(
                facebook_product_id="prod_3", data={"name": "Test Product 3 Newest"}
            ).exists()
        )

    def test_no_duplicates_found(self):
        # Test when there are no duplicates
        UploadProduct.objects.create(
            facebook_product_id="prod_4",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 4"},
        )
        UploadProduct.objects.create(
            facebook_product_id="prod_5",
            catalog=self.catalog,
            feed=self.feed,
            data={"name": "Test Product 5"},
        )

        # Call remove_duplicates
        UploadProduct.remove_duplicates(self.catalog)

        # Ensure both records remain intact
        self.assertEqual(
            UploadProduct.objects.filter(facebook_product_id="prod_4").count(), 1
        )
        self.assertEqual(
            UploadProduct.objects.filter(facebook_product_id="prod_5").count(), 1
        )


# TODO: Testing for get_latest_products
