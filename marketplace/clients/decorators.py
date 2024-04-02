import time
import functools
import requests


def retry_on_exception(max_attempts=8, start_sleep_time=1, factor=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts, sleep_time = 0, start_sleep_time
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout as e:
                    if attempts >= 5:
                        print(f"Timeout error: {str(e)}. Retrying...")
                except requests.exceptions.HTTPError as e:
                    if attempts >= 5:
                        if e.response.status_code == 429:
                            print(f"Too many requests: {str(e)}. Retrying...")
                        elif e.response.status_code == 500:
                            print(f"A 500 error occurred: {str(e)}. Retrying...")
                        else:
                            raise
                except Exception as e:
                    if attempts >= 5:
                        print(f"An unexpected error has occurred: {e}")
                    raise

                if attempts >= 5:
                    print(
                        f"Retrying... Attempt {attempts + 1} after {sleep_time} seconds"
                    )

                time.sleep(sleep_time)
                attempts += 1
                sleep_time *= factor

            print("Max retry attempts reached. Raising exception.")
            raise Exception("Rate limit exceeded, max retry attempts reached.")

        return wrapper

    return decorator_retry
