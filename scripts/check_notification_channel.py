from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ALERTMANAGER_URL = os.getenv(
    "NOTIFICATION_ALERTMANAGER_URL",
    "http://localhost:9093",
).rstrip("/")

SLACK_WEBHOOK_FILE = Path(
    os.getenv(
        "SLACK_WEBHOOK_FILE",
        str(PROJECT_ROOT / ".secrets" / "slack_webhook_url"),
    )
)

SEND_TEST_ALERT = os.getenv("SEND_TEST_ALERT", "false").lower() == "true"
RESOLVE_TEST_ALERT = os.getenv("RESOLVE_TEST_ALERT", "false").lower() == "true"

TEST_ALERT_NAME = os.getenv(
    "TEST_ALERT_NAME",
    "JobSkillNotificationChannelHealthCheck",
)


def http_request(
    method: str,
    url: str,
    payload: object | None = None,
    timeout: int = 10,
) -> tuple[int, str]:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, body

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body

    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to connect to {url}: {exc}") from exc


def check_slack_webhook_file() -> None:
    if not SLACK_WEBHOOK_FILE.exists():
        raise RuntimeError(f"Slack webhook secret file not found: {SLACK_WEBHOOK_FILE}")

    content = SLACK_WEBHOOK_FILE.read_text(encoding="utf-8").strip()

    if not content:
        raise RuntimeError(f"Slack webhook secret file is empty: {SLACK_WEBHOOK_FILE}")

    if not content.startswith("https://hooks.slack.com/services/"):
        raise RuntimeError(
            "Slack webhook URL format looks invalid. "
            "Expected it to start with https://hooks.slack.com/services/"
        )

    print(f"[PASS] Slack webhook secret file exists: {SLACK_WEBHOOK_FILE}")
    print("[PASS] Slack webhook URL format looks valid")


def check_alertmanager_status() -> None:
    status_code, body = http_request(
        method="GET",
        url=f"{ALERTMANAGER_URL}/api/v2/status",
    )

    if status_code != 200:
        raise RuntimeError(
            f"Alertmanager status check failed. status={status_code}, body={body}"
        )

    print(f"[PASS] Alertmanager status endpoint is reachable: {ALERTMANAGER_URL}")


def send_test_alert() -> None:
    now = datetime.now(UTC).replace(microsecond=0)

    if RESOLVE_TEST_ALERT:
        starts_at = now - timedelta(minutes=5)
        ends_at = now
        summary = "JobSkill notification channel health check resolved"
        description = "This test alert was resolved by notification channel health check."
    else:
        starts_at = now
        ends_at = None
        summary = "JobSkill notification channel health check"
        description = "This is a manual notification channel health check alert."

    alert = {
        "labels": {
            "alertname": TEST_ALERT_NAME,
            "severity": "info",
            "service": "jobskill-mlops",
            "source": "notification-channel-check",
        },
        "annotations": {
            "summary": summary,
            "description": description,
        },
        "startsAt": starts_at.isoformat().replace("+00:00", "Z"),
    }

    if ends_at is not None:
        alert["endsAt"] = ends_at.isoformat().replace("+00:00", "Z")

    status_code, body = http_request(
        method="POST",
        url=f"{ALERTMANAGER_URL}/api/v2/alerts",
        payload=[alert],
    )

    if status_code not in {200, 202}:
        raise RuntimeError(
            f"Failed to send test alert. status={status_code}, body={body}"
        )

    if RESOLVE_TEST_ALERT:
        print(f"[PASS] Resolved test alert sent to Alertmanager: {TEST_ALERT_NAME}")
    else:
        print(f"[PASS] Test alert sent to Alertmanager: {TEST_ALERT_NAME}")


def verify_test_alert_exists() -> None:
    status_code, body = http_request(
        method="GET",
        url=f"{ALERTMANAGER_URL}/api/v2/alerts",
    )

    if status_code != 200:
        raise RuntimeError(
            f"Failed to read Alertmanager alerts. status={status_code}, body={body}"
        )

    alerts = json.loads(body)

    matched_alerts = [
        alert
        for alert in alerts
        if alert.get("labels", {}).get("alertname") == TEST_ALERT_NAME
    ]

    if not matched_alerts:
        raise RuntimeError(
            f"Test alert was sent but not found in Alertmanager: {TEST_ALERT_NAME}"
        )

    print(f"[PASS] Test alert is visible in Alertmanager: {TEST_ALERT_NAME}")


def main() -> None:
    print("")
    print("JobSkill Notification Channel Health Check")
    print("==========================================")
    print(f"alertmanager_url : {ALERTMANAGER_URL}")
    print(f"webhook_file     : {SLACK_WEBHOOK_FILE}")
    print(f"send_test_alert  : {SEND_TEST_ALERT}")
    print(f"resolve_alert    : {RESOLVE_TEST_ALERT}")
    print("")

    check_slack_webhook_file()
    check_alertmanager_status()

    if SEND_TEST_ALERT:
        send_test_alert()

        if not RESOLVE_TEST_ALERT:
            verify_test_alert_exists()
    else:
        print("[SKIP] Test alert sending is disabled.")
        print("       Run with SEND_TEST_ALERT=true to send a real Slack notification.")

    print("")
    print("[PASS] Notification channel health check completed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
