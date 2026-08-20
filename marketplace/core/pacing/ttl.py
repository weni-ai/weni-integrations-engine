import logging

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


def is_recently_synced(key: str, redis=None) -> bool:
    redis = redis or get_redis_connection()
    if redis.get(key) is None:
        return False
    ttl = redis.ttl(key)
    logger.debug(f"Skipping {key}, recently synced ({ttl} seconds left).")
    return True


def mark_synced(key: str, ttl_seconds: int, redis=None) -> None:
    redis = redis or get_redis_connection()
    redis.set(key, "synced", ex=ttl_seconds)
