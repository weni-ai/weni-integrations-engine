"""
Service for managing VTEX App instances within a project.
"""

import time
import uuid

from datetime import datetime

from django.core.cache import cache
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
    def first_product_insert(self, credentials: APICredentials, catalog: Catalog):
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        products = pvt_service.list_all_products(
            credentials.domain, catalog.vtex_app.config
        )
        if not products:
            return None

        products_csv = pvt_service.data_processor.products_to_csv(products)
        product_feed = self._send_products_to_facebook(products_csv, catalog)
        pvt_service.data_processor.clear_csv_buffer(
            products_csv
        )  # frees the memory of the csv file
        self.product_manager.create_or_update_products_on_database(
            products, catalog, product_feed
        )
        self.app_manager.initial_sync_products_completed(catalog.vtex_app)

        return pvt_service.data_processor.convert_dtos_to_dicts_list(products)

    def _send_products_to_facebook(self, products_csv, catalog: Catalog):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_name = f"csv_vtex_products_{current_time}.csv"
        product_feed = self._create_product_feed(file_name, catalog)
        self._upload_product_feed(
            catalog.app,
            product_feed.facebook_feed_id,
            products_csv,
            file_name,
        )
        return product_feed

    def _create_product_feed(self, name, catalog: Catalog) -> ProductFeed:
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
        webhook_data: dict,
        product_feed: ProductFeed,
    ):
        super().__init__()
        self.api_credentials = api_credentials
        self.catalog = catalog
        self.webhook_data = webhook_data
        self.product_feed = product_feed
        self.sku_id = self.webhook_data["IdSku"]
        self.app = self.catalog.app
        self.feed_id = self.product_feed.facebook_feed_id
        self.fba_service = self.fb_service(self.app)
        self.redis = get_redis_connection()
        self.last_update_id = None

    def webhook_product_insert(self):
        update_id = self.generate_update_id()
        self.set_last_update_id(update_id)

        can_sync = self._verify_product_sync_queue()
        if can_sync is False:
            return can_sync

        pvt_service = self.get_private_service(
            self.api_credentials.app_key, self.api_credentials.app_token
        )
        products_dto = pvt_service.update_webhook_product_info(
            self.api_credentials.domain, self.webhook_data, self.catalog.vtex_app.config
        )
        if not products_dto:
            return None

        products_csv = pvt_service.data_processor.products_to_csv(products_dto)

        self._webhook_update_products_on_facebook(products_csv)
        if self.is_latest_update(update_id):
            self.product_manager.create_or_update_products_on_database(
                products_dto, self.catalog, self.product_feed
            )
            return pvt_service.data_processor.convert_dtos_to_dicts_list(
                products_dto
            )  # TODO: Fix: when there is more than one execution this block is returning None for the task return

    def _webhook_upload_product_feed(self, csv_file, file_name: str) -> str:
        update_only = True
        response = self.fba_service.upload_product_feed(
            self.feed_id, csv_file, file_name, "text/csv", update_only
        )
        if "id" not in response:
            raise FileNotSendValidationError()
        return response["id"]

    def _verify_product_sync_queue(self) -> bool:
        """
        Check for pending sync for a specific product SKU within a feed.

        Returns:
        - bool: False if another sync is pending after the current sync,
        True if no pending items and can proceed.

        Note:
        - False means a re-sync is queued after current sync.
        - True means no pending sync, process can continue.
        """
        if self.redis.get(self._get_key_uploading()):
            key_re_sync = f"lock:re-sync-product_sku-{self.feed_id}-{self.sku_id}"
            cache.set(key_re_sync, True)
            return False

        return True

    def _webhook_update_products_on_facebook(self, products_csv) -> bool:
        key_uploading = self._get_key_uploading()
        key_re_sync = self._get_key_resync()

        if self.redis.get(key_uploading):
            cache.set(key_re_sync, True)
        else:
            with self.redis.lock(key_uploading):
                current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
                file_name = f"update_{current_time}_{self.product_feed.name}"
                upload_id = self._webhook_upload_product_feed(
                    csv_file=products_csv,
                    file_name=file_name,
                )
                upload_complete = self._wait_for_upload_completion(upload_id=upload_id)
                if not upload_complete:
                    print("Upload did not complete within the expected time frame.")

            if cache.get(key_re_sync):
                cache.delete(key_re_sync)
                self.webhook_product_insert()

        print("Finish update products to facebook")
        return True

    def _wait_for_upload_completion(self, upload_id) -> bool:
        wait_time = 5
        max_wait_time = 20 * 60
        total_wait_time = 0

        while total_wait_time < max_wait_time:
            upload_complete = self.fba_service.get_upload_status_by_feed(
                self.feed_id, upload_id
            )

            if upload_complete:
                return True

            print(
                f"Waiting {wait_time} seconds to get feed: {self.feed_id} upload status."
            )
            time.sleep(wait_time)
            total_wait_time += wait_time
            wait_time = min(wait_time * 2, 160)

        return False

    def _get_key_uploading(self) -> str:
        return f"lock:product_sku_uploading-{self.feed_id}-{self.sku_id}"

    def _get_key_resync(self) -> str:
        return f"lock:re-sync-product_sku-{self.feed_id}-{self.sku_id}"

    def generate_update_id(self):
        """Gera um identificador único para a atualização."""
        return str(uuid.uuid4())

    def set_last_update_id(self, update_id):
        """Define o identificador da última atualização."""
        self.last_update_id = update_id

    def is_latest_update(self, update_id):
        """Verifica se o update_id é o mais recente."""
        return update_id == self.last_update_id
