"""
Service for managing VTEX App instances within a project.
"""

import time

from datetime import datetime

from typing import Optional, List

from django.db import close_old_connections
from django_redis import get_redis_connection

from dataclasses import dataclass

from marketplace.applications.models import App
from marketplace.services.vtex.private.products.service import (
    PrivateProductsService,
)
from marketplace.clients.vtex.client import VtexPrivateClient
from marketplace.services.vtex.exceptions import (
    CredentialsValidationError,
)
from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import ProductFeed
from marketplace.wpp_products.models import Catalog
from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.exceptions import (
    UnexpectedFacebookApiResponseValidationError,
)
from marketplace.services.vtex.exceptions import FileNotSendValidationError
from marketplace.services.vtex.app_manager import AppVtexManager


@dataclass
class APICredentials:
    domain: str
    app_key: str
    app_token: str

    def to_dict(self):
        return {
            "domain": self.domain,
            "app_key": self.app_key,
            "app_token": self.app_token,
        }


class VtexServiceBase:
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        self._pvt_service = None
        self._fb_service = None
        self.product_manager = ProductFacebookManager()
        self.app_manager = AppVtexManager()

    def fb_service(self, app: App) -> FacebookService:  # pragma: no cover
        access_token = app.apptype.get_access_token(app)
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class(access_token))
        return self._fb_service

    def get_private_service(
        self, app_key, app_token
    ) -> PrivateProductsService:  # pragma nocover
        if not self._pvt_service:
            client = VtexPrivateClient(app_key, app_token)
            self._pvt_service = PrivateProductsService(client)
        return self._pvt_service

    def check_is_valid_credentials(self, credentials: APICredentials) -> bool:
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        if not pvt_service.validate_private_credentials(credentials.domain):
            raise CredentialsValidationError()

        return True

    def configure(
        self, app, credentials: APICredentials, wpp_cloud_uuid, store_domain
    ) -> App:
        app.config["api_credentials"] = credentials.to_dict()
        app.config["wpp_cloud_uuid"] = wpp_cloud_uuid
        app.config["initial_sync_completed"] = False
        app.config["title"] = credentials.domain
        app.config["connected_catalog"] = False
        app.config["rules"] = [
            "exclude_alcoholic_drinks",
            "calculate_by_weight",
            "currency_pt_br",
            "unifies_id_with_seller",
        ]
        app.config["store_domain"] = store_domain
        app.configured = True
        app.save()
        return app

    def get_vtex_credentials_or_raise(self, app):
        domain = app.config["api_credentials"]["domain"]
        app_key = app.config["api_credentials"]["app_key"]
        app_token = app.config["api_credentials"]["app_token"]
        if not domain or not app_key or not app_token:
            raise CredentialsValidationError()

        return domain, app_key, app_token


class ProductInsertionService(VtexServiceBase):
    def first_product_insert(
        self,
        credentials: APICredentials,
        catalog: Catalog,
        sellers: Optional[List[str]] = None,
    ):
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        products = pvt_service.list_all_products(
            credentials.domain, catalog.vtex_app.config, sellers
        )
        if not products:
            return None

        products_csv = pvt_service.data_processor.products_to_csv(products)
        close_old_connections()
        self._send_products_to_facebook(products_csv, catalog)
        pvt_service.data_processor.clear_csv_buffer(
            products_csv
        )  # frees the memory of the csv file
        # Removed on 03-30-2024
        # close_old_connections()
        # self.product_manager.create_or_update_products_on_database(
        #     products, catalog, product_feed
        # )
        close_old_connections()
        self.app_manager.initial_sync_products_completed(catalog.vtex_app)

        return products

    def _send_products_to_facebook(self, products_csv, catalog: Catalog):
        print("Starting to upload the CSV file to Facebook")
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_name = f"csv_vtex_products_{current_time}.csv"
        product_feed = self._create_product_feed(file_name, catalog)
        self._upload_product_feed(
            catalog.app,
            product_feed.facebook_feed_id,
            products_csv,
            file_name,
        )
        print("Uploading the CSV file to Facebook completed successfully")
        return product_feed

    def _create_product_feed(self, name, catalog: Catalog) -> ProductFeed:
        print("Creating the product feed")
        service = self.fb_service(catalog.app)
        response = service.create_product_feed(catalog.facebook_catalog_id, name)

        if "id" not in response:
            raise UnexpectedFacebookApiResponseValidationError()

        product_feed = ProductFeed.objects.create(
            facebook_feed_id=response["id"],
            name=name,
            catalog=catalog,
            created_by=catalog.created_by,
        )
        return product_feed

    def _upload_product_feed(
        self, app, product_feed_id, csv_file, file_name, update_only=False
    ):
        print("Uploading the product feed to facebook")
        service = self.fb_service(app)
        response = service.upload_product_feed(
            product_feed_id, csv_file, file_name, "text/csv", update_only
        )
        if "id" not in response:
            raise FileNotSendValidationError()

        return True


class ProductUpdateService(VtexServiceBase):
    def __init__(
        self,
        api_credentials: APICredentials,
        catalog: Catalog,
        skus_ids: list,
        product_feed: ProductFeed,
    ):
        super().__init__()
        self.api_credentials = api_credentials
        self.catalog = catalog
        self.skus_ids = skus_ids
        self.product_feed = product_feed
        self.app = self.catalog.app
        self.feed_id = self.product_feed.facebook_feed_id
        self.fba_service = self.fb_service(self.app)
        self.redis = get_redis_connection()
        self.last_update_id = None

    def webhook_product_insert(self):
        pvt_service = self.get_private_service(
            self.api_credentials.app_key, self.api_credentials.app_token
        )
        products_dto = pvt_service.update_webhook_product_info(
            self.api_credentials.domain, self.skus_ids, self.catalog.vtex_app.config
        )
        if not products_dto:
            return None

        products_csv = pvt_service.data_processor.products_to_csv(products_dto)
        update_successful = self._webhook_update_products_on_facebook(products_csv)

        if update_successful is not True:
            print("Not upload products on '_webhook_update_products_on_facebook'")
            return None

        # Removed on 03-30-2024
        # self.product_manager.create_or_update_products_on_database(
        #     products_dto, self.catalog, self.product_feed
        # )
        # products_list = pvt_service.data_processor.convert_dtos_to_dicts_list(
        #     products_dto
        # )
        return products_dto

    def _webhook_update_products_on_facebook(self, products_csv) -> bool:
        upload_id_in_process = self._uploads_in_progress()

        if upload_id_in_process:
            print("There is already a feed upload in progress, waiting for completion.")
            self._wait_for_upload_completion(upload_id_in_process)

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_name = f"update_{current_time}_{self.product_feed.name}"
        upload_id = self._webhook_upload_product_feed(
            csv_file=products_csv,
            file_name=file_name,
        )
        upload_complete = self._wait_for_upload_completion(upload_id=upload_id)
        if not upload_complete:
            print("Upload did not complete within the expected time frame.")
            return False

        print("Finish update products to facebook")
        return True

    def _webhook_upload_product_feed(self, csv_file, file_name: str) -> str:
        print("Uploading the product feed to facebook")
        update_only = True
        response = self.fba_service.upload_product_feed(
            self.feed_id, csv_file, file_name, "text/csv", update_only
        )
        if "id" not in response:
            raise FileNotSendValidationError()
        return response["id"]

    def _wait_for_upload_completion(self, upload_id) -> bool:
        wait_time = 5
        max_wait_time = 20 * 60
        total_wait_time = 0
        attempt = 1

        while total_wait_time < max_wait_time:
            upload_complete = self.fba_service.get_upload_status_by_feed(
                self.feed_id, upload_id
            )
            if upload_complete:
                return True

            print(
                f"Attempt {attempt}: Waiting {wait_time} seconds "
                f"to get feed: {self.feed_id} upload {upload_id} status."
            )
            time.sleep(wait_time)
            total_wait_time += wait_time
            wait_time = min(wait_time * 2, 160)
            attempt += 1

        return False

    def _uploads_in_progress(self):
        upload_id = self.fba_service.get_in_process_uploads_by_feed(self.feed_id)
        if upload_id:
            return upload_id

        return False


class CatalogProductInsertion:
    @classmethod
    def first_product_insert_with_catalog(
        cls, vtex_app: App, catalog_id: str, sellers: Optional[List[str]] = None
    ):
        """Inserts the first product with the given catalog."""
        wpp_cloud_uuid = cls._get_wpp_cloud_uuid(vtex_app)
        credentials = cls._get_credentials(vtex_app)
        wpp_cloud = cls._get_wpp_cloud(wpp_cloud_uuid)

        catalog = cls._get_or_sync_catalog(wpp_cloud, catalog_id)
        cls._delete_existing_feeds_ifexists(catalog)
        cls._update_app_connected_catalog_flag(wpp_cloud)
        cls._link_catalog_to_vtex_app_if_needed(catalog, vtex_app)

        cls._send_insert_task(credentials, catalog, sellers)

    @staticmethod
    def _get_wpp_cloud_uuid(vtex_app) -> str:
        """Retrieves WPP Cloud UUID from VTEX app config."""
        wpp_cloud_uuid = vtex_app.config.get("wpp_cloud_uuid")
        if not wpp_cloud_uuid:
            raise ValueError(
                "The VTEX app does not have the WPP Cloud UUID in its configuration."
            )
        return wpp_cloud_uuid

    @staticmethod
    def _get_credentials(vtex_app) -> dict:
        """Extracts API credentials from VTEX app config."""
        api_credentials = vtex_app.config.get("api_credentials", {})
        if not all(
            key in api_credentials for key in ["app_key", "app_token", "domain"]
        ):
            raise ValueError("Missing one or more API credentials.")
        return api_credentials

    @staticmethod
    def _get_wpp_cloud(wpp_cloud_uuid) -> App:
        """Fetches the WPP Cloud app based on UUID."""
        try:
            return App.objects.get(uuid=wpp_cloud_uuid)
        except App.DoesNotExist:
            raise ValueError(
                f"The cloud app {wpp_cloud_uuid} linked to the VTEX app does not exist."
            )

    @classmethod
    def _get_or_sync_catalog(cls, wpp_cloud, catalog_id) -> Catalog:
        from marketplace.wpp_products.tasks import FacebookCatalogSyncService

        """Attempts to find the catalog, syncs if not found, and tries again."""
        catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
        if not catalog:
            print(
                f"Catalog {catalog_id} not found for cloud app: {wpp_cloud.uuid}. Starting catalog synchronization."
            )
            sync_service = FacebookCatalogSyncService(wpp_cloud)
            sync_service.sync_catalogs()
            catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
            if not catalog:
                raise ValueError(
                    f"Catalog {catalog_id} not found for cloud app: {wpp_cloud.uuid} after synchronization."
                )
        return catalog

    @staticmethod
    def _link_catalog_to_vtex_app_if_needed(catalog, vtex_app) -> None:
        from django.contrib.auth import get_user_model

        """Links the catalog to the VTEX app if not already linked."""
        if not catalog.vtex_app:
            User = get_user_model()
            catalog.vtex_app = vtex_app
            catalog.modified_by = User.objects.get_admin_user()
            catalog.save()
            print(
                f"Catalog {catalog.name} successfully linked to VTEX app: {vtex_app.uuid}."
            )

    @staticmethod
    def _delete_existing_feeds_ifexists(catalog) -> None:
        """Deletes existing feeds linked to the catalog and logs their IDs."""
        feeds = catalog.feeds.all()
        total = feeds.count()
        if total > 0:
            print(f"Deleting {total} feed(s) linked to catalog {catalog.name}.")
            for feed in feeds:
                print(f"Deleting feed with ID {feed.facebook_feed_id}.")
                feed.delete()
            print(
                f"All feeds linked to catalog {catalog.name} have been successfully deleted."
            )
        else:
            print(f"No feeds linked to catalog {catalog.name} to delete.")

    @staticmethod
    def _update_app_connected_catalog_flag(app) -> None:
        """Change connected catalog status"""
        connected_catalog = app.config.get("connected_catalog", None)
        if connected_catalog is not True:
            app.config["connected_catalog"] = True
            app.save()
            print("Changed connected_catalog to True")

    @staticmethod
    def _send_insert_task(
        credentials, catalog, sellers: Optional[List[str]] = None
    ) -> None:
        from marketplace.celery import app as celery_app

        """Sends the insert task to the task queue."""
        celery_app.send_task(
            name="task_insert_vtex_products",
            kwargs={
                "credentials": credentials,
                "catalog_uuid": str(catalog.uuid),
                "sellers": sellers,
            },
            queue="product_first_synchronization",
        )
        print(
            f"Catalog: {catalog.name} was sent successfully sent to task_insert_vtex_products"
        )
