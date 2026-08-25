from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketplace.core.pacing.ttl import is_recently_synced, mark_synced


class SyncTtlTestCase(SimpleTestCase):
    @patch("marketplace.core.pacing.ttl.get_redis_connection")
    def test_is_recently_synced_false_when_key_missing(self, mock_conn):
        redis = MagicMock()
        redis.get.return_value = None
        mock_conn.return_value = redis
        self.assertFalse(is_recently_synced("lock-key"))

    @patch("marketplace.core.pacing.ttl.get_redis_connection")
    def test_is_recently_synced_true_when_key_present(self, mock_conn):
        redis = MagicMock()
        redis.get.return_value = b"synced"
        redis.ttl.return_value = 30
        mock_conn.return_value = redis
        self.assertTrue(is_recently_synced("lock-key"))

    @patch("marketplace.core.pacing.ttl.get_redis_connection")
    def test_mark_synced_sets_ttl(self, mock_conn):
        redis = MagicMock()
        mock_conn.return_value = redis
        mark_synced("lock-key", 3600)
        redis.set.assert_called_once_with("lock-key", "synced", ex=3600)
