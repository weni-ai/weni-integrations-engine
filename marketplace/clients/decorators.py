import time
import functools


def retry_on_exception(max_attempts=11, start_sleep_time=1, factor=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts, sleep_time = 0, start_sleep_time
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (
                    Exception
                ) as e:  # TODO: Map only timeout errors or errors from many requests
                    if attempts > 5:
                        print(
                            f"Retrying... Attempt {attempts + 1} after {sleep_time} seconds, {str(e)}"
                        )
                    time.sleep(sleep_time)
                    attempts += 1
                    sleep_time *= factor

            print("Max retry attempts reached. Raising exception.")
            raise Exception("Rate limit exceeded, max retry attempts reached.")

        return wrapper

    return decorator_retry
