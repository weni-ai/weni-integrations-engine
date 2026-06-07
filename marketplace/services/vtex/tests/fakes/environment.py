"""
Reusable in-memory VTEX environment for tests.

`VtexTestEnvironment` bundles the database fixtures (vtex App, wpp-cloud App and a
linked Catalog) with a `FakeVtexClient` and a real `PrivateProductsService`, so
catalog sync/upload flows can be exercised end-to-end without touching VTEX/Meta.

Example:
    env = VtexTestEnvironment.create().add_product("1047", price=1500)
    details = env.service.get_product_details("1047", env.domain)
"""

import uuid as uuid_lib

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.tests.fakes.vtex_client import FakeVtexClient
from marketplace.wpp_products.models import Catalog


User = get_user_model()


@dataclass
class VtexTestEnvironment:
    user: object
    vtex_app: App
    wpp_cloud_app: App
    catalog: Catalog
    client: FakeVtexClient
    service: PrivateProductsService
    store_domain: str
    domain: str

    @classmethod
    def create(
        cls,
        *,
        project_uuid: Optional[str] = None,
        store_domain: str = "store.myvtex.com",
        domain: Optional[str] = None,
        facebook_catalog_id: str = "123456789",
        catalog_name: str = "Fake Catalog",
        domain_valid: bool = True,
        credentials_valid: bool = True,
        config: Optional[dict] = None,
    ) -> "VtexTestEnvironment":
        """Create the DB fixtures and wire the fakes into a ready-to-use environment."""
        project_uuid = project_uuid or str(uuid_lib.uuid4())
        domain = domain or store_domain

        user = User.objects.create_user(
            email=f"vtex-fake-{uuid_lib.uuid4().hex[:8]}@marketplace.ai",
            password="fake@pass#$",
        )
        vtex_config = config or {
            "api_credentials": {
                "app_key": "fake-key",
                "app_token": "fake-token",
                "domain": domain,
            },
            "initial_sync_completed": True,
            "connected_catalog": True,
        }
        vtex_app = App.objects.create(
            code="vtex",
            created_by=user,
            project_uuid=project_uuid,
            platform=App.PLATFORM_VTEX,
            config=vtex_config,
        )
        wpp_cloud_app = App.objects.create(
            code="wpp-cloud",
            created_by=user,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )
        catalog = Catalog.objects.create(
            app=wpp_cloud_app,
            vtex_app=vtex_app,
            facebook_catalog_id=facebook_catalog_id,
            name=catalog_name,
            created_by=user,
        )
        client = FakeVtexClient(
            domain_valid=domain_valid, credentials_valid=credentials_valid
        )
        service = PrivateProductsService(client)

        return cls(
            user=user,
            vtex_app=vtex_app,
            wpp_cloud_app=wpp_cloud_app,
            catalog=catalog,
            client=client,
            service=service,
            store_domain=store_domain,
            domain=domain,
        )

    @property
    def project_uuid(self) -> str:
        return str(self.vtex_app.project_uuid)

    def add_product(self, sku_id, **kwargs) -> "VtexTestEnvironment":
        self.client.add_product(sku_id, **kwargs)
        return self

    def add_seller(self, seller_id, **kwargs) -> "VtexTestEnvironment":
        self.client.add_seller(seller_id, **kwargs)
        return self
