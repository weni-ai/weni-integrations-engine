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
if COVERAGE_CURRENT_ABSOLUTE < float(COVERAGE_LAST_COMMIT):
    print(
        f"Coverage decreased from {COVERAGE_LAST_COMMIT} to {COVERAGE_CURRENT_ABSOLUTE:.2f}"
    )
    exit(1)
else:
    print(
        f"Coverage increased from {COVERAGE_LAST_COMMIT} to {COVERAGE_CURRENT_ABSOLUTE:.2f}."
    )
    exit(0)
