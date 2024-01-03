import logging

from functools import wraps

from celery import shared_task

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog
from marketplace.applications.models import App
from marketplace.clients.flows.client import FlowsClient
from marketplace.celery import app as celery_app
from marketplace.services.vtex.generic_service import VtexService
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.services.flows.service import FlowsService


logger = logging.getLogger(__name__)


@shared_task(name="sync_facebook_catalogs")
def sync_facebook_catalogs():
    apps = App.objects.filter(code="wpp-cloud")
    client = FacebookClient()
    flows_client = FlowsClient()

    for app in apps:
        wa_business_id = app.config.get("wa_business_id")
        wa_waba_id = app.config.get("wa_waba_id")

        if wa_business_id and wa_waba_id:
            local_catalog_ids = set(
                app.catalogs.values_list("facebook_catalog_id", flat=True)
            )

            all_catalogs_id, all_catalogs = list_all_catalogs_task(app, client)

            if all_catalogs_id:
                update_catalogs_on_flows_task(app, flows_client, all_catalogs)

                fba_catalogs_ids = set(all_catalogs_id)
                to_create = fba_catalogs_ids - local_catalog_ids
                to_delete = local_catalog_ids - fba_catalogs_ids

                for catalog_id in to_create:
                    details = get_catalog_details_task(client, app, catalog_id)
                    if details:
                        create_catalog_task(app, details)

                if to_delete:
                    delete_catalogs_task(app, to_delete)


def handle_exceptions(
    logger, error_msg, continue_on_exception=True, extra_info_func=None
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                extra_info_str = (
                    extra_info_func(*args, **kwargs) if extra_info_func else ""
                )
                logger.error(f"{error_msg}{extra_info_str}: {str(e)}")
                if not continue_on_exception:
                    raise

        return wrapper

    return decorator


def get_extra_info(app, *args, **kwargs):
    return f"- UUID: {app.uuid}"


@handle_exceptions(
    logger, "Error listing all catalogs for App: ", extra_info_func=get_extra_info
)
def list_all_catalogs_task(app, client):
    return client.list_all_catalogs(wa_business_id=app.config.get("wa_business_id"))


@handle_exceptions(
    logger, "Error updating catalogs for App: ", extra_info_func=get_extra_info
)
def update_catalogs_on_flows_task(app, flows_client, all_catalogs):
    flows_client.update_catalogs(str(app.flow_object_uuid), all_catalogs)


@handle_exceptions(
    logger,
    "Error getting catalog details for App",
    continue_on_exception=False,
    extra_info_func=get_extra_info,
)
def get_catalog_details_task(client, app, catalog_id):
    return client.get_catalog_details(catalog_id)


@handle_exceptions(
    logger, "Error creating catalog for App: ", extra_info_func=get_extra_info
)
def create_catalog_task(app, details):
    Catalog.objects.create(
        app=app,
        facebook_catalog_id=details["id"],
        name=details["name"],
        category=details["vertical"],
    )


@handle_exceptions(
    logger, "Error deleting catalogs for App: ", extra_info_func=get_extra_info
)
def delete_catalogs_task(app, to_delete):
    app.catalogs.filter(facebook_catalog_id__in=to_delete).delete()


@celery_app.task(name="task_insert_vtex_products")
def task_insert_vtex_products(**kwargs):
    vtex_service = VtexService()
    flows_service = FlowsService(FlowsClient())

    credentials = kwargs.get("credentials")
    catalog_uuid = kwargs.get("catalog_uuid")

    catalog = Catalog.objects.get(uuid=catalog_uuid)
    try:
        api_credentials = APICredentials(
            app_key=credentials.get("app_key"),
            app_token=credentials.get("app_token"),
            domain=credentials.get("domain"),
        )
        products = vtex_service.first_product_insert(api_credentials, catalog)
        flows_service.update_vtex_products(
            products, str(catalog.app.flow_object_uuid), catalog.facebook_catalog_id
        )
        print("Products created and sent to flows successfully")
    except Exception as e:
        logger.error(
            f"Error on insert vtex products for catalog {str(catalog.uuid)}, {e}"
        )
