from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


REPORT_PATH = Path("reports/latest_incident_response_report.md")


def table_exists(table_name: str) -> bool:
    engine = get_engine()

    with engine.begin() as conn:
        return bool(
            conn.execute(
                text("SELECT to_regclass(:table_name) IS NOT NULL"),
                {"table_name": f"public.{table_name}"},
            ).scalar()
        )


def read_sql(query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    engine = get_engine()

    with engine.begin() as conn:
        return pd.read_sql(text(query), conn, params=params)


def read_sql_if_table_exists(
    table_name: str,
    query: str,
    params: dict[str, Any] | None = None,
) -> pd.DataFrame:
    if not table_exists(table_name):
        return pd.DataFrame()

    return read_sql(query, params=params)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data found._"

    return df.to_markdown(index=False)


def fetch_current_firing_alerts() -> pd.DataFrame:
    return read_sql_if_table_exists(
        "alert_current_states",
        """
        SELECT
            status,
            alert_name,
            severity,
            service,
            instance,
            summary,
            starts_at,
            updated_at
        FROM alert_current_states
        WHERE status = 'firing'
        ORDER BY updated_at DESC
        """,
    )


def fetch_current_alert_summary() -> pd.DataFrame:
    return read_sql_if_table_exists(
        "alert_current_states",
        """
        SELECT
            status,
            COALESCE(severity, 'unknown') AS severity,
            COALESCE(service, 'unknown') AS service,
            COUNT(*) AS alert_count,
            MAX(updated_at) AS latest_updated_at
        FROM alert_current_states
        GROUP BY
            status,
            COALESCE(severity, 'unknown'),
            COALESCE(service, 'unknown')
        ORDER BY latest_updated_at DESC
        """,
    )


def fetch_recent_alert_events(limit: int = 30) -> pd.DataFrame:
    return read_sql_if_table_exists(
        "alert_events",
        """
        SELECT
            id,
            status,
            alert_name,
            severity,
            service,
            instance,
            summary,
            starts_at,
            ends_at,
            created_at
        FROM alert_events
        ORDER BY id DESC
        LIMIT :limit
        """,
        params={"limit": limit},
    )


def fetch_recent_acknowledgements(limit: int = 30) -> pd.DataFrame:
    return read_sql_if_table_exists(
        "alert_acknowledgements",
        """
        SELECT
            id,
            alert_name,
            severity,
            service,
            status,
            acknowledged_by,
            note,
            created_at
        FROM alert_acknowledgements
        ORDER BY id DESC
        LIMIT :limit
        """,
        params={"limit": limit},
    )


def fetch_recent_silence_actions(limit: int = 30) -> pd.DataFrame:
    return read_sql_if_table_exists(
        "alert_silence_actions",
        """
        SELECT
            id,
            silence_id,
            alert_name,
            severity,
            service,
            duration_minutes,
            starts_at,
            ends_at,
            created_by,
            reason,
            created_at
        FROM alert_silence_actions
        ORDER BY id DESC
        LIMIT :limit
        """,
        params={"limit": limit},
    )


def fetch_alert_response_metrics() -> pd.DataFrame:
    if not table_exists("alert_events") or not table_exists("alert_acknowledgements"):
        return pd.DataFrame()

    return read_sql(
        """
        WITH firing_alerts AS (
            SELECT
                fingerprint,
                COALESCE(alert_name, 'unknown') AS alert_name,
                COALESCE(severity, 'unknown') AS severity,
                COALESCE(service, 'unknown') AS service,
                MIN(COALESCE(starts_at, created_at)) AS first_fired_at
            FROM alert_events
            WHERE status = 'firing'
              AND fingerprint IS NOT NULL
            GROUP BY
                fingerprint,
                COALESCE(alert_name, 'unknown'),
                COALESCE(severity, 'unknown'),
                COALESCE(service, 'unknown')
        ),
        first_acknowledgements AS (
            SELECT
                fingerprint,
                MIN(created_at) AS first_acknowledged_at
            FROM alert_acknowledgements
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
        ),
        resolved_alerts AS (
            SELECT
                fingerprint,
                MIN(COALESCE(ends_at, created_at)) AS first_resolved_at
            FROM alert_events
            WHERE status = 'resolved'
              AND fingerprint IS NOT NULL
            GROUP BY fingerprint
        )
        SELECT
            f.alert_name,
            f.severity,
            f.service,
            COUNT(*) AS alert_count,
            COUNT(a.first_acknowledged_at) AS acknowledged_count,
            COUNT(r.first_resolved_at) AS resolved_count,
            ROUND(
                AVG(
                    EXTRACT(
                        EPOCH FROM (a.first_acknowledged_at - f.first_fired_at)
                    ) / 60
                )::numeric,
                2
            ) AS avg_mtta_minutes,
            ROUND(
                AVG(
                    EXTRACT(
                        EPOCH FROM (r.first_resolved_at - f.first_fired_at)
                    ) / 60
                )::numeric,
                2
            ) AS avg_mttr_minutes,
            MAX(f.first_fired_at) AS latest_fired_at
        FROM firing_alerts f
        LEFT JOIN first_acknowledgements a
            ON f.fingerprint = a.fingerprint
           AND a.first_acknowledged_at >= f.first_fired_at
        LEFT JOIN resolved_alerts r
            ON f.fingerprint = r.fingerprint
           AND r.first_resolved_at >= f.first_fired_at
        GROUP BY
            f.alert_name,
            f.severity,
            f.service
        ORDER BY latest_fired_at DESC
        """
    )


def fetch_alert_response_details(limit: int = 30) -> pd.DataFrame:
    if not table_exists("alert_events") or not table_exists("alert_acknowledgements"):
        return pd.DataFrame()

    return read_sql(
        """
        WITH firing_alerts AS (
            SELECT
                fingerprint,
                COALESCE(alert_name, 'unknown') AS alert_name,
                COALESCE(severity, 'unknown') AS severity,
                COALESCE(service, 'unknown') AS service,
                MIN(COALESCE(starts_at, created_at)) AS first_fired_at
            FROM alert_events
            WHERE status = 'firing'
              AND fingerprint IS NOT NULL
            GROUP BY
                fingerprint,
                COALESCE(alert_name, 'unknown'),
                COALESCE(severity, 'unknown'),
                COALESCE(service, 'unknown')
        ),
        first_acknowledgements AS (
            SELECT
                fingerprint,
                MIN(created_at) AS first_acknowledged_at
            FROM alert_acknowledgements
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
        ),
        resolved_alerts AS (
            SELECT
                fingerprint,
                MIN(COALESCE(ends_at, created_at)) AS first_resolved_at
            FROM alert_events
            WHERE status = 'resolved'
              AND fingerprint IS NOT NULL
            GROUP BY fingerprint
        )
        SELECT
            f.alert_name,
            f.severity,
            f.service,
            f.first_fired_at,
            a.first_acknowledged_at,
            r.first_resolved_at,
            ROUND(
                (
                    EXTRACT(
                        EPOCH FROM (a.first_acknowledged_at - f.first_fired_at)
                    ) / 60
                )::numeric,
                2
            ) AS mtta_minutes,
            ROUND(
                (
                    EXTRACT(
                        EPOCH FROM (r.first_resolved_at - f.first_fired_at)
                    ) / 60
                )::numeric,
                2
            ) AS mttr_minutes,
            CASE
                WHEN a.first_acknowledged_at IS NULL THEN 'NOT_ACKNOWLEDGED'
                ELSE 'ACKNOWLEDGED'
            END AS acknowledgement_status,
            CASE
                WHEN r.first_resolved_at IS NULL THEN 'OPEN'
                ELSE 'RESOLVED'
            END AS resolution_status
        FROM firing_alerts f
        LEFT JOIN first_acknowledgements a
            ON f.fingerprint = a.fingerprint
           AND a.first_acknowledged_at >= f.first_fired_at
        LEFT JOIN resolved_alerts r
            ON f.fingerprint = r.fingerprint
           AND r.first_resolved_at >= f.first_fired_at
        ORDER BY f.first_fired_at DESC
        LIMIT :limit
        """,
        params={"limit": limit},
    )


def fetch_pipeline_failure_summary(limit: int = 20) -> pd.DataFrame:
    return read_sql_if_table_exists(
        "pipeline_check_results",
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
        ORDER BY checked_at DESC
        LIMIT :limit
        """,
        params={"limit": limit},
    )


def fetch_api_quality_summary() -> pd.DataFrame:
    return read_sql_if_table_exists(
        "api_prediction_logs",
        """
        SELECT
            status,
            COUNT(*) AS request_count,
            ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms,
            ROUND(MAX(latency_ms)::numeric, 2) AS max_latency_ms,
            MAX(created_at) AS latest_request_at
        FROM api_prediction_logs
        GROUP BY status
        ORDER BY status
        """,
    )


def build_report() -> str:
    current_firing_alerts = fetch_current_firing_alerts()
    current_alert_summary = fetch_current_alert_summary()
    recent_alert_events = fetch_recent_alert_events()
    recent_acknowledgements = fetch_recent_acknowledgements()
    recent_silence_actions = fetch_recent_silence_actions()
    response_metrics = fetch_alert_response_metrics()
    response_details = fetch_alert_response_details()
    pipeline_failures = fetch_pipeline_failure_summary()
    api_quality_summary = fetch_api_quality_summary()

    firing_count = len(current_firing_alerts)
    acknowledgement_count = len(recent_acknowledgements)
    silence_count = len(recent_silence_actions)

    if response_metrics.empty:
        avg_mtta = None
        avg_mttr = None
    else:
        avg_mtta = response_metrics["avg_mtta_minutes"].dropna().mean()
        avg_mttr = response_metrics["avg_mttr_minutes"].dropna().mean()

    lines = [
        "# JobSkill Incident Response Report",
        "",
        "## Summary",
        "",
        f"- Current firing alerts: **{firing_count}**",
        f"- Recent acknowledgement records: **{acknowledgement_count}**",
        f"- Recent silence actions: **{silence_count}**",
        f"- Average MTTA minutes: **{'-' if pd.isna(avg_mtta) else round(float(avg_mtta), 2)}**",
        f"- Average MTTR minutes: **{'-' if pd.isna(avg_mttr) else round(float(avg_mttr), 2)}**",
        "",
        "## Operational Interpretation",
        "",
    ]

    if firing_count > 0:
        lines.extend(
            [
                "- 현재 firing 상태의 alert가 존재합니다.",
                "- Current Alerts에서 acknowledgement 또는 silence 처리가 필요한지 확인해야 합니다.",
                "- 실제 장애라면 해당 alert의 runbook을 기준으로 원인 확인과 조치를 진행해야 합니다.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- 현재 firing 상태의 alert는 없습니다.",
                "- 최근 alert event와 acknowledgement 이력을 기준으로 대응 품질을 확인하면 됩니다.",
                "",
            ]
        )

    if not response_metrics.empty:
        lines.extend(
            [
                "- MTTA는 alert 발생부터 운영자 확인까지 걸린 시간입니다.",
                "- MTTR은 alert 발생부터 resolved 이벤트 수신까지 걸린 시간입니다.",
                "- MTTA/MTTR이 높다면 alert 확인 지연 또는 장애 해소 지연이 있었는지 확인해야 합니다.",
                "",
            ]
        )

    lines.extend(
        [
            "## Current Alert Summary",
            "",
            dataframe_to_markdown(current_alert_summary),
            "",
            "## Current Firing Alerts",
            "",
            dataframe_to_markdown(current_firing_alerts),
            "",
            "## Alert Response Metrics",
            "",
            dataframe_to_markdown(response_metrics),
            "",
            "## Alert Response Details",
            "",
            dataframe_to_markdown(response_details),
            "",
            "## Recent Acknowledgements",
            "",
            dataframe_to_markdown(recent_acknowledgements),
            "",
            "## Recent Silence Actions",
            "",
            dataframe_to_markdown(recent_silence_actions),
            "",
            "## Recent Alert Events",
            "",
            dataframe_to_markdown(recent_alert_events),
            "",
            "## Recent Pipeline Failures",
            "",
            dataframe_to_markdown(pipeline_failures),
            "",
            "## API Quality Summary",
            "",
            dataframe_to_markdown(api_quality_summary),
            "",
            "## Recommended Next Actions",
            "",
        ]
    )

    if firing_count > 0:
        lines.extend(
            [
                "1. Current firing alert의 runbook을 확인합니다.",
                "2. 실제 장애인지 테스트성 alert인지 구분합니다.",
                "3. 실제 장애라면 조치 내용을 acknowledgement note로 남깁니다.",
                "4. 반복 알림이 예상되면 Alertmanager silence를 생성합니다.",
                "5. 테스트/점검 전체 구간이라면 maintenance mode 사용 여부를 검토합니다.",
            ]
        )
    else:
        lines.extend(
            [
                "1. 최근 acknowledgement와 silence action이 적절히 남았는지 확인합니다.",
                "2. MTTA/MTTR이 과도하게 높다면 대응 지연 원인을 확인합니다.",
                "3. 반복적으로 발생한 alert는 threshold 또는 runbook 보강이 필요한지 검토합니다.",
                "4. 테스트 alert가 지표를 오염시키고 있다면 maintenance mode 또는 silence 사용 기준을 정리합니다.",
            ]
        )

    lines.append("")

    return "\n".join(lines)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"Incident response report generated: {REPORT_PATH}")


if __name__ == "__main__":
    main()
