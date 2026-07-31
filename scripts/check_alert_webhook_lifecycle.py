from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DEFAULT_WEBHOOK_URL = os.getenv(
    "ALERT_WEBHOOK_URL",
    "http://api:8000/alertmanager/webhook",
)
DEFAULT_ALERT_NAME = "SmokeLifecycleAlert"
DEFAULT_SERVICE = "smoke-test"
DEFAULT_SEVERITY = "info"


class CheckFailed(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_database_url() -> str:
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_engine() -> Engine:
    return create_engine(
        build_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
    )


def post_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw_response": raw}
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise CheckFailed(f"Webhook returned HTTP {exc.code}: {response_body}") from exc
    except URLError as exc:
        raise CheckFailed(f"Webhook request failed: {exc}") from exc


def build_alertmanager_payload(
    *,
    receiver: str,
    status: str,
    alert_name: str,
    service: str,
    severity: str,
    fingerprint: str,
    starts_at: str,
    ends_at: str,
) -> dict[str, Any]:
    return {
        "receiver": receiver,
        "status": status,
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": alert_name,
                    "severity": severity,
                    "service": service,
                },
                "annotations": {
                    "summary": "Smoke lifecycle alert",
                    "description": "Synthetic alert used to validate firing and resolved webhook lifecycle.",
                },
                "startsAt": starts_at,
                "endsAt": ends_at,
                "generatorURL": "http://localhost:9090/graph",
                "fingerprint": fingerprint,
            }
        ],
    }


def fetch_current_state(engine: Engine, fingerprint: str) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            fingerprint,
            status,
            alert_name,
            service,
            severity,
            starts_at,
            ends_at,
            last_received_at,
            updated_at
        FROM alert_current_states
        WHERE fingerprint = :fingerprint
        ORDER BY updated_at DESC
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        row = conn.execute(query, {"fingerprint": fingerprint}).mappings().first()
        return dict(row) if row else None


def fetch_event_count(engine: Engine, fingerprint: str) -> int:
    query = text(
        """
        SELECT COUNT(*)
        FROM alert_events
        WHERE fingerprint = :fingerprint
        """
    )
    with engine.begin() as conn:
        return int(conn.execute(query, {"fingerprint": fingerprint}).scalar() or 0)


def wait_for_status(
    *,
    engine: Engine,
    fingerprint: str,
    expected_status: str,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_state: dict[str, Any] | None = None

    while time.monotonic() <= deadline:
        state = fetch_current_state(engine, fingerprint)
        if state is not None:
            last_state = state
            if state.get("status") == expected_status:
                return state
        time.sleep(poll_interval_seconds)

    raise CheckFailed(
        "Current alert state did not reach "
        f"status={expected_status!r} within {timeout_seconds}s. "
        f"last_state={last_state}"
    )


def cleanup_synthetic_rows(engine: Engine, fingerprint: str) -> tuple[int, int]:
    with engine.begin() as conn:
        current_result = conn.execute(
            text("DELETE FROM alert_current_states WHERE fingerprint = :fingerprint"),
            {"fingerprint": fingerprint},
        )
        event_result = conn.execute(
            text("DELETE FROM alert_events WHERE fingerprint = :fingerprint"),
            {"fingerprint": fingerprint},
        )

    return int(current_result.rowcount or 0), int(event_result.rowcount or 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Alertmanager webhook firing/resolved lifecycle without leaving synthetic alert rows behind.",
    )
    parser.add_argument(
        "--webhook-url",
        default=DEFAULT_WEBHOOK_URL,
        help="FastAPI Alertmanager webhook URL. Default: %(default)s",
    )
    parser.add_argument(
        "--alert-name",
        default=DEFAULT_ALERT_NAME,
        help="Synthetic alert name. Default: %(default)s",
    )
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help="Synthetic alert service label. Default: %(default)s",
    )
    parser.add_argument(
        "--severity",
        default=DEFAULT_SEVERITY,
        help="Synthetic alert severity label. Default: %(default)s",
    )
    parser.add_argument(
        "--fingerprint",
        default=None,
        help="Synthetic alert fingerprint. Default: generated unique fingerprint.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=15,
        help="Webhook and DB polling timeout. Default: %(default)s",
    )
    parser.add_argument(
        "--keep-rows",
        action="store_true",
        help="Keep synthetic rows after validation. Default behavior deletes them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fingerprint = args.fingerprint or f"smoke-lifecycle-{int(time.time())}"
    starts_at = utc_now_iso()

    engine = get_engine()

    firing_payload = build_alertmanager_payload(
        receiver="smoke-test",
        status="firing",
        alert_name=args.alert_name,
        service=args.service,
        severity=args.severity,
        fingerprint=fingerprint,
        starts_at=starts_at,
        ends_at="0001-01-01T00:00:00Z",
    )

    print("Alert Webhook Lifecycle Check")
    print("=============================")
    print(f"webhook_url={args.webhook_url}")
    print(f"alert_name={args.alert_name}")
    print(f"service={args.service}")
    print(f"fingerprint={fingerprint}")

    print("\n[1/5] Send firing alert")
    post_json(args.webhook_url, firing_payload, args.timeout_seconds)

    print("[2/5] Verify firing current state")
    firing_state = wait_for_status(
        engine=engine,
        fingerprint=fingerprint,
        expected_status="firing",
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=0.5,
    )
    print(f"firing_state={firing_state}")

    print("[3/5] Send resolved alert")
    resolved_payload = build_alertmanager_payload(
        receiver="smoke-test",
        status="resolved",
        alert_name=args.alert_name,
        service=args.service,
        severity=args.severity,
        fingerprint=fingerprint,
        starts_at=starts_at,
        ends_at=utc_now_iso(),
    )
    post_json(args.webhook_url, resolved_payload, args.timeout_seconds)

    print("[4/5] Verify resolved current state")
    resolved_state = wait_for_status(
        engine=engine,
        fingerprint=fingerprint,
        expected_status="resolved",
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=0.5,
    )
    print(f"resolved_state={resolved_state}")

    event_count = fetch_event_count(engine, fingerprint)
    if event_count < 2:
        raise CheckFailed(
            f"Expected at least 2 alert_events rows for firing/resolved lifecycle, got {event_count}."
        )
    print(f"event_count={event_count}")

    print("[5/5] Cleanup synthetic lifecycle rows")
    if args.keep_rows:
        print("skip cleanup because --keep-rows was set")
    else:
        current_deleted, events_deleted = cleanup_synthetic_rows(engine, fingerprint)
        print(f"deleted_current_states={current_deleted}")
        print(f"deleted_alert_events={events_deleted}")

    print("\nPASS: Alert webhook lifecycle check completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailed as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

