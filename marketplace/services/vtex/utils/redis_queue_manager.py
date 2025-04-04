import json

from typing import Any, List, Optional
from django_redis import get_redis_connection

from marketplace.interfaces.redis.interfaces import AbstractQueue


class BaseRedisQueue(AbstractQueue[Any]):
    """
    Base class for Redis-based queues implementing common functionality.

    This class provides core operations for interacting with Redis lists
    as queues, including adding, retrieving, and managing queue items.
    """

    def __init__(self, redis_key: str, redis_client=None, timeout: int = 86400):
        """
        Initialize the base Redis queue.

        Args:
            redis_key: Unique identifier for the queue in Redis.
            redis_client: Redis client instance (if None, default connection is used).
            timeout: Expiration time for the key in seconds.
        """
        self.key: str = redis_key
        self.client = redis_client or get_redis_connection()
        self.timeout: int = timeout
        # Set expiration if the key does not exist yet.
        if not self.client.exists(self.key):
            self.client.expire(self.key, timeout)

    def put(self, item: Any) -> None:
        """
        Add an item to the end of the queue.

        Args:
            item: The item to add to the queue. Can be any serializable object.
        """
        serialized = item if isinstance(item, str) else json.dumps(item)
        self.client.rpush(self.key, serialized)
        # Refresh expiration time.
        self.client.expire(self.key, self.timeout)

    def get(self) -> Optional[Any]:
        """
        Remove and return an item from the beginning of the queue.

        Returns:
            The first item in the queue, or None if the queue is empty.
            If the item was stored as JSON, it will be deserialized.
        """
        item = self.client.lpop(self.key)
        if item is None:
            return None
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        try:
            return json.loads(item)
        except (TypeError, json.JSONDecodeError):
            return item

    def empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        return self.client.llen(self.key) == 0

    def qsize(self) -> int:
        """
        Return the current size of the queue.

        Returns:
            The number of items in the queue.
        """
        return self.client.llen(self.key)

    def put_many(self, items: List[Any]) -> None:
        """
        Add multiple items to the queue at once.

        This method is more efficient than calling put() multiple times
        as it uses Redis pipelining to reduce network overhead.

        Args:
            items: List of items to add to the queue.
        """
        serialized_items = [
            item if isinstance(item, str) else json.dumps(item) for item in items
        ]
        batch_size = 100_000
        pipeline = self.client.pipeline()
        for i in range(0, len(serialized_items), batch_size):
            batch = serialized_items[i : i + batch_size]  # noqa: E203
            pipeline.rpush(self.key, *batch)
        pipeline.execute()
        self.client.expire(self.key, self.timeout)

    def clear(self) -> None:
        """
        Delete the queue key from Redis, effectively clearing the queue.
        """
        self.client.delete(self.key)


class RedisQueueManager(BaseRedisQueue):
    """
    Main Redis queue used for processing items.

    This class inherits all functionality from BaseRedisQueue and serves
    as the primary queue implementation for standard processing workflows.
    """

    pass


class TempRedisQueueManager(BaseRedisQueue):
    """
    Temporary Redis queue used to store items during processing.

    This queue is typically used as a staging area during batch operations
    or when items need to be temporarily stored before being processed or
    moved back to the main queue.

    The temporary queue key is prefixed with "temp_" to differentiate it
    from the main queue.
    """

    def __init__(self, redis_key: str, redis_client=None, timeout: int = 86400):
        """
        Initialize a temporary Redis queue.

        Args:
            redis_key: Base identifier for the queue (will be prefixed with 'temp_').
            redis_client: Redis client instance (if None, default connection is used).
            timeout: Expiration time for the key in seconds.
        """
        # Prepend 'temp_' to the key to differentiate from the main queue.
        super().__init__(
            redis_key=f"temp_{redis_key}", redis_client=redis_client, timeout=timeout
        )

    def get_all(self) -> List[Any]:
        """
        Retrieve all items currently stored in the temporary queue.

        This method does not remove items from the queue, it only reads them.

        Returns:
            A list of all items in the queue, deserialized if they were stored as JSON.
        """
        items = self.client.lrange(self.key, 0, -1)
        results = []
        for item in items:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            try:
                results.append(json.loads(item))
            except (TypeError, json.JSONDecodeError):
                results.append(item)
        return results
