from unittest.mock import MagicMock, patch
import json

from django.test import TestCase

from marketplace.services.vtex.utils.redis_queue_manager import (
    BaseRedisQueue,
    TempRedisQueueManager,
)


class TestBaseRedisQueue(TestCase):
    """Unit tests for BaseRedisQueue using dependency injection and mocks."""

    def setUp(self):
        """Prepare a mock Redis client for each test to avoid real Redis calls."""
        self.mock_client = MagicMock()
        # Default behaviors
        self.mock_client.exists.return_value = False
        self.mock_client.pipeline.return_value = MagicMock()

    def test_init_sets_expire_when_key_not_exists(self):
        """Ensure __init__ sets TTL when the key does not exist."""
        self.mock_client.exists.return_value = False

        queue = BaseRedisQueue(
            redis_key="test_queue", redis_client=self.mock_client, timeout=123
        )

        self.mock_client.exists.assert_called_once_with("test_queue")
        self.mock_client.expire.assert_called_with("test_queue", 123)
        self.assertEqual(queue.key, "test_queue")
        self.assertEqual(queue.timeout, 123)
        self.assertIs(queue.client, self.mock_client)

    def test_init_does_not_expire_when_key_exists(self):
        """Ensure __init__ does not set TTL when the key already exists."""
        self.mock_client.exists.return_value = True

        BaseRedisQueue(redis_key="q", redis_client=self.mock_client, timeout=999)

        self.mock_client.exists.assert_called_once_with("q")
        # No expire at init when key already exists
        self.mock_client.expire.assert_not_called()

    def test_init_uses_default_connection_when_client_none(self):
        """Ensure default Redis connection is fetched when client is not provided."""
        with patch(
            "marketplace.services.vtex.utils.redis_queue_manager.get_redis_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value = self.mock_client
            self.mock_client.exists.return_value = False

            queue = BaseRedisQueue(redis_key="default_q")

            mock_get_conn.assert_called_once_with()
            self.assertIs(queue.client, self.mock_client)
            self.mock_client.expire.assert_called_with("default_q", 86400)

    def test_put_serializes_non_str_and_refreshes_ttl(self):
        """Verify put() JSON-serializes non-string items and refreshes TTL."""
        self.mock_client.exists.return_value = True  # avoid expire at init
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client, timeout=77)

        item = {"a": 1}
        queue.put(item)

        # Should serialize dict to JSON
        serialized = json.dumps(item)
        self.mock_client.rpush.assert_called_once_with("q", serialized)
        # TTL refreshed on each put
        self.mock_client.expire.assert_called_once_with("q", 77)

    def test_put_keeps_string_unchanged(self):
        """Verify put() keeps strings unchanged."""
        self.mock_client.exists.return_value = True
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client, timeout=50)

        queue.put("hello")

        self.mock_client.rpush.assert_called_once_with("q", "hello")
        self.mock_client.expire.assert_called_once_with("q", 50)

    def test_get_returns_none_when_empty(self):
        """get() should return None when queue is empty."""
        self.mock_client.lpop.return_value = None
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        result = queue.get()
        self.assertIsNone(result)

    def test_get_decodes_bytes_and_parses_json(self):
        """get() should decode bytes and parse JSON payloads."""
        self.mock_client.lpop.return_value = b'{"x": 1}'
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        result = queue.get()
        self.assertEqual(result, {"x": 1})

    def test_get_decodes_bytes_non_json(self):
        """get() should decode bytes and return raw string if not JSON."""
        self.mock_client.lpop.return_value = b"not-json"
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        result = queue.get()
        self.assertEqual(result, "not-json")

    def test_get_returns_raw_string(self):
        """get() should return raw string if already a string and not JSON."""
        self.mock_client.lpop.return_value = "already-string"
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        result = queue.get()
        self.assertEqual(result, "already-string")

    def test_empty_true_when_llen_zero(self):
        """empty() should be True when llen is zero."""
        self.mock_client.llen.return_value = 0
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        self.assertTrue(queue.empty())
        self.mock_client.llen.assert_called_once_with("q")

    def test_empty_false_when_llen_positive(self):
        """empty() should be False when llen > 0."""
        self.mock_client.llen.return_value = 3
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        self.assertFalse(queue.empty())
        self.mock_client.llen.assert_called_once_with("q")

    def test_qsize_returns_llen(self):
        """qsize() should return llen value."""
        self.mock_client.llen.return_value = 42
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        self.assertEqual(queue.qsize(), 42)
        self.mock_client.llen.assert_called_once_with("q")

    def test_put_many_uses_pipeline_and_serializes(self):
        """put_many() should pipeline rpush calls and refresh TTL."""
        self.mock_client.exists.return_value = True
        pipeline = MagicMock()
        self.mock_client.pipeline.return_value = pipeline

        queue = BaseRedisQueue(
            redis_key="q", redis_client=self.mock_client, timeout=3600
        )

        items = ["a", {"k": 1}, 2]
        queue.put_many(items)

        # One batch (batch_size is large enough)
        self.mock_client.pipeline.assert_called_once_with()
        # Validate arguments passed to rpush (key, *serialized_items)
        expected_serialized = ["a", json.dumps({"k": 1}), json.dumps(2)]
        pipeline.rpush.assert_called_once()
        args, _ = pipeline.rpush.call_args
        # First arg is key, the rest are items
        self.assertEqual(args[0], "q")
        self.assertEqual(list(args[1:]), expected_serialized)

        pipeline.execute.assert_called_once_with()
        self.mock_client.expire.assert_called_once_with("q", 3600)

    def test_clear_deletes_key(self):
        """clear() should delete the queue key."""
        queue = BaseRedisQueue(redis_key="q", redis_client=self.mock_client)

        queue.clear()

        self.mock_client.delete.assert_called_once_with("q")


class TestTempRedisQueueManager(TestCase):
    """Unit tests for TempRedisQueueManager using mocks."""

    def setUp(self):
        """Prepare a mock Redis client."""
        self.mock_client = MagicMock()
        self.mock_client.exists.return_value = False

    def test_init_prefixes_key_with_temp(self):
        """Ensure the key is properly prefixed with 'temp_'."""
        queue = TempRedisQueueManager(
            redis_key="base", redis_client=self.mock_client, timeout=10
        )

        self.assertEqual(queue.key, "temp_base")
        self.mock_client.expire.assert_called_with("temp_base", 10)

    def test_get_all_decodes_and_deserializes_items(self):
        """get_all() should read, decode and JSON-deserialize items from the list."""
        # Mix of bytes and str, JSON and non-JSON
        items_in_redis = [
            b'{"a": 1}',
            "plain-text",
            b"3",
            '["x", "y"]',
        ]
        self.mock_client.lrange.return_value = items_in_redis

        queue = TempRedisQueueManager(redis_key="k", redis_client=self.mock_client)
        results = queue.get_all()

        # Expected: dict, same string, int, list
        self.assertEqual(results[0], {"a": 1})
        self.assertEqual(results[1], "plain-text")
        self.assertEqual(results[2], 3)
        self.assertEqual(results[3], ["x", "y"])
