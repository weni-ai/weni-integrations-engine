import subprocess
import requests
import xml.etree.ElementTree as ET


# Read the coverage report from the XML file
COVERAGE_REPORT = ET.parse("coverage.xml").getroot()

# Get the current coverage rate from the XML file
COVERAGE_CURRENT = float(COVERAGE_REPORT.attrib["line-rate"])
COVERAGE_CURRENT_ABSOLUTE = COVERAGE_CURRENT * 100

try:
    # Get the latest commit ID from the Git repository
    LAST_COMMIT = (
        subprocess.check_output(["git", "rev-parse", "origin/main"]).decode().strip()
    )
except subprocess.CalledProcessError as e:
    print("Error:", e.output)
    exit(1)

# Get the coverage rate for the latest commit from the Codecov API
URL_V2 = (
    "https://api.codecov.io/api/v2/gh/weni-ai/repos/weni-integrations-engine/commits/"
)
COVERAGE_LAST_COMMIT_API = f"{URL_V2}{LAST_COMMIT}"
response = requests.get(COVERAGE_LAST_COMMIT_API).json()
COVERAGE_LAST_COMMIT = response["totals"]["coverage"]

# Compare the current coverage rate to the coverage rate for the latest commit
current_commit_cov = round(float(COVERAGE_CURRENT_ABSOLUTE), 2)
last_commit_cov = round(float(COVERAGE_LAST_COMMIT), 2)

print('absolute', current_commit_cov)
print('last', last_commit_cov)

if current_commit_cov < last_commit_cov:
    print(
        f"Coverage decreased from {last_commit_cov} to {current_commit_cov}"
    )
    exit(1)
else:
    print(
        f"Coverage increased from {last_commit_cov} to {current_commit_cov}"
    )
    exit(0)
