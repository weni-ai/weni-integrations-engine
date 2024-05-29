import functools
import time

from django_redis import get_redis_connection


class RateLimiter:
    """
    A class for implementing rate limiting using Redis.

    This class limits the rate of operations performed by an identifier
    (e.g., a user or API key) within a specified period. It uses a Redis
    backend to track the count of operations and ensures the rate limit
    is not exceeded.

    Attributes:
        key_prefix (str): Prefix for Redis keys to avoid naming conflicts.
        calls (int): Maximum allowed operations within the period.
        period (int): Duration (in seconds) for the rate limit period.
        redis (Redis): Redis connection instance for rate data storage.
        current_count (dict): Tracks current count of operations for monitoring.
    """

    def __init__(self, key_prefix, calls, period, redis_connection):
        self.key_prefix = key_prefix
        self.calls = calls
        self.period = period
        self.redis = redis_connection
        self.current_count = {}

    def _get_key(self, identifier):
        return f"{self.key_prefix}:{identifier}"

    def check(self, identifier):
        """
        Check and enforce the rate limit for the given identifier.
        """
        key = self._get_key(identifier)
        current_count = self.redis.incr(key)

        if current_count == 1:
            # Set the TTL for the key if this is the first increment
            self.redis.expire(key, self.period)

        self.current_count[key] = current_count

        if current_count > self.calls:
            print(
                f"Rate limit [{current_count}/{self.calls}] was reached, in {self.period} seconds, "
                f"for key {key}. Waiting for 20 seconds."
            )
            time.sleep(20)
            # force reset the counter key after sleeping
            self.redis.delete(key)


def rate_limit_and_retry_on_exception(domain_key_func, calls_per_period, period):
    """
    Decorator to enforce rate limiting and retries.

    Applies rate limits and handles retries with exponential backoff
    for network or HTTP errors.

    Args:
        domain_key_func (callable): Function to extract domain identifier.
        calls_per_period (int): Max allowed function calls per period.
        period (int): Time period (in seconds) for rate limiting.

    Returns:
        callable: Decorated function with rate limiting and retries.
    """

    def decorator(func):
        redis_connection = get_redis_connection()
        rate_limiter = RateLimiter(
            "rate_limit", calls_per_period, period, redis_connection
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            domain = domain_key_func(*args, **kwargs)
            max_attempts = 8
            sleep_time = 1
            attempts = 0
            last_exception = ""

            while attempts < max_attempts:
                try:
                    rate_limiter.check(domain)
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    status_code = e.status_code if hasattr(e, "status_code") else None
                    if not status_code:
                        print(f"Unexpected error: {str(e)}")
                        raise

                    if status_code == 404:
                        print(f"Not Found: {str(e)}. Not retrying this.")
                        raise
                    elif status_code == 500:
                        print(f"A 500 error occurred: {str(e)}. Retrying...")
                        raise

                    if attempts >= 2:
                        if status_code == 429:
                            print(f"Too many requests: {str(e)}. Retrying...")
                        elif status_code == 408:
                            print(f"Timeout error: {str(e)}. Retrying...")
                        else:
                            print(f"Unexpected error: {str(e)}. status: {status_code}")
                            raise

                print(
                    f"Retrying... Attempt {attempts + 1} after {sleep_time} seconds, in {func.__name__}:"
                )
                time.sleep(sleep_time)
                attempts += 1
                sleep_time *= 2

            message = (
                f"Rate limit exceeded, max retry attempts reached. Last error in {func.__name__}:"
                f"Last error:{last_exception}, after {attempts} attempts."
            )

            print(message)
            raise Exception(message)

        return wrapper

    return decorator
