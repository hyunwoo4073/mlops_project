from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ALERT_RULES_PATH = PROJECT_ROOT / "monitoring/prometheus/rules/jobskill_alert_rules.yml"
RUNBOOK_DIR = PROJECT_ROOT / "docs/runbooks"

RUNBOOK_CHECK_API = os.getenv("RUNBOOK_CHECK_API", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


ALERT_PATTERN = re.compile(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$")
RUNBOOK_URL_PATTERN = re.compile(r"^\s*runbook_url:\s*[\"']?([^\"'\s]+)[\"']?\s*$")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def parse_alert_runbook_urls() -> dict[str, str | None]:
    if not ALERT_RULES_PATH.exists():
        fail(f"Alert rules file not found: {ALERT_RULES_PATH}")

    alert_runbooks: dict[str, str | None] = {}
    current_alert: str | None = None

    for line in ALERT_RULES_PATH.read_text(encoding="utf-8").splitlines():
        alert_match = ALERT_PATTERN.match(line)

        if alert_match:
            current_alert = alert_match.group(1)
            alert_runbooks[current_alert] = None
            continue

        runbook_match = RUNBOOK_URL_PATTERN.match(line)

        if runbook_match and current_alert:
            alert_runbooks[current_alert] = runbook_match.group(1)

    if not alert_runbooks:
        fail(f"No alert rules found in {ALERT_RULES_PATH}")

    return alert_runbooks


def validate_runbook_url(alert_name: str, runbook_url: str | None) -> str:
    if not runbook_url:
        fail(f"{alert_name}: runbook_url annotation is missing")

    parsed = urlparse(runbook_url)

    if not parsed.path.startswith("/runbooks/"):
        fail(
            f"{alert_name}: runbook_url must point to /runbooks/*.md "
            f"but got {runbook_url}"
        )

    filename = Path(parsed.path).name

    if not filename.endswith(".md"):
        fail(f"{alert_name}: runbook_url must end with .md but got {runbook_url}")

    runbook_path = RUNBOOK_DIR / filename

    if not runbook_path.exists():
        fail(f"{alert_name}: runbook file not found: {runbook_path}")

    return filename


def check_runbook_api(alert_name: str, filename: str) -> None:
    url = f"{API_URL}/runbooks/{filename}"

    try:
        with urlopen(url, timeout=10) as response:
            status_code = response.status
            body = response.read(200).decode("utf-8", errors="ignore")
    except HTTPError as exc:
        fail(f"{alert_name}: runbook API returned HTTP {exc.code}: {url}")
    except URLError as exc:
        fail(f"{alert_name}: runbook API request failed: {url} ({exc})")

    if status_code != 200:
        fail(f"{alert_name}: runbook API returned HTTP {status_code}: {url}")

    if not body.strip():
        fail(f"{alert_name}: runbook API returned empty body: {url}")


def main() -> None:
    print("")
    print("JobSkill Runbook Coverage Check")
    print(f"Alert rules: {ALERT_RULES_PATH}")
    print(f"Runbook dir : {RUNBOOK_DIR}")
    print(f"API check   : {RUNBOOK_CHECK_API}")
    print(f"API URL     : {API_URL}")

    alert_runbooks = parse_alert_runbook_urls()

    checked_count = 0

    for alert_name, runbook_url in alert_runbooks.items():
        filename = validate_runbook_url(alert_name, runbook_url)

        if RUNBOOK_CHECK_API:
            check_runbook_api(alert_name, filename)

        print(f"[OK] {alert_name} -> {filename}")
        checked_count += 1

    print("")
    pass_check(f"Runbook coverage check completed: {checked_count} alerts")


if __name__ == "__main__":
    main()
