from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
import importlib
import sys
import types


def import_tasks_module():
    """
    Imports tasks module with a stub for marketplace.services.vtex.generic_service
    to avoid deep imports and circular dependencies during tests.
    """
    module_name = "marketplace.services.vtex.generic_service"
    if module_name not in sys.modules:
        stub = types.ModuleType(module_name)
        # Minimal stubs used by tasks

        class ProductUpdateService:  # noqa: D401
            def __init__(self, *args, **kwargs):
                pass

            def process_batch_sync(self):
                return []

        class ProductInsertionService:  # noqa: D401
            def __init__(self, *args, **kwargs):
                pass

            def first_product_insert(self, *args, **kwargs):
                return []

        class VtexServiceBase:  # noqa: D401
            def get_vtex_credentials_or_raise(self, *args, **kwargs):
                return MagicMock()

        class ProductInsertionBySellerService:  # noqa: D401
            def insertion_products_by_seller(self, *args, **kwargs):
                return True

        class APICredentials:  # noqa: D401
            def __init__(self, *args, **kwargs):
                pass

        stub.ProductUpdateService = ProductUpdateService
        stub.ProductInsertionService = ProductInsertionService
        stub.VtexServiceBase = VtexServiceBase
        stub.ProductInsertionBySellerService = ProductInsertionBySellerService
        stub.APICredentials = APICredentials
        sys.modules[module_name] = stub

    return importlib.import_module("marketplace.wpp_products.tasks")


class TestFacebookCatalogSyncService(SimpleTestCase):
    def _make_app(self, config=None):
        app = MagicMock()
        app.uuid = "app-uuid"
        app.name = "App"
        app.flow_object_uuid = "flow-uuid"
        app.config = config or {"wa_business_id": "B", "wa_waba_id": "W"}
        app.catalogs.values_list.return_value = []
        return app

    def test_sync_catalogs_already_locked(self):
        app = self._make_app()
        with patch(
            "marketplace.wpp_products.tasks.get_redis_connection"
        ) as mock_conn, patch("marketplace.wpp_products.tasks.FacebookClient"):
            redis = MagicMock()
            redis.get.return_value = "locked"
            mock_conn.return_value = redis
            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.sync_catalogs()
            # Should return early
            self.assertFalse(redis.lock.called)

    def test_sync_catalogs_missing_ids(self):
        app = self._make_app(config={"wa_business_id": None, "wa_waba_id": None})
        with patch(
            "marketplace.wpp_products.tasks.get_redis_connection"
        ) as mock_conn, patch("marketplace.wpp_products.tasks.FacebookClient"):
            # Lock context
            cm = MagicMock()
            cm.__enter__.return_value = True
            cm.__exit__.return_value = False
            redis = MagicMock()
            redis.get.return_value = None
            redis.lock.return_value = cm
            mock_conn.return_value = redis
            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.client = MagicMock()
            svc.sync_catalogs()
            svc.client.list_all_catalogs.assert_not_called()

    def test_sync_catalogs_happy_path(self):
        app = self._make_app()
        with patch(
            "marketplace.wpp_products.tasks.get_redis_connection"
        ) as mock_conn, patch("marketplace.wpp_products.tasks.FacebookClient"):
            cm = MagicMock()
            cm.__enter__.return_value = True
            cm.__exit__.return_value = False
            redis = MagicMock()
            redis.get.return_value = None
            redis.lock.return_value = cm
            mock_conn.return_value = redis

            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.client = MagicMock()
            svc.flows_client = MagicMock()

            svc._list_all_catalogs = MagicMock(return_value=(["1"], [{"id": "1"}]))
            svc._get_active_catalog = MagicMock(return_value="active")
            svc._update_catalogs_on_flows = MagicMock()
            svc._sync_local_catalogs = MagicMock()

            svc.sync_catalogs()

            svc._update_catalogs_on_flows.assert_called_once()
            svc._sync_local_catalogs.assert_called_once_with(["1"], set())

    def test_list_all_catalogs_error(self):
        app = self._make_app()
        with patch("marketplace.wpp_products.tasks.FacebookClient"):
            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.client = MagicMock()
            svc.client.list_all_catalogs.side_effect = Exception("fail")
            ids, cats = svc._list_all_catalogs()
            self.assertEqual(ids, [])
            self.assertEqual(cats, [])

    def test_get_active_catalog(self):
        app = self._make_app()
        with patch("marketplace.wpp_products.tasks.FacebookClient"):
            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.client = MagicMock()
            svc.client.get_connected_catalog.return_value = {"data": [{"id": "X"}]}
            self.assertEqual(svc._get_active_catalog("W"), "X")

            svc.client.get_connected_catalog.return_value = {"data": []}
            self.assertIsNone(svc._get_active_catalog("W"))

            svc.client.get_connected_catalog.side_effect = Exception("err")
            self.assertIsNone(svc._get_active_catalog("W"))

    def test_sync_local_catalogs_create_and_delete_with_error(self):
        app = self._make_app()
        with patch("marketplace.wpp_products.tasks.FacebookClient"):
            tasks = import_tasks_module()
            svc = tasks.FacebookCatalogSyncService(app)
            svc.client = MagicMock()
            svc.client.get_catalog_details.return_value = {
                "id": "1",
                "name": "n",
                "vertical": "v",
            }
            # Patch ORM
            with patch("marketplace.wpp_products.tasks.Catalog") as mock_catalog:
                # First create raises, then continue
                mock_catalog.objects.create.side_effect = [Exception("db"), MagicMock()]
                app.catalogs.filter.return_value.delete.return_value = None

                svc._sync_local_catalogs(
                    all_catalogs_id={"1", "2"}, local_catalog_ids={"2", "3"}
                )

                # Should attempt to create for '1'
                self.assertTrue(mock_catalog.objects.create.called)
                # Should delete '3'
                app.catalogs.filter.assert_called_with(facebook_catalog_id__in={"3"})


class TestTasks(SimpleTestCase):
    def test_task_upload_vtex_products_happy_path(self):
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks.App") as mock_app, patch(
            "marketplace.wpp_products.tasks.get_redis_connection"
        ) as mock_conn, patch(
            "marketplace.wpp_products.tasks.ProductBatchUploader"
        ) as mock_uploader_cls:
            app = MagicMock()
            catalog = MagicMock()
            catalog.vtex_app = True
            app.vtex_catalogs = MagicMock()
            qs = MagicMock()
            qs.exists.return_value = True
            qs.__iter__.return_value = iter([catalog])
            app.vtex_catalogs.all.return_value = qs
            mock_app.objects.get.return_value = app

            redis = MagicMock()
            redis.set.return_value = True
            mock_conn.return_value = redis

            uploader = MagicMock()
            mock_uploader_cls.return_value = uploader

            tasks.task_upload_vtex_products(app_vtex_uuid="uuid", priority=5)

            mock_uploader_cls.assert_called_once()
            uploader.process_and_upload.assert_called_once()
            redis.delete.assert_called()  # lock released

    def test_task_enqueue_webhook_calls(self):
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks._enqueue_webhook") as mock_enqueue:
            tasks.task_enqueue_webhook("a", "s", "sku")
            mock_enqueue.assert_called_once_with("a", "s", "sku")

    def test_task_dequeue_webhooks_flow(self):
        tasks = import_tasks_module()
        with patch(
            "marketplace.wpp_products.tasks.RedisQueue"
        ) as mock_queue_cls, patch(
            "marketplace.wpp_products.tasks.celery_app"
        ) as mock_celery:
            queue = MagicMock()
            queue.length.side_effect = [2, 2, 0]
            queue.get_batch.return_value = ["s#1", "s#2"]
            queue.redis = MagicMock()
            queue.redis.set.return_value = True
            mock_queue_cls.return_value = queue

            tasks.task_dequeue_webhooks(
                app_uuid="app", celery_queue="q", priority=1, batch_size=2
            )

            mock_celery.send_task.assert_called_once()
            queue.redis.delete.assert_called()  # lock removed

    def test_task_update_webhook_batch_products_paths(self):
        # DEFAULT without initial sync -> None
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app:
            mock_cache.get.return_value = None
            vtex_app = MagicMock()
            vtex_app.config = {"initial_sync_completed": False}
            mock_app.objects.get.return_value = vtex_app

            res = tasks.task_update_webhook_batch_products("app", ["s#1"], priority=0)
            self.assertIsNone(res)

        # Non-DEFAULT, no catalog -> None
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app, patch(
            "marketplace.wpp_products.tasks.VtexServiceBase"
        ) as mock_base:
            mock_cache.get.return_value = None
            vtex_app = MagicMock()
            vtex_app.config = {"initial_sync_completed": True}
            vtex_app.vtex_catalogs.first.return_value = None
            mock_app.objects.get.return_value = vtex_app
            mock_base.return_value.get_vtex_credentials_or_raise.return_value = (
                MagicMock()
            )

            res = tasks.task_update_webhook_batch_products("app", ["s#1"], priority=1)
            self.assertIsNone(res)

        # API_ONLY returns processed products
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app, patch(
            "marketplace.wpp_products.tasks.VtexServiceBase"
        ) as mock_base, patch(
            "marketplace.wpp_products.tasks.ProductUpdateService"
        ) as mock_service:
            mock_cache.get.return_value = None
            vtex_app = MagicMock()
            vtex_app.config = {"initial_sync_completed": True}
            catalog = MagicMock()
            vtex_app.vtex_catalogs.first.return_value = catalog
            mock_app.objects.get.return_value = vtex_app
            mock_base.return_value.get_vtex_credentials_or_raise.return_value = (
                MagicMock()
            )

            instance = MagicMock()
            instance.process_batch_sync.return_value = ["p"]
            mock_service.return_value = instance

            res = tasks.task_update_webhook_batch_products("app", ["s#1"], priority=2)
            self.assertEqual(res, ["p"])

    def test_task_insert_vtex_products_missing_params(self):
        # No credentials/cat -> returns
        tasks = import_tasks_module()
        res = tasks.task_insert_vtex_products(credentials=None, catalog_uuid=None)
        self.assertIsNone(res)

    def test_task_insert_vtex_products_exception_and_finally(self):
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks.Catalog") as mock_catalog, patch(
            "marketplace.wpp_products.tasks.ProductInsertionService"
        ) as mock_service, patch(
            "marketplace.wpp_products.tasks.close_old_connections"
        ) as mock_close:
            catalog = MagicMock()
            catalog.name = "CAT"
            mock_catalog.objects.get.return_value = catalog
            mock_service.return_value.first_product_insert.side_effect = Exception(
                "oops"
            )
            tasks.task_insert_vtex_products(
                credentials={"app_key": "a", "app_token": "b", "domain": "d"},
                catalog_uuid="c",
            )
            mock_close.assert_called_once()

    def test_task_insert_vtex_products_by_sellers_paths(self):
        # Missing sellers and flag -> returns
        tasks = import_tasks_module()
        res = tasks.task_insert_vtex_products_by_sellers(
            credentials={"app_key": "a", "app_token": "b", "domain": "d"},
            catalog_uuid="c",
        )
        self.assertIsNone(res)

        # Missing credentials/cat -> returns
        res = tasks.task_insert_vtex_products_by_sellers(
            sellers=["s"],
            sync_all_sellers=False,
            credentials=None,
            catalog_uuid=None,
        )
        self.assertIsNone(res)

        # Happy path with lock, insertion False -> returns
        with patch("marketplace.wpp_products.tasks.Catalog") as mock_catalog, patch(
            "marketplace.wpp_products.tasks.ProductInsertionBySellerService"
        ) as mock_service, patch(
            "marketplace.wpp_products.tasks.SellerSyncUtils"
        ) as mock_sync:
            catalog = MagicMock()
            catalog.name = "CAT"
            catalog.vtex_app.uuid = "v-uuid"
            mock_catalog.objects.get.return_value = catalog
            mock_sync.create_lock.return_value = "lock"
            mock_service.return_value.insertion_products_by_seller.return_value = False

            tasks.task_insert_vtex_products_by_sellers(
                credentials={"app_key": "a", "app_token": "b", "domain": "d"},
                catalog_uuid="c",
                sellers=["s"],
                sync_all_sellers=False,
            )
            mock_sync.release_lock.assert_called_once_with("v-uuid")

    def test_task_cleanup_vtex_logs_and_uploads(self):
        tasks = import_tasks_module()
        with patch(
            "marketplace.wpp_products.tasks.ProductUploadLog"
        ) as mock_log, patch(
            "marketplace.wpp_products.tasks.WebhookLog"
        ) as mock_webhook, patch(
            "marketplace.wpp_products.tasks.UploadProduct"
        ) as mock_upload:
            mock_upload.objects.filter.return_value.exists.side_effect = [True, True]
            tasks.task_cleanup_vtex_logs_and_uploads()
            mock_log.objects.all.return_value.delete.assert_called_once()
            mock_webhook.objects.all.return_value.delete.assert_called_once()
            self.assertEqual(
                mock_upload.objects.filter.return_value.update.call_count, 2
            )

    def test_send_sync_paths(self):
        # App does not exist
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app:
            mock_cache.get.return_value = None
            mock_app.objects.get.side_effect = mock_app.DoesNotExist()
            res = tasks.send_sync("app", {})
            self.assertIsNone(res)

        # Initial sync not completed
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app:
            app = MagicMock()
            app.config = {"initial_sync_completed": False}
            mock_cache.get.return_value = app
            res = tasks.send_sync("app", {"IdSku": "1"})
            self.assertIsNone(res)

        # Seller not allowed
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks.App"
        ) as mock_app, patch(
            "marketplace.wpp_products.tasks._extract_sellers_ids", return_value="X"
        ):
            app = MagicMock()
            app.config = {
                "initial_sync_completed": True,
                "sync_specific_sellers": ["Y"],
            }
            mock_cache.get.return_value = app
            res = tasks.send_sync("app", {"IdSku": "1"})
            self.assertIsNone(res)

        # Missing sku
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache:
            app = MagicMock()
            app.config = {"initial_sync_completed": True}
            mock_cache.get.return_value = app
            res = tasks.send_sync("app", {})
            self.assertIsNone(res)

        # Enqueue false -> no schedule
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks._enqueue_webhook", return_value=False
        ), patch(
            "marketplace.wpp_products.tasks._schedule_dequeue_with_debounce"
        ) as mock_sched:
            app = MagicMock()
            app.config = {"initial_sync_completed": True}
            mock_cache.get.return_value = app
            res = tasks.send_sync("app", {"IdSku": "1", "An": "A"})
            mock_sched.assert_not_called()

        # Enqueue true -> schedule called
        with patch("marketplace.wpp_products.tasks.cache") as mock_cache, patch(
            "marketplace.wpp_products.tasks._enqueue_webhook", return_value=True
        ), patch(
            "marketplace.wpp_products.tasks._schedule_dequeue_with_debounce"
        ) as mock_sched:
            app = MagicMock()
            app.config = {"initial_sync_completed": True, "celery_queue_name": "q"}
            mock_cache.get.return_value = app
            res = tasks.send_sync("app", {"IdSku": "1", "An": "A"})
            mock_sched.assert_called_once()

    def test_get_projects_with_vtex_app_and_sync_facebook_catalogs(self):
        # get_projects_with_vtex_app
        tasks = import_tasks_module()
        with patch("marketplace.wpp_products.tasks.App") as mock_app:
            a1 = MagicMock()
            a1.project_uuid = "p1"
            a2 = MagicMock()
            a2.project_uuid = None
            mock_app.objects.filter.return_value = [a1, a2]
            res = tasks.get_projects_with_vtex_app()
            self.assertEqual(res, ["p1"])

        # sync_facebook_catalogs
        with patch(
            "marketplace.wpp_products.tasks.get_projects_with_vtex_app",
            return_value=["p"],
        ), patch("marketplace.wpp_products.tasks.App") as mock_app, patch(
            "marketplace.wpp_products.tasks.FacebookCatalogSyncService"
        ) as mock_service:
            mock_app.objects.filter.return_value = [MagicMock(), MagicMock()]
            instance = MagicMock()
            mock_service.return_value = instance

            tasks.sync_facebook_catalogs()
            self.assertEqual(instance.sync_catalogs.call_count, 2)

    def test_extract_sellers_ids(self):
        tasks = import_tasks_module()
        self.assertEqual(
            tasks._extract_sellers_ids({"An": "A", "SellerChain": "B"}), "B"
        )
        self.assertEqual(tasks._extract_sellers_ids({"An": "A"}), "A")
        self.assertIsNone(tasks._extract_sellers_ids({}))
