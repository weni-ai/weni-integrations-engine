import functools
import time

from django_redis import get_redis_connection


class RateLimiter:
    """
    A class for implementing rate limiting using Redis.

    This class provides a mechanism to limit the rate of operations
    performed by an identifier (e.g., a user or API key)
    within a specified period. It uses a Redis backend to track
    the count of operations performed and ensures that the
    operation does not exceed the defined thresholds.

    Attributes:
        key_prefix (str): A prefix for Redis keys to avoid naming conflicts.
        calls (int): Maximum number of allowed operations within the defined period.
        period (int): The duration (in seconds) for which the rate limit applies.
        redis (Redis): An instance of a Redis connection to be used
        for storing and managing rate data.
        current_count (dict): A dictionary to store the current
        count of operations for monitoring and debugging.
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
        key = self._get_key(identifier)
        current_time = int(time.time())
        pipeline = self.redis.pipeline()
        pipeline.zremrangebyscore(key, 0, current_time - self.period)
        pipeline.zcard(key)
        pipeline.zadd(key, {current_time: current_time})
        pipeline.expire(key, self.period)
        _, current_count, _, _ = pipeline.execute()

        self.current_count = {key: current_count}
        if current_count > self.calls:
            sleep_duration = self._calculate_sleep_time(
                current_count, self.calls, self.period
            )
            print(
                f"Rate limit [{current_count}/{self.calls}] exceeded for key {key}. "
                f"Sleeping for {sleep_duration} seconds."
            )
            time.sleep(sleep_duration)

    def _calculate_sleep_time(self, current_count, calls, period):
        if current_count > calls:
            if period == 1:
                return 2
            elif period == 60:
                return 20
        return 0


def rate_limit_and_retry_on_exception(
    calls_per_second, calls_per_minute, domain_key_func
):
    """
    Decorates a function to enforce rate limiting and retries.

    Applies rate limits per second and per minute based on the provided limits. Handles retries
    with exponential backoff for network or HTTP errors.

    Parameters:
        calls_per_second (int): Maximum allowed function calls per second.
        calls_per_minute (int): Maximum allowed function calls per minute.
        domain_key_func (callable): Function to extract a domain identifier for rate limiting.

    Returns:
        Decorated function with applied rate limiting and error handling for retries.
    """

    def decorator(func):
        redis_connection = get_redis_connection()
        seconds_limiter = RateLimiter("per_sec", calls_per_second, 1, redis_connection)
        minute_limiter = RateLimiter("per_min", calls_per_minute, 60, redis_connection)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            domain = domain_key_func(*args, **kwargs)
            max_attempts = 8
            sleep_time = 1
            attempts = 0
            last_exception = ""

            while attempts < max_attempts:
                try:
                    seconds_limiter.check(domain)
                    minute_limiter.check(domain)
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    status_code = e.status_code if hasattr(e, "status_code") else None
                    if not status_code:
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
