import time
import functools
import requests


def retry_on_exception(max_attempts=8, start_sleep_time=1, factor=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts, sleep_time = 0, start_sleep_time
            last_exception = ""
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    if attempts >= 5:
                        print(f"Timeout error: {str(e)}. Retrying...")
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    if attempts >= 5:
                        if e.response.status_code == 429:
                            print(f"Too many requests: {str(e)}. Retrying...")
                        elif e.response.status_code == 500:
                            print(f"A 500 error occurred: {str(e)}. Retrying...")
                        else:
                            raise
                except Exception as e:
                    last_exception = e
                    if hasattr(e, "status_code") and e.status_code == 404:
                        print(f"Not Found: {str(e)}. Not retrying this.")
                        raise

                    if attempts >= 5:
                        print(f"An unexpected error has occurred: {e}")

                if attempts >= 5:
                    print(
                        f"Retrying... Attempt {attempts + 1} after {sleep_time} seconds"
                    )

                time.sleep(sleep_time)
                attempts += 1
                sleep_time *= factor

            message = (
                f"Rate limit exceeded, max retry attempts reached. Last error in {func.__name__}:"
                f"Last error:{last_exception}, after {attempts} attempts."
            )

            print(message)
            raise Exception(message)

        return wrapper

    return decorator_retry
