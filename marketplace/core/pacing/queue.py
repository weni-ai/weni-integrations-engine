import logging
import time

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


class RedisQueue:
    def __init__(self, queue_key):
        self.queue_key = queue_key
        self.redis = get_redis_connection()

    def insert(self, value):
        """Add an item to the ZSET queue with a timestamp score."""
        if self.redis.zscore(self.queue_key, value) is not None:
            logger.debug(f"{value} already exists in {self.queue_key}")
            return False

        score = time.time()
        self.redis.zadd(self.queue_key, {value: score})
        self.redis.expire(self.queue_key, 3600 * 24)
        return True

    def remove(self):
        """Remove and return the first item from the queue (FIFO)."""
        items = self.redis.zrange(self.queue_key, 0, 0, withscores=False)
        if not items:
            return None
        self.redis.zrem(self.queue_key, items[0])
        return self._decode(items[0])

    def order(self):
        """List all items in the queue in order."""
        items = self.redis.zrange(self.queue_key, 0, -1, withscores=False)
        return [self._decode(item) for item in items]

    def length(self):
        """Returns the total number of items in the queue."""
        return self.redis.zcard(self.queue_key)

    def get_batch(self, batch_size):
        items = self.redis.zrange(self.queue_key, 0, batch_size - 1, withscores=False)
        if items:
            self.redis.zrem(self.queue_key, *items)
        return [self._decode(item) for item in items]

    @staticmethod
    def _decode(item):
        if isinstance(item, bytes):
            return item.decode("utf-8")
        return item


def enqueue_item(queue_key: str, item_id: str) -> bool:
    return RedisQueue(queue_key).insert(str(item_id))
