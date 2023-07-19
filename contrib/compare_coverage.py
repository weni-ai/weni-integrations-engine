import subprocess
import requests

try:
    LAST_MAIN_COMMIT = (
        subprocess.check_output(["git", "rev-parse", "origin/main"]).decode().strip()
    )
    LAST_LOCAL_COMMIT = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    )
except subprocess.CalledProcessError as e:
    print("Error executing git command:", e)
    exit(1)

print("11111111111")

URL_V2 = (
    "https://api.codecov.io/api/v2/gh/weni-ai/repos/weni-integrations-engine/commits/"
)

response_main_commit = requests.get(f"{URL_V2}{LAST_MAIN_COMMIT}")
response_local_commit = requests.get(f"{URL_V2}{LAST_LOCAL_COMMIT}")
print("2222222222")
print(f"response_main_commit.status_code {response_main_commit.status_code}")
print(f"response_local_commit.status_code {response_local_commit.status_code}")
if response_main_commit.status_code != 200 or response_local_commit.status_code != 200:
    print("Error: Failed to fetch coverage data from Codecov API")
    exit(1)

try:
    response_main_commit = response_main_commit.json()
    response_local_commit = response_local_commit.json()
except ValueError as e:
    print("Error parsing JSON response from Codecov API:", e)
    exit(1)

if "totals" in response_local_commit and "totals" in response_main_commit:
    local_misses = response_local_commit["totals"].get("misses")
    main_misses = response_main_commit["totals"].get("misses")
else:
    print("Error: Invalid JSON response from Codecov API")
    exit(1)

if local_misses is not None and main_misses is not None:
    if local_misses > main_misses:
        print(f"Number of test lines decreased by {local_misses - main_misses}")
        exit(1)
    else:
        print(f"Number of test lines increased by {main_misses - local_misses}")
        exit(0)
else:
    print("Error: Missing 'misses' value in JSON response from Codecov API")
    exit(1)
