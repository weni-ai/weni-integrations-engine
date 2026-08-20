from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketplace.core.pacing.queue import RedisQueue, enqueue_item


class RedisQueueTestCase(SimpleTestCase):
    @patch("marketplace.core.pacing.queue.get_redis_connection")
    def test_insert_skips_existing_and_adds_new(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        queue = RedisQueue("q")

        redis.zscore.return_value = 1.0
        self.assertFalse(queue.insert("v1"))

        redis.zscore.return_value = None
        self.assertTrue(queue.insert("v2"))
        redis.zadd.assert_called()
        redis.expire.assert_called()

    @patch("marketplace.core.pacing.queue.get_redis_connection")
    def test_remove_order_length_and_get_batch(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        queue = RedisQueue("q")

        redis.zrange.return_value = []
        self.assertIsNone(queue.remove())

        redis.zrange.return_value = [b"v2"]
        self.assertEqual(queue.remove(), "v2")
        redis.zrem.assert_called()

        redis.zrange.return_value = [b"a", b"b"]
        self.assertEqual(queue.order(), ["a", "b"])

        redis.zcard.return_value = 5
        self.assertEqual(queue.length(), 5)

        redis.zrange.return_value = [b"c", b"d"]
        self.assertEqual(queue.get_batch(2), ["c", "d"])
        redis.zrem.assert_called()

    @patch("marketplace.core.pacing.queue.get_redis_connection")
    def test_decode_accepts_str_items(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        queue = RedisQueue("q")
        redis.zrange.return_value = ["already-str"]
        self.assertEqual(queue.get_batch(1), ["already-str"])

    @patch("marketplace.core.pacing.queue.get_redis_connection")
    def test_enqueue_item_stringifies_id(self, mock_conn):
        redis = MagicMock()
        redis.zscore.return_value = None
        mock_conn.return_value = redis
        self.assertTrue(enqueue_item("q", 123))
        redis.zadd.assert_called()
