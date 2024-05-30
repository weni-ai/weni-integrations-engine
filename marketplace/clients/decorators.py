import time
import functools
import logging


logger = logging.getLogger(__name__)


def retry_on_exception(max_attempts=8, start_sleep_time=1, factor=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts, sleep_time = 0, start_sleep_time
            last_exception = ""
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    status_code = e.status_code if hasattr(e, "status_code") else None
                    if not status_code:
                        print(f"Unexpected error: [{str(e)}]")
                        logger.error(e)

                    if status_code == 404:
                        print(f"Not Found: {str(e)}. Not retrying this.")
                        raise
                    elif status_code == 500:
                        print(f"A 500 error occurred: {str(e)}. Retrying...")
                        raise

                    if attempts >= 5:
                        if status_code == 429:
                            print(f"Too many requests: {str(e)}. Retrying...")
                        elif status_code == 408:
                            print(f"Timeout error: {str(e)}. Retrying...")
                        else:
                            print(
                                f"Unexpected error: [{str(e)}]. status: {status_code}"
                            )
                            logger.error(e)

                if attempts >= 5:
                    print(
                        f"Retrying... Attempt {attempts + 1} after {sleep_time} seconds, in {func.__name__}:"
                    )

                time.sleep(sleep_time)
                attempts += 1
                sleep_time *= factor

            message = (
                f"Rate limit exceeded, max retry attempts reached. Last error in {func.__name__}:"
                f"Last error:{last_exception}, after {attempts} attempts."
            )

            print(message)
            logger.error(message)

        return wrapper

    return decorator_retry
