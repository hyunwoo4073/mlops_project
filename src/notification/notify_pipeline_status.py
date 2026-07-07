from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _format_float(value: Any) -> str:
    if value is None:
        return "N/A"

    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def fetch_latest_model(conn) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT
                id,
                model_name,
                run_id,
                accuracy,
                f1_weighted,
                status,
                promoted_model_path,
                created_at
            FROM model_registry
            WHERE status = 'PROMOTED'
            ORDER BY id DESC
            LIMIT 1
            """
        )
    ).mappings().first()

    return dict(row) if row else None


def fetch_recent_check_summary(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            WITH recent_checks AS (
                SELECT *
                FROM pipeline_check_results
                ORDER BY id DESC
                LIMIT 50
            )
            SELECT
                check_type,
                status,
                COUNT(*) AS count
            FROM recent_checks
            GROUP BY check_type, status
            ORDER BY check_type, status
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


def fetch_recent_failed_checks(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                check_type,
                check_name,
                status,
                metric_value,
                threshold_value,
                message,
                checked_at
            FROM pipeline_check_results
            WHERE UPPER(status) NOT IN ('PASS', 'SUCCESS')
              AND checked_at >= NOW() - INTERVAL '24 hours'
            ORDER BY id DESC
            LIMIT 10
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


def fetch_prediction_summary(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                COALESCE(prediction_source, 'BATCH') AS prediction_source,
                COUNT(*) AS prediction_count,
                AVG(confidence) AS avg_confidence,
                COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count
            FROM model_predictions
            GROUP BY COALESCE(prediction_source, 'BATCH')
            ORDER BY prediction_source
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


def fetch_api_summary(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                status,
                COUNT(*) AS request_count,
                AVG(latency_ms) AS avg_latency_ms
            FROM api_prediction_logs
            GROUP BY status
            ORDER BY status
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


def build_message(
    latest_model: dict[str, Any] | None,
    check_summary: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
    prediction_summary: list[dict[str, Any]],
    api_summary: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    has_failed_checks = len(failed_checks) > 0
    title_icon = ":rotating_light:" if has_failed_checks else ":white_check_mark:"

    lines.append(f"{title_icon} JobSkill MLOps Pipeline Status")
    lines.append("")

    if latest_model:
        lines.append("*Latest Promoted Model*")
        lines.append(
            "- "
            f"id={latest_model.get('id')}, "
            f"status={latest_model.get('status')}, "
            f"accuracy={_format_float(latest_model.get('accuracy'))}, "
            f"f1_weighted={_format_float(latest_model.get('f1_weighted'))}"
        )
        lines.append(f"- path={latest_model.get('promoted_model_path')}")
    else:
        lines.append("*Latest Promoted Model*")
        lines.append("- No model_registry record found.")

    lines.append("")
    lines.append("*Recent Check Summary*")

    if check_summary:
        for row in check_summary:
            lines.append(
                "- "
                f"{row.get('check_type')} / {row.get('status')}: "
                f"{row.get('count')}"
            )
    else:
        lines.append("- No pipeline_check_results records found.")

    lines.append("")
    lines.append("*Prediction Summary*")

    if prediction_summary:
        for row in prediction_summary:
            prediction_count = int(row.get("prediction_count") or 0)
            low_confidence_count = int(row.get("low_confidence_count") or 0)
            low_ratio = (
                low_confidence_count / prediction_count
                if prediction_count > 0
                else 0.0
            )

            lines.append(
                "- "
                f"{row.get('prediction_source')}: "
                f"count={prediction_count}, "
                f"avg_confidence={_format_float(row.get('avg_confidence'))}, "
                f"low_confidence_ratio={low_ratio:.4f}"
            )
    else:
        lines.append("- No model_predictions records found.")

    lines.append("")
    lines.append("*API Summary*")

    if api_summary:
        for row in api_summary:
            lines.append(
                "- "
                f"{row.get('status')}: "
                f"count={row.get('request_count')}, "
                f"avg_latency_ms={_format_float(row.get('avg_latency_ms'))}"
            )
    else:
        lines.append("- No api_prediction_logs records found.")

    if failed_checks:
        lines.append("")
        lines.append("*Recent Failed Checks*")

        for row in failed_checks:
            lines.append(
                "- "
                f"{row.get('check_type')} / {row.get('check_name')} / "
                f"{row.get('status')} "
                f"(metric={_format_float(row.get('metric_value'))}, "
                f"threshold={_format_float(row.get('threshold_value'))})"
            )
            if row.get("message"):
                lines.append(f"  - {row.get('message')}")

    return "\n".join(lines)


def send_slack_message(message: str) -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()

    if not webhook_url:
        print("[Notification skipped] SLACK_WEBHOOK_URL is not set.")
        return

    response = requests.post(
        webhook_url,
        json={"text": message},
        timeout=10,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Failed to send Slack notification. "
            f"status_code={response.status_code}, body={response.text}"
        )

    print("Slack notification sent successfully.")


def main() -> None:
    alert_enabled = _env_bool("ALERT_ENABLED", default=False)
    alert_only_on_failure = _env_bool("ALERT_ONLY_ON_FAILURE", default=False)

    engine = get_engine()

    with engine.begin() as conn:
        latest_model = fetch_latest_model(conn)
        check_summary = fetch_recent_check_summary(conn)
        failed_checks = fetch_recent_failed_checks(conn)
        prediction_summary = fetch_prediction_summary(conn)
        api_summary = fetch_api_summary(conn)

    message = build_message(
        latest_model=latest_model,
        check_summary=check_summary,
        failed_checks=failed_checks,
        prediction_summary=prediction_summary,
        api_summary=api_summary,
    )

    has_failed_checks = len(failed_checks) > 0

    print()
    print("[Pipeline Notification Message]")
    print(message)
    print()

    if not alert_enabled:
        print("[Notification skipped] ALERT_ENABLED is false.")
        return

    if alert_only_on_failure and not has_failed_checks:
        print("[Notification skipped] ALERT_ONLY_ON_FAILURE is true and no failed checks were found.")
        return

    send_slack_message(message)


if __name__ == "__main__":
    main()
