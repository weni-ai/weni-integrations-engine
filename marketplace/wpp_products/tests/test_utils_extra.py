from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from marketplace.wpp_products.utils import (
    ProductUploadManager,
    ProductBatchFetcher,
    SellerSyncUtils,
    UploadManager,
    ProductSyncMetaPolices,
    extract_sku_id,
    ProductBatchUploader,
    RedisQueue,
    exceptions,
)


class TestExtractSkuId(SimpleTestCase):
    def test_extract_sku_id_valid(self):
        self.assertEqual(extract_sku_id("123#abc"), 123)

    def test_extract_sku_id_invalid(self):
        with self.assertRaises(ValueError):
            extract_sku_id("abc#x")


class TestProductUploadManager(SimpleTestCase):
    @patch("marketplace.wpp_products.utils.UploadProduct")
    def test_mark_products_as_sent(self, mock_upload):
        mock_upload.objects.filter.return_value.update.return_value = 3
        mgr = ProductUploadManager()
        mgr.mark_products_as_sent(["1", "2"])
        mock_upload.objects.filter.assert_called_once()
        mock_upload.objects.filter.return_value.update.assert_called_once_with(
            status="success"
        )

    @patch("marketplace.wpp_products.utils.UploadProduct")
    def test_mark_products_as_error(self, mock_upload):
        mock_upload.objects.filter.return_value.update.return_value = 2
        mgr = ProductUploadManager()
        mgr.mark_products_as_error(["1", "2"])
        mock_upload.objects.filter.assert_called_once()
        mock_upload.objects.filter.return_value.update.assert_called_once_with(
            status="error"
        )


class QuerySetFake:
    def __init__(self):
        self._exists = True

    def exists(self):
        return self._exists

    def values_list(self, field, flat=False):
        if field == "id":
            return [11, 22]
        if field == "facebook_product_id":
            return ["11#x", "22#y"]
        return []


class TestProductBatchFetcher(SimpleTestCase):
    @patch("marketplace.wpp_products.utils.UploadProduct")
    def test_next_returns_products_and_marks_processing(self, mock_upload):
        qs = QuerySetFake()
        mock_upload.get_latest_products.return_value = qs

        fetcher = ProductBatchFetcher(catalog=MagicMock(name="Cat"), batch_size=2)
        products, fb_ids = next(fetcher)

        self.assertIs(products, qs)
        self.assertEqual(fb_ids, ["11#x", "22#y"])
        mock_upload.objects.filter.assert_called_once()
        mock_upload.objects.filter.return_value.update.assert_called_once_with(
            status="processing"
        )

    @patch("marketplace.wpp_products.utils.UploadProduct")
    def test_next_raises_stop_iteration_when_empty(self, mock_upload):
        qs = QuerySetFake()
        qs._exists = False
        mock_upload.get_latest_products.return_value = qs

        fetcher = ProductBatchFetcher(catalog=MagicMock(name="Cat"), batch_size=2)
        with self.assertRaises(StopIteration):
            next(fetcher)


class TestSellerSyncUtils(SimpleTestCase):
    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_create_lock_success_and_fail(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        redis.set.return_value = True
        key = SellerSyncUtils.create_lock("app1", ["s1"])
        self.assertEqual(key, "sync-sellers:app1")

        redis.set.return_value = None
        key2 = SellerSyncUtils.create_lock("app1", ["s1"])
        self.assertIsNone(key2)

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_release_lock(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        SellerSyncUtils.release_lock("app1")
        redis.delete.assert_called_once_with("sync-sellers:app1")

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_get_lock_data(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        redis.get.return_value = '{"a":1}'
        out = SellerSyncUtils.get_lock_data("k")
        self.assertEqual(out, {"a": 1})

        redis.get.return_value = None
        self.assertIsNone(SellerSyncUtils.get_lock_data("k"))


class TestUploadManager(SimpleTestCase):
    @patch("marketplace.wpp_products.utils.celery_app")
    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_check_and_start_upload_no_lock_starts_task(self, mock_conn, mock_celery):
        redis = MagicMock()
        mock_conn.return_value = redis
        redis.exists.return_value = 0

        UploadManager.check_and_start_upload("app1", priority=7)

        mock_celery.send_task.assert_called_once()

    @patch("marketplace.wpp_products.utils.celery_app")
    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_check_and_start_upload_has_lock_no_task(self, mock_conn, mock_celery):
        redis = MagicMock()
        mock_conn.return_value = redis
        redis.exists.return_value = 1

        UploadManager.check_and_start_upload("app1")

        mock_celery.send_task.assert_not_called()


class TestProductSyncMetaPolices(SimpleTestCase):
    def _make_catalog(self, config=None):
        app = MagicMock()
        app.uuid = "app-uuid"
        app.name = "AppName"
        app.apptype.get_system_access_token.return_value = "tok"
        app.config = config or {"wa_business_id": "B", "wa_waba_id": "W"}
        catalog = MagicMock()
        catalog.app = app
        catalog.facebook_catalog_id = "cat-1"
        catalog.name = "CatalogName"
        return catalog

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    @patch("marketplace.wpp_products.utils.FacebookClient")
    def test_sync_products_polices_already_running(self, mock_client, mock_conn):
        redis = MagicMock()
        redis.get.return_value = "locked"
        mock_conn.return_value = redis

        p = ProductSyncMetaPolices(self._make_catalog())
        # Override heavy deps
        p.client = MagicMock()
        p.redis = redis

        p.sync_products_polices()
        p.client.list_unapproved_products.assert_not_called()

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    @patch("marketplace.wpp_products.utils.FacebookClient")
    def test_sync_products_polices_missing_ids(self, mock_client, mock_conn):
        redis = MagicMock()
        cm = MagicMock()
        cm.__enter__.return_value = True
        cm.__exit__.return_value = False
        redis.get.return_value = None
        redis.lock.return_value = cm
        mock_conn.return_value = redis

        p = ProductSyncMetaPolices(
            self._make_catalog(config={"wa_business_id": None, "wa_waba_id": None})
        )
        p.client = MagicMock()
        p.redis = redis

        p.sync_products_polices()
        p.client.list_unapproved_products.assert_not_called()

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    @patch("marketplace.wpp_products.utils.FacebookClient")
    def test_sync_products_polices_calls_sync_local_and_handles_exception(
        self, mock_client, mock_conn
    ):
        redis = MagicMock()
        cm = MagicMock()
        cm.__enter__.return_value = True
        cm.__exit__.return_value = False
        redis.get.return_value = None
        redis.lock.return_value = cm
        mock_conn.return_value = redis

        p = ProductSyncMetaPolices(self._make_catalog())
        p.redis = redis
        p.client = MagicMock()
        p._list_unapproved_products = MagicMock(
            return_value=[{"id": "p1", "retailer_id": "1#x"}]
        )
        p._sync_local_products = MagicMock()

        p.sync_products_polices()
        p._sync_local_products.assert_called_once()

        # Now simulate exception inside _sync_local_products
        p._sync_local_products.side_effect = Exception("fail")
        p.sync_products_polices()  # logs error, no raise

    @patch("marketplace.wpp_products.utils.get_redis_connection")
    @patch("marketplace.wpp_products.utils.FacebookClient")
    def test_sync_products_polices_lock_error(self, mock_client, mock_conn):
        redis = MagicMock()
        redis.get.return_value = None
        # Simulate lock error
        redis.lock.side_effect = exceptions.LockError("lock-fail")
        mock_conn.return_value = redis

        p = ProductSyncMetaPolices(self._make_catalog())
        p.redis = redis
        p.client = MagicMock()

        p.sync_products_polices()  # should handle lock error

    def test_list_unapproved_products_delegates(self):
        p = ProductSyncMetaPolices(self._make_catalog())
        p.client = MagicMock()
        p.client.list_unapproved_products.return_value = ["a"]
        out = p._list_unapproved_products()
        self.assertEqual(out, ["a"])

    @patch("marketplace.wpp_products.utils.ProductValidation")
    def test_save_invalid_products(self, mock_validation):
        p = ProductSyncMetaPolices(self._make_catalog())
        # First item: is_valid False -> skip creation
        # Next two: None -> create True and then False
        q = MagicMock()
        q.values_list.return_value.first.side_effect = [False, None, None]
        mock_validation.objects.filter.return_value = q

        created_obj = MagicMock()
        mock_validation.objects.get_or_create.side_effect = [
            (created_obj, True),
            (created_obj, False),
        ]

        invalids = [
            {"sku_id": 1, "rejection_reason": "x"},
            {"sku_id": 2, "rejection_reason": "y"},
            {"sku_id": 3, "rejection_reason": "z"},
        ]
        p._save_invalid_products(invalids)

        # get_or_create called for last two only
        self.assertEqual(mock_validation.objects.get_or_create.call_count, 2)

    def test_sync_local_products_builds_deletes_and_saves(self):
        p = ProductSyncMetaPolices(self._make_catalog())
        p._delete_products_in_batch = MagicMock()
        p._save_invalid_products = MagicMock()
        # Provide one valid product
        products = [{"id": "1", "retailer_id": "123#x"}]
        p._sync_local_products(products)
        # One deletion for valid item
        p._delete_products_in_batch.assert_called_once()
        p._save_invalid_products.assert_called_once()


class TestProductBatchUploader(SimpleTestCase):
    def _make_catalog(self):
        app = MagicMock()
        app.apptype.get_system_access_token.return_value = "tok"
        catalog = MagicMock()
        catalog.app = app
        catalog.name = "CAT"
        catalog.facebook_catalog_id = "cat-1"
        catalog.vtex_app = "vt"
        return catalog

    def test_initialize_fb_service_with_injected_classes(self):
        uploader = ProductBatchUploader(self._make_catalog())
        with patch("marketplace.wpp_products.utils.FacebookService") as mock_service:
            fake_fb_service = MagicMock()
            mock_service.return_value = fake_fb_service
            svc = uploader.initialize_fb_service()
            self.assertIs(svc, fake_fb_service)

    def test_create_batch_payload(self):
        uploader = ProductBatchUploader(self._make_catalog())
        product1 = MagicMock()
        product1.data = {"a": 1}
        product2 = MagicMock()
        product2.data = {"b": 2}
        payload = uploader.create_batch_payload([product1, product2])
        self.assertEqual(payload["item_type"], "PRODUCT_ITEM")
        self.assertEqual(len(payload["requests"]), 2)

    def test_send_to_meta_success_and_fail_and_exception(self):
        uploader = ProductBatchUploader(self._make_catalog())
        uploader.fb_service = MagicMock()

        uploader.fb_service.upload_batch.return_value = {"handles": [1]}
        self.assertTrue(uploader.send_to_meta({"x": 1}))

        uploader.fb_service.upload_batch.return_value = {}
        self.assertFalse(uploader.send_to_meta({"x": 1}))

        uploader.fb_service.upload_batch.side_effect = Exception("boom")
        self.assertFalse(uploader.send_to_meta({"x": 1}))

    @patch("time.sleep", return_value=None)
    def test_process_and_upload_iterates_and_marks_status(self, _sleep):
        uploader = ProductBatchUploader(self._make_catalog(), priority=0)
        uploader.send_to_meta = MagicMock(side_effect=[True, False])

        class DummyPM:
            def __init__(self):
                p1 = MagicMock()
                p1.data = {"a": 1}
                p2 = MagicMock()
                p2.data = {"b": 2}
                self.items = [([p1], ["11#x"]), ([p2], ["22#y"])]
                self.idx = 0
                self.mark_products_as_sent = MagicMock()
                self.mark_products_as_error = MagicMock()

            def __iter__(self):
                return self

            def __next__(self):
                if self.idx < len(self.items):
                    val = self.items[self.idx]
                    self.idx += 1
                    return val
                raise StopIteration

        uploader.product_manager = DummyPM()
        redis = MagicMock()
        uploader.log_sent_products = MagicMock()

        uploader.process_and_upload(
            redis_client=redis, lock_key="lk", lock_expiration_time=60
        )

        uploader.product_manager.mark_products_as_sent.assert_called_once_with(["11#x"])
        uploader.product_manager.mark_products_as_error.assert_called_once_with(
            ["22#y"]
        )
        self.assertEqual(redis.expire.call_count, 2)
        uploader.log_sent_products.assert_called_once()

    @patch("marketplace.wpp_products.utils.ProductUploadLog")
    def test_log_sent_products(self, mock_log):
        uploader = ProductBatchUploader(self._make_catalog())
        uploader.log_sent_products(["11#x", "22#y"])
        self.assertEqual(mock_log.objects.create.call_count, 2)


class TestRedisQueue(SimpleTestCase):
    @patch("marketplace.wpp_products.utils.get_redis_connection")
    def test_insert_and_remove_and_order_and_length_and_get_batch(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis

        rq = RedisQueue("q")
        rq.redis = redis  # ensure using our mock

        # insert when exists
        redis.zscore.return_value = 1.0
        self.assertFalse(rq.insert("v1"))

        # insert new
        redis.zscore.return_value = None
        self.assertTrue(rq.insert("v2"))
        redis.zadd.assert_called()
        redis.expire.assert_called()

        # remove empty
        redis.zrange.return_value = []
        self.assertIsNone(rq.remove())

        # remove with item
        redis.zrange.return_value = [b"v2"]
        v = rq.remove()
        self.assertEqual(v, "v2")
        redis.zrem.assert_called()

        # order
        redis.zrange.return_value = [b"a", b"b"]
        self.assertEqual(rq.order(), ["a", "b"])

        # length
        redis.zcard.return_value = 5
        self.assertEqual(rq.length(), 5)

        # get_batch
        redis.zrange.return_value = [b"c", b"d"]
        out = rq.get_batch(2)
        self.assertEqual(out, ["c", "d"])
        redis.zrem.assert_called()
