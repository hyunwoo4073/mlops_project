import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.reporting.generate_incident_response_report import build_report

INCIDENT_REPORT_PATH = PROJECT_ROOT / "reports" / "latest_incident_response_report.md"
MODEL_CARD_PATH = PROJECT_ROOT / "reports" / "latest_model_card.md"


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


@st.cache_resource
def get_engine():
    return create_engine(get_database_url())


def read_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()

    with engine.begin() as conn:
        return pd.read_sql(text(query), conn, params=params)


def get_alertmanager_url() -> str:
    return os.getenv("ALERTMANAGER_URL", "http://alertmanager:9093").rstrip("/")


def render_metric_cards():
    counts_df = read_sql(
        """
        SELECT 'raw_job_posts' AS table_name, COUNT(*) AS row_count FROM raw_job_posts
        UNION ALL
        SELECT 'cleaned_job_posts' AS table_name, COUNT(*) AS row_count FROM cleaned_job_posts
        UNION ALL
        SELECT 'job_post_skills' AS table_name, COUNT(*) AS row_count FROM job_post_skills
        UNION ALL
        SELECT 'model_predictions' AS table_name, COUNT(*) AS row_count FROM model_predictions
        UNION ALL
        SELECT 'pipeline_check_results' AS table_name, COUNT(*) AS row_count FROM pipeline_check_results
        UNION ALL
        SELECT 'model_registry' AS table_name, COUNT(*) AS row_count FROM model_registry
        UNION ALL
        SELECT 'api_prediction_logs' AS table_name, COUNT(*) AS row_count FROM api_prediction_logs
        UNION ALL
        SELECT 'alert_events' AS table_name, COUNT(*) AS row_count FROM alert_events
        UNION ALL
        SELECT 'alert_current_states' AS table_name, COUNT(*) AS row_count FROM alert_current_states
        """
    )

    count_map = dict(zip(counts_df["table_name"], counts_df["row_count"]))

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Raw jobs", int(count_map.get("raw_job_posts", 0)))
    col2.metric("Cleaned jobs", int(count_map.get("cleaned_job_posts", 0)))
    col3.metric("Predictions", int(count_map.get("model_predictions", 0)))
    col4.metric("API logs", int(count_map.get("api_prediction_logs", 0)))
    col5.metric("Alert events", int(count_map.get("alert_events", 0)))
    col6.metric("Current alerts", int(count_map.get("alert_current_states", 0)))


def render_latest_model():
    st.subheader("Latest promoted model")

    df = read_sql(
        """
        SELECT
            id,
            model_name,
            run_id,
            ROUND(accuracy::numeric, 4) AS accuracy,
            ROUND(f1_weighted::numeric, 4) AS f1_weighted,
            status,
            promoted_model_path,
            created_at
        FROM model_registry
        WHERE status = 'PROMOTED'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """
    )

    if df.empty:
        st.info("No promoted model found.")
        return

    row = df.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Model", row["model_name"])
    col2.metric("Accuracy", row["accuracy"])
    col3.metric("F1 weighted", row["f1_weighted"])

    st.dataframe(df, use_container_width=True)


def render_source_quality():
    st.subheader("Source data quality")

    df = read_sql(
        """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            COUNT(*) AS cleaned_count,
            COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
            ROUND(
                COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
                / NULLIF(COUNT(*), 0),
                4
            ) AS unknown_ratio
        FROM cleaned_job_posts c
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        GROUP BY COALESCE(r.source, 'unknown')
        ORDER BY cleaned_count DESC
        """
    )

    if df.empty:
        st.info("No cleaned data found.")
        return

    st.dataframe(df, use_container_width=True)

    fig = px.bar(
        df,
        x="source",
        y="cleaned_count",
        text="cleaned_count",
        title="Cleaned job count by source",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_prediction_quality():
    st.subheader("Batch prediction quality")

    summary_df = read_sql(
        """
        SELECT
            COUNT(*) AS prediction_count,
            ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
            COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count,
            ROUND(
                COUNT(*) FILTER (WHERE is_low_confidence = true)::numeric
                / NULLIF(COUNT(*), 0),
                4
            ) AS low_confidence_ratio
        FROM model_predictions
        WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH'
          AND job_post_id IS NOT NULL
        """
    )

    if summary_df.empty:
        st.info("No batch prediction found.")
        return

    row = summary_df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Batch predictions", int(row["prediction_count"] or 0))
    col2.metric("Avg confidence", row["avg_confidence"])
    col3.metric("Low confidence", int(row["low_confidence_count"] or 0))
    col4.metric("Low ratio", row["low_confidence_ratio"])

    category_df = read_sql(
        """
        SELECT
            predicted_category,
            COUNT(*) AS prediction_count,
            ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
            COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count,
            ROUND(
                COUNT(*) FILTER (WHERE is_low_confidence = true)::numeric
                / NULLIF(COUNT(*), 0),
                4
            ) AS low_confidence_ratio
        FROM model_predictions
        WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH'
          AND job_post_id IS NOT NULL
        GROUP BY predicted_category
        ORDER BY prediction_count DESC
        """
    )

    st.dataframe(category_df, use_container_width=True)

    if not category_df.empty:
        fig = px.bar(
            category_df,
            x="predicted_category",
            y="prediction_count",
            color="avg_confidence",
            text="prediction_count",
            title="Batch predictions by category",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_pipeline_checks():
    st.subheader("Pipeline check results")

    df = read_sql(
        """
        SELECT
            check_type,
            check_name,
            status,
            ROUND(metric_value::numeric, 4) AS metric_value,
            ROUND(threshold_value::numeric, 4) AS threshold_value,
            message,
            checked_at
        FROM pipeline_check_results
        ORDER BY id DESC
        LIMIT 50
        """
    )

    if df.empty:
        st.info("No pipeline check result found.")
        return

    status_df = (
        df.groupby(["check_type", "status"])
        .size()
        .reset_index(name="count")
        .sort_values(["check_type", "status"])
    )

    fig = px.bar(
        status_df,
        x="check_type",
        y="count",
        color="status",
        text="count",
        title="Check result count by type",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)


def render_api_logs():
    st.subheader("FastAPI prediction logs")

    summary_df = read_sql(
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
        """
    )

    if summary_df.empty:
        st.info("No API prediction logs found.")
        return

    st.dataframe(summary_df, use_container_width=True)

    fig = px.bar(
        summary_df,
        x="status",
        y="request_count",
        text="request_count",
        title="API requests by status",
    )
    st.plotly_chart(fig, use_container_width=True)

    recent_df = read_sql(
        """
        SELECT
            id,
            prediction_id,
            request_title,
            response_category,
            ROUND(response_confidence::numeric, 4) AS response_confidence,
            response_confidence_level,
            response_is_low_confidence,
            status,
            ROUND(latency_ms::numeric, 2) AS latency_ms,
            created_at
        FROM api_prediction_logs
        ORDER BY id DESC
        LIMIT 30
        """
    )

    st.dataframe(recent_df, use_container_width=True)


def render_recent_predictions():
    st.subheader("Recent predictions")

    df = read_sql(
        """
        SELECT
            id,
            prediction_source,
            job_post_id,
            predicted_category,
            ROUND(confidence::numeric, 4) AS confidence,
            confidence_level,
            is_low_confidence,
            model_name,
            model_run_id,
            model_registry_id,
            predicted_at
        FROM model_predictions
        ORDER BY id DESC
        LIMIT 50
        """
    )

    if df.empty:
        st.info("No prediction found.")
        return

    st.dataframe(df, use_container_width=True)


def fetch_alert_summary() -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        SELECT
            COALESCE(alert_name, 'unknown') AS alert_name,
            COALESCE(severity, 'unknown') AS severity,
            COALESCE(service, 'unknown') AS service,
            status,
            COUNT(*) AS alert_count,
            MAX(created_at) AS latest_created_at
        FROM alert_events
        GROUP BY
            COALESCE(alert_name, 'unknown'),
            COALESCE(severity, 'unknown'),
            COALESCE(service, 'unknown'),
            status
        ORDER BY latest_created_at DESC
        """
    )

    with engine.begin() as conn:
        return pd.read_sql(query, conn)

def parse_bool(value) -> bool:
    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def ensure_alert_settings_table() -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alert_settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value VARCHAR(100) NOT NULL,
                    description TEXT,
                    updated_by VARCHAR(100),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO alert_settings (
                    setting_key,
                    setting_value,
                    description,
                    updated_by
                )
                VALUES (
                    'maintenance_mode',
                    'false',
                    'Suppress non-critical Prometheus alert rules during testing or maintenance.',
                    'system'
                )
                ON CONFLICT (setting_key) DO NOTHING
                """
            )
        )


def fetch_alert_maintenance_mode() -> dict:
    ensure_alert_settings_table()

    df = read_sql(
        """
        SELECT
            setting_key,
            setting_value,
            description,
            updated_by,
            updated_at
        FROM alert_settings
        WHERE setting_key = 'maintenance_mode'
        """
    )

    if df.empty:
        return {
            "setting_key": "maintenance_mode",
            "setting_value": "false",
            "description": "Suppress non-critical Prometheus alert rules during testing or maintenance.",
            "updated_by": "system",
            "updated_at": None,
        }

    return df.iloc[0].to_dict()


def update_alert_maintenance_mode(enabled: bool, updated_by: str) -> None:
    ensure_alert_settings_table()

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO alert_settings (
                    setting_key,
                    setting_value,
                    description,
                    updated_by,
                    updated_at
                )
                VALUES (
                    'maintenance_mode',
                    :setting_value,
                    'Suppress non-critical Prometheus alert rules during testing or maintenance.',
                    :updated_by,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (setting_key)
                DO UPDATE SET
                    setting_value = EXCLUDED.setting_value,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "setting_value": "true" if enabled else "false",
                "updated_by": updated_by,
            },
        )


def render_alert_maintenance_mode_section() -> None:
    st.subheader("Alert Maintenance Mode")

    setting = fetch_alert_maintenance_mode()
    enabled = parse_bool(setting["setting_value"])

    if enabled:
        st.warning(
            "Maintenance mode is ON. Non-critical Prometheus alert rules are suppressed."
        )
    else:
        st.success(
            "Maintenance mode is OFF. Non-critical Prometheus alert rules are active."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric("Maintenance Mode", "ON" if enabled else "OFF")
    col2.metric("Updated By", setting.get("updated_by") or "-")
    col3.metric("Updated At", str(setting.get("updated_at") or "-"))

    updated_by = st.text_input(
        "변경자",
        value=os.getenv("USER", "local-user"),
        key="maintenance_mode_updated_by",
    )

    button_col1, button_col2 = st.columns(2)

    with button_col1:
        if st.button(
            "Enable maintenance mode",
            type="primary",
            disabled=enabled,
        ):
            update_alert_maintenance_mode(
                enabled=True,
                updated_by=updated_by.strip() or "local-user",
            )
            st.success("Maintenance mode enabled.")
            st.rerun()

    with button_col2:
        if st.button(
            "Disable maintenance mode",
            disabled=not enabled,
        ):
            update_alert_maintenance_mode(
                enabled=False,
                updated_by=updated_by.strip() or "local-user",
            )
            st.success("Maintenance mode disabled.")
            st.rerun()

    st.caption(
        "Maintenance mode is exposed as "
        "`jobskill_alert_maintenance_mode` from FastAPI `/metrics`. "
        "Prometheus suppresses non-critical alert rules when this value is 1."
    )


def fetch_current_alert_states() -> pd.DataFrame:
    return read_sql(
        """
        SELECT
            fingerprint,
            status,
            alert_name,
            severity,
            service,
            instance,
            summary,
            description,

            COALESCE(
                annotations ->> 'runbook_url',
                CASE
                    WHEN alert_name = 'JobSkillApiMetricsDown'
                        THEN 'http://localhost:8000/runbooks/jobskill_api_metrics_down.md'
                    WHEN alert_name IN (
                        'JobSkillApiHighLowConfidenceRatio',
                        'JobSkillBatchHighLowConfidenceRatio'
                    )
                        THEN 'http://localhost:8000/runbooks/jobskill_high_low_confidence_ratio.md'
                    WHEN alert_name = 'JobSkillApiHighLatency'
                        THEN 'http://localhost:8000/runbooks/jobskill_api_high_latency.md'
                    WHEN alert_name = 'JobSkillPipelineCheckFailure'
                        THEN 'http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md'
                    WHEN alert_name IN (
                        'JobSkillPromotedModelLowAccuracy',
                        'JobSkillPromotedModelLowF1'
                    )
                        THEN 'http://localhost:8000/runbooks/jobskill_promoted_model_low_performance.md'
                    ELSE 'http://localhost:8000/runbooks'
                END
            ) AS runbook_url,

            COALESCE(
                annotations ->> 'dashboard_url',
                'http://localhost:3000'
            ) AS dashboard_url,

            COALESCE(
                annotations ->> 'prometheus_url',
                'http://localhost:9090/alerts'
            ) AS prometheus_url,

            starts_at,
            ends_at,
            last_received_at,
            updated_at
        FROM alert_current_states
        ORDER BY
            CASE
                WHEN status = 'firing' THEN 0
                ELSE 1
            END,
            updated_at DESC
        """
    )


def get_alert_link_column_config() -> dict:
    return {
        "runbook_url": st.column_config.LinkColumn(
            "Runbook",
            display_text="Open runbook",
        ),
        "dashboard_url": st.column_config.LinkColumn(
            "Grafana",
            display_text="Open Grafana",
        ),
        "prometheus_url": st.column_config.LinkColumn(
            "Prometheus",
            display_text="Open Prometheus",
        ),
    }


def create_alert_acknowledgement(
    fingerprint: str | None,
    alert_name: str | None,
    severity: str | None,
    service: str | None,
    status: str | None,
    acknowledged_by: str,
    note: str,
) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO alert_acknowledgements (
                    fingerprint,
                    alert_name,
                    severity,
                    service,
                    status,
                    acknowledged_by,
                    note
                )
                VALUES (
                    :fingerprint,
                    :alert_name,
                    :severity,
                    :service,
                    :status,
                    :acknowledged_by,
                    :note
                )
                """
            ),
            {
                "fingerprint": fingerprint,
                "alert_name": alert_name,
                "severity": severity,
                "service": service,
                "status": status,
                "acknowledged_by": acknowledged_by,
                "note": note,
            },
        )


def create_alertmanager_silence(
    alert: pd.Series,
    duration_minutes: int,
    created_by: str,
    reason: str,
) -> str:
    alertmanager_url = get_alertmanager_url()

    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(minutes=duration_minutes)

    alert_name = str(alert.get("alert_name") or "")
    service = str(alert.get("service") or "")
    severity = str(alert.get("severity") or "")

    matchers = [
        {
            "name": "alertname",
            "value": alert_name,
            "isRegex": False,
            "isEqual": True,
        }
    ]

    if service:
        matchers.append(
            {
                "name": "service",
                "value": service,
                "isRegex": False,
                "isEqual": True,
            }
        )

    if severity:
        matchers.append(
            {
                "name": "severity",
                "value": severity,
                "isRegex": False,
                "isEqual": True,
            }
        )

    payload = {
        "matchers": matchers,
        "startsAt": now.isoformat().replace("+00:00", "Z"),
        "endsAt": ends_at.isoformat().replace("+00:00", "Z"),
        "createdBy": created_by,
        "comment": reason,
    }

    response = requests.post(
        f"{alertmanager_url}/api/v2/silences",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()

    result = response.json()

    return result["silenceID"]


def expire_alertmanager_silence(silence_id: str) -> None:
    alertmanager_url = get_alertmanager_url()

    response = requests.delete(
        f"{alertmanager_url}/api/v2/silence/{silence_id}",
        timeout=10,
    )
    response.raise_for_status()


def save_alert_silence_action(
    silence_id: str,
    alert: pd.Series | None,
    duration_minutes: int | None,
    created_by: str,
    reason: str,
    action_type: str = "CREATE",
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> None:
    engine = get_engine()

    now = datetime.now(timezone.utc)

    if starts_at is None:
        starts_at = now

    if ends_at is None and duration_minutes is not None:
        ends_at = now + timedelta(minutes=duration_minutes)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO alert_silence_actions (
                    silence_id,
                    fingerprint,
                    alert_name,
                    severity,
                    service,
                    instance,
                    action_type,
                    duration_minutes,
                    starts_at,
                    ends_at,
                    created_by,
                    reason
                )
                VALUES (
                    :silence_id,
                    :fingerprint,
                    :alert_name,
                    :severity,
                    :service,
                    :instance,
                    :action_type,
                    :duration_minutes,
                    :starts_at,
                    :ends_at,
                    :created_by,
                    :reason
                )
                """
            ),
            {
                "silence_id": silence_id,
                "fingerprint": alert.get("fingerprint") if alert is not None else None,
                "alert_name": alert.get("alert_name") if alert is not None else None,
                "severity": alert.get("severity") if alert is not None else None,
                "service": alert.get("service") if alert is not None else None,
                "instance": alert.get("instance") if alert is not None else None,
                "action_type": action_type,
                "duration_minutes": duration_minutes,
                "starts_at": starts_at.replace(tzinfo=None) if starts_at else None,
                "ends_at": ends_at.replace(tzinfo=None) if ends_at else None,
                "created_by": created_by,
                "reason": reason,
            },
        )


def fetch_recent_alert_silence_actions(limit: int = 30) -> pd.DataFrame:
    return read_sql(
        """
        SELECT
            id,
            action_type,
            silence_id,
            alert_name,
            severity,
            service,
            instance,
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


def fetch_alertmanager_silences() -> pd.DataFrame:
    alertmanager_url = get_alertmanager_url()

    try:
        response = requests.get(
            f"{alertmanager_url}/api/v2/silences",
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        st.warning(f"Alertmanager silence 목록을 조회하지 못했습니다: {exc}")
        return pd.DataFrame()

    silences = response.json()

    rows = []

    for silence in silences:
        rows.append(
            {
                "id": silence.get("id"),
                "state": silence.get("status", {}).get("state"),
                "created_by": silence.get("createdBy"),
                "comment": silence.get("comment"),
                "starts_at": silence.get("startsAt"),
                "ends_at": silence.get("endsAt"),
                "updated_at": silence.get("updatedAt"),
                "matchers": silence.get("matchers"),
            }
        )

    return pd.DataFrame(rows)


def format_silence_option(row: pd.Series) -> str:
    matchers = row.get("matchers")

    if isinstance(matchers, list):
        matcher_text = ", ".join(
            f"{matcher.get('name')}={matcher.get('value')}"
            for matcher in matchers
        )
    else:
        matcher_text = "-"

    return (
        f"{row.get('state')} | "
        f"{row.get('id')} | "
        f"{matcher_text} | "
        f"ends_at={row.get('ends_at')}"
    )


def fetch_recent_alert_acknowledgements(limit: int = 30) -> pd.DataFrame:
    return read_sql(
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


def format_alert_option(row: pd.Series) -> str:
    fingerprint = str(row.get("fingerprint") or "")
    fingerprint_short = fingerprint[:8] if fingerprint else "no-fp"

    return (
        f"{row.get('status')} | "
        f"{row.get('alert_name')} | "
        f"{row.get('service')} | "
        f"{row.get('severity')} | "
        f"{fingerprint_short}"
    )


def fetch_recent_alert_events(limit: int = 50) -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        SELECT
            id,
            status,
            alert_name,
            severity,
            service,
            instance,
            summary,
            description,

            COALESCE(
                annotations ->> 'runbook_url',
                CASE
                    WHEN alert_name = 'JobSkillApiMetricsDown'
                        THEN 'http://localhost:8000/runbooks/jobskill_api_metrics_down.md'
                    WHEN alert_name IN (
                        'JobSkillApiHighLowConfidenceRatio',
                        'JobSkillBatchHighLowConfidenceRatio'
                    )
                        THEN 'http://localhost:8000/runbooks/jobskill_high_low_confidence_ratio.md'
                    WHEN alert_name = 'JobSkillApiHighLatency'
                        THEN 'http://localhost:8000/runbooks/jobskill_api_high_latency.md'
                    WHEN alert_name = 'JobSkillPipelineCheckFailure'
                        THEN 'http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md'
                    WHEN alert_name IN (
                        'JobSkillPromotedModelLowAccuracy',
                        'JobSkillPromotedModelLowF1'
                    )
                        THEN 'http://localhost:8000/runbooks/jobskill_promoted_model_low_performance.md'
                    ELSE 'http://localhost:8000/runbooks'
                END
            ) AS runbook_url,

            COALESCE(
                annotations ->> 'dashboard_url',
                'http://localhost:3000'
            ) AS dashboard_url,

            COALESCE(
                annotations ->> 'prometheus_url',
                'http://localhost:9090/alerts'
            ) AS prometheus_url,

            starts_at,
            ends_at,
            created_at
        FROM alert_events
        ORDER BY id DESC
        LIMIT :limit
        """
    )

    with engine.begin() as conn:
        return pd.read_sql(query, conn, params={"limit": limit})


def fetch_alert_status_counts() -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        SELECT
            status,
            COUNT(*) AS count
        FROM alert_events
        GROUP BY status
        ORDER BY status
        """
    )

    with engine.begin() as conn:
        return pd.read_sql(query, conn)


def fetch_alert_severity_counts() -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        SELECT
            COALESCE(severity, 'unknown') AS severity,
            COUNT(*) AS count
        FROM alert_events
        GROUP BY COALESCE(severity, 'unknown')
        ORDER BY count DESC
        """
    )

    with engine.begin() as conn:
        return pd.read_sql(query, conn)


def dashboard_table_exists(table_name: str) -> bool:
    engine = get_engine()

    with engine.begin() as conn:
        return bool(
            conn.execute(
                text("SELECT to_regclass(:table_name) IS NOT NULL"),
                {"table_name": f"public.{table_name}"},
            ).scalar()
        )


def fetch_current_promoted_model() -> pd.DataFrame:
    return read_sql("""
        SELECT
            id,
            model_name,
            NULL::text AS model_version,
            run_id AS model_run_id,
            status,
            promoted_model_path,
            ROUND(accuracy::numeric, 4) AS accuracy,
            ROUND(f1_weighted::numeric, 4) AS f1_weighted,
            created_at
        FROM model_registry
        WHERE status = 'PROMOTED'
        ORDER BY id DESC
        LIMIT 1
    """)


def fetch_model_promotion_archives(limit: int = 50) -> pd.DataFrame:
    if not dashboard_table_exists("model_promotion_archives"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            id,
            model_registry_id,
            model_name,
            model_version,
            model_run_id,
            source_model_path,
            archived_model_path,
            accuracy,
            f1_weighted,
            archive_reason,
            created_by,
            created_at
        FROM model_promotion_archives
        ORDER BY id DESC
        LIMIT :limit
    """, params={"limit": limit})


def fetch_model_rollback_actions(limit: int = 50) -> pd.DataFrame:
    if not dashboard_table_exists("model_rollback_actions"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            id,
            archive_id,
            target_model_registry_id,
            previous_model_registry_id,
            archived_model_path,
            restored_model_path,
            backup_model_path,
            rollback_reason,
            created_by,
            status,
            created_at
        FROM model_rollback_actions
        ORDER BY id DESC
        LIMIT :limit
    """, params={"limit": limit})


def fetch_model_lifecycle_summary() -> dict:
    archive_df = fetch_model_promotion_archives(limit=1000)
    rollback_df = fetch_model_rollback_actions(limit=1000)

    return {
        "archive_count": 0 if archive_df.empty else len(archive_df),
        "rollback_count": 0 if rollback_df.empty else len(rollback_df),
        "latest_archive_at": "-" if archive_df.empty else str(archive_df.iloc[0]["created_at"]),
        "latest_rollback_at": "-" if rollback_df.empty else str(rollback_df.iloc[0]["created_at"]),
    }


def format_archive_option(row: pd.Series) -> str:
    return (
        f"archive_id={row.get('id')} | "
        f"registry_id={row.get('model_registry_id')} | "
        f"f1={row.get('f1_weighted')} | "
        f"created_at={row.get('created_at')}"
    )


def render_alert_silence_section(target_df: pd.DataFrame) -> None:
    st.subheader("Silence Alert")

    if target_df.empty:
        st.info("Silence할 alert가 없습니다.")
        return

    selected_index = st.selectbox(
        "Silence 대상 alert 선택",
        options=target_df.index.tolist(),
        format_func=lambda index: format_alert_option(target_df.loc[index]),
        key="alert_silence_target",
    )

    selected_alert = target_df.loc[selected_index]

    with st.form("alert_silence_form", clear_on_submit=True):
        duration_option = st.selectbox(
            "Silence duration",
            options=[
                "30 minutes",
                "1 hour",
                "2 hours",
                "Custom",
            ],
        )

        custom_minutes = st.number_input(
            "Custom duration minutes",
            min_value=5,
            max_value=1440,
            value=int(os.getenv("ALERT_SILENCE_DEFAULT_MINUTES", "30")),
            step=5,
            disabled=duration_option != "Custom",
        )

        created_by = st.text_input(
            "처리자",
            value=os.getenv("USER", "local-user"),
            key="alert_silence_created_by",
        )

        reason = st.text_area(
            "Silence 사유",
            placeholder=(
                "예: API low confidence alert 테스트 중. "
                "30분 동안 Slack 알림을 억제하고 원인 확인 예정."
            ),
            height=120,
        )

        submitted = st.form_submit_button("Create silence")

        if submitted:
            if duration_option == "30 minutes":
                duration_minutes = 30
            elif duration_option == "1 hour":
                duration_minutes = 60
            elif duration_option == "2 hours":
                duration_minutes = 120
            else:
                duration_minutes = int(custom_minutes)

            if not reason.strip():
                st.warning("Silence 사유를 입력해야 합니다.")
                return

            try:
                silence_id = create_alertmanager_silence(
                    alert=selected_alert,
                    duration_minutes=duration_minutes,
                    created_by=created_by.strip() or "local-user",
                    reason=reason.strip(),
                )

                save_alert_silence_action(
                    silence_id=silence_id,
                    alert=selected_alert,
                    duration_minutes=duration_minutes,
                    created_by=created_by.strip() or "local-user",
                    reason=reason.strip(),
                    action_type="CREATE",
                )

                st.success(f"Alertmanager silence created: {silence_id}")
                st.rerun()

            except requests.RequestException as exc:
                st.error(f"Alertmanager silence 생성 실패: {exc}")


def render_alert_silence_management_section() -> None:
    st.subheader("Manage Alertmanager Silences")

    silences_df = fetch_alertmanager_silences()

    if silences_df.empty:
        st.info("No Alertmanager silence found.")
        return

    active_silences_df = silences_df[
        silences_df["state"].fillna("").str.lower() == "active"
    ]

    st.caption(
        "Active 상태의 Alertmanager silence를 선택해 수동으로 expire 처리할 수 있습니다."
    )

    st.dataframe(
        silences_df,
        use_container_width=True,
        hide_index=True,
    )

    if active_silences_df.empty:
        st.success("No active Alertmanager silence.")
        return

    selected_index = st.selectbox(
        "Expire 대상 silence 선택",
        options=active_silences_df.index.tolist(),
        format_func=lambda index: format_silence_option(active_silences_df.loc[index]),
        key="expire_silence_target",
    )

    selected_silence = active_silences_df.loc[selected_index]

    with st.form("expire_silence_form", clear_on_submit=True):
        expired_by = st.text_input(
            "처리자",
            value=os.getenv("USER", "local-user"),
            key="expire_silence_created_by",
        )

        reason = st.text_area(
            "해제 사유",
            placeholder=(
                "예: 테스트 완료로 silence 해제. "
                "이후 alert notification이 정상 전송되는지 확인 예정."
            ),
            height=100,
        )

        submitted = st.form_submit_button("Expire selected silence")

        if submitted:
            if not reason.strip():
                st.warning("해제 사유를 입력해야 합니다.")
                return

            silence_id = str(selected_silence.get("id"))

            try:
                expire_alertmanager_silence(silence_id)

                save_alert_silence_action(
                    silence_id=silence_id,
                    alert=None,
                    duration_minutes=None,
                    created_by=expired_by.strip() or "local-user",
                    reason=reason.strip(),
                    action_type="EXPIRE",
                )

                st.success(f"Alertmanager silence expired: {silence_id}")
                st.rerun()

            except requests.RequestException as exc:
                st.error(f"Alertmanager silence expire 실패: {exc}")


def render_current_alerts_section() -> None:
    st.header("Current Alerts")

    render_alert_maintenance_mode_section()

    st.divider()

    df = fetch_current_alert_states()

    if df.empty:
        st.success("No current alert states found.")
        return

    firing_df = df[df["status"].str.lower() == "firing"]
    resolved_df = df[df["status"].str.lower() == "resolved"]

    warning_count = int(
        firing_df[firing_df["severity"].fillna("").str.lower() == "warning"].shape[0]
    )
    critical_count = int(
        firing_df[firing_df["severity"].fillna("").str.lower() == "critical"].shape[0]
    )

    latest_updated_at = df["updated_at"].max()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Current Alert States", len(df))
    col2.metric("Firing", len(firing_df))
    col3.metric("Resolved", len(resolved_df))
    col4.metric("Warning Firing", warning_count)
    col5.metric("Critical Firing", critical_count)

    st.caption(f"Latest updated at: {latest_updated_at}")

    alert_column_order = [
        "status",
        "alert_name",
        "severity",
        "service",
        "summary",
        "description",
        "runbook_url",
        "dashboard_url",
        "prometheus_url",
        "instance",
        "starts_at",
        "ends_at",
        "last_received_at",
        "updated_at",
    ]

    alert_column_config = get_alert_link_column_config()

    st.subheader("Firing Alerts")

    if firing_df.empty:
        st.success("No firing alerts.")
    else:
        st.dataframe(
            firing_df,
            use_container_width=True,
            hide_index=True,
            column_order=alert_column_order,
            column_config=alert_column_config,
        )

    target_df = firing_df if not firing_df.empty else df

    render_alert_silence_section(target_df)

    st.subheader("Acknowledge Alert")

    selected_index = st.selectbox(
        "Alert 선택",
        options=target_df.index.tolist(),
        format_func=lambda index: format_alert_option(target_df.loc[index]),
    )

    selected_alert = target_df.loc[selected_index]

    with st.form("alert_acknowledgement_form", clear_on_submit=True):
        acknowledged_by = st.text_input(
            "확인자",
            value=os.getenv("USER", "local-user"),
        )

        note = st.text_area(
            "조치 메모",
            placeholder=(
                "예: API low confidence alert 확인. "
                "테스트 요청으로 인한 발생으로 판단하여 rule threshold 조정 예정."
            ),
            height=120,
        )

        submitted = st.form_submit_button("Save acknowledgement")

        if submitted:
            if not note.strip():
                st.warning("조치 메모를 입력해야 합니다.")
            else:
                create_alert_acknowledgement(
                    fingerprint=selected_alert.get("fingerprint"),
                    alert_name=selected_alert.get("alert_name"),
                    severity=selected_alert.get("severity"),
                    service=selected_alert.get("service"),
                    status=selected_alert.get("status"),
                    acknowledged_by=acknowledged_by.strip() or "local-user",
                    note=note.strip(),
                )
                st.success("Alert acknowledgement saved.")
                st.rerun()

    st.subheader("Recent Acknowledgements")

    ack_df = fetch_recent_alert_acknowledgements()

    if ack_df.empty:
        st.info("No alert acknowledgement found.")
    else:
        st.dataframe(
            ack_df,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Recent Silence Actions")

    silence_action_df = fetch_recent_alert_silence_actions()

    if silence_action_df.empty:
        st.info("No alert silence action found.")
    else:
        st.dataframe(
            silence_action_df,
            use_container_width=True,
            hide_index=True,
        )

    render_alert_silence_management_section()
    st.subheader("All Current Alert States")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_order=alert_column_order,
        column_config=alert_column_config,
    )


def fetch_alert_response_metrics() -> pd.DataFrame:
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


def fetch_recent_alert_response_details(limit: int = 50) -> pd.DataFrame:
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
            f.fingerprint,
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


def fetch_latest_model_class_performance_checks():
    query = """
        WITH latest_group AS (
            SELECT
                COALESCE(run_id, 'manual') AS run_key,
                MAX(checked_at) AS latest_checked_at
            FROM pipeline_check_results
            WHERE check_type = 'MODEL_CLASS_PERFORMANCE'
            GROUP BY COALESCE(run_id, 'manual')
            ORDER BY latest_checked_at DESC
            LIMIT 1
        )
        SELECT
            p.check_type,
            p.check_name,
            p.status,
            ROUND(p.metric_value::numeric, 4) AS metric_value,
            ROUND(p.threshold_value::numeric, 4) AS threshold_value,
            p.message,
            p.dag_id,
            p.task_id,
            p.run_id,
            p.checked_at
        FROM pipeline_check_results p
        JOIN latest_group l
          ON COALESCE(p.run_id, 'manual') = l.run_key
        WHERE p.check_type = 'MODEL_CLASS_PERFORMANCE'
          AND p.checked_at >= l.latest_checked_at - INTERVAL '10 minutes'
        ORDER BY p.checked_at DESC, p.check_name
    """

    return read_sql(query)


def build_class_performance_summary(checks_df):
    if checks_df.empty:
        return checks_df

    rows = []

    for _, row in checks_df.iterrows():
        check_name = str(row.get("check_name", ""))

        if "." not in check_name:
            continue

        label_key, metric_name = check_name.rsplit(".", 1)

        if metric_name not in {"support", "recall", "f1"}:
            continue

        rows.append(
            {
                "label": label_key.replace("_", " "),
                "metric": metric_name,
                "status": row.get("status"),
                "metric_value": row.get("metric_value"),
                "threshold_value": row.get("threshold_value"),
                "message": row.get("message"),
                "checked_at": row.get("checked_at"),
            }
        )

    if not rows:
        return pd.DataFrame()

    metric_df = pd.DataFrame(rows)

    value_pivot = (
        metric_df.pivot_table(
            index="label",
            columns="metric",
            values="metric_value",
            aggfunc="last",
        )
        .reset_index()
    )

    threshold_pivot = (
        metric_df.pivot_table(
            index="label",
            columns="metric",
            values="threshold_value",
            aggfunc="last",
        )
        .reset_index()
        .rename(
            columns={
                "support": "support_threshold",
                "recall": "recall_threshold",
                "f1": "f1_threshold",
            }
        )
    )

    status_summary = (
        metric_df.groupby("label")["status"]
        .apply(lambda values: "FAIL" if "FAIL" in set(values) else "PASS")
        .reset_index()
        .rename(columns={"status": "overall_status"})
    )

    result = value_pivot.merge(threshold_pivot, on="label", how="left")
    result = result.merge(status_summary, on="label", how="left")

    preferred_columns = [
        "label",
        "overall_status",
        "support",
        "support_threshold",
        "recall",
        "recall_threshold",
        "f1",
        "f1_threshold",
    ]

    existing_columns = [column for column in preferred_columns if column in result.columns]

    return result[existing_columns].sort_values(
        by=["overall_status", "label"],
        ascending=[True, True],
    )


def render_alert_response_metrics() -> None:
    st.subheader("Alert Response Metrics")

    summary_df = fetch_alert_response_metrics()
    detail_df = fetch_recent_alert_response_details()

    if summary_df.empty:
        st.info("No alert response metrics found.")
        return

    total_alert_count = int(summary_df["alert_count"].sum())
    total_acknowledged_count = int(summary_df["acknowledged_count"].sum())
    total_resolved_count = int(summary_df["resolved_count"].sum())

    avg_mtta = summary_df["avg_mtta_minutes"].dropna().mean()
    avg_mttr = summary_df["avg_mttr_minutes"].dropna().mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Alert groups", total_alert_count)
    col2.metric("Acknowledged", total_acknowledged_count)
    col3.metric("Resolved", total_resolved_count)
    col4.metric(
        "Avg MTTA",
        "-" if pd.isna(avg_mtta) else f"{avg_mtta:.2f} min",
    )
    col5.metric(
        "Avg MTTR",
        "-" if pd.isna(avg_mttr) else f"{avg_mttr:.2f} min",
    )

    st.caption(
        "MTTA는 alert firing부터 acknowledgement 저장까지의 시간이고, "
        "MTTR은 alert firing부터 resolved 이벤트 수신까지의 시간입니다."
    )

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
    )

    if not summary_df.empty:
        chart_df = summary_df.dropna(subset=["avg_mtta_minutes"])

        if not chart_df.empty:
            fig = px.bar(
                chart_df,
                x="alert_name",
                y="avg_mtta_minutes",
                color="severity",
                text="avg_mtta_minutes",
                title="Average MTTA by alert",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Alert Response Details")

    if detail_df.empty:
        st.info("No alert response detail found.")
    else:
        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
        )


def render_alert_history_section() -> None:
    st.header("Alert History")

    alert_summary_df = fetch_alert_summary()
    recent_alerts_df = fetch_recent_alert_events()
    status_counts_df = fetch_alert_status_counts()
    severity_counts_df = fetch_alert_severity_counts()

    if alert_summary_df.empty:
        st.info("No alert events found.")
        return

    total_alert_count = int(alert_summary_df["alert_count"].sum())
    firing_event_count = int(
        alert_summary_df.loc[
            alert_summary_df["status"].str.lower() == "firing",
            "alert_count",
        ].sum()
    )
    resolved_event_count = int(
        alert_summary_df.loc[
            alert_summary_df["status"].str.lower() == "resolved",
            "alert_count",
        ].sum()
    )
    latest_created_at = alert_summary_df["latest_created_at"].max()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Alert Events", total_alert_count)
    col2.metric("Firing Events", firing_event_count)
    col3.metric("Resolved Events", resolved_event_count)
    col4.metric("Latest Event", str(latest_created_at))

    render_alert_response_metrics()
    
    st.subheader("Alert Event Status Distribution")

    if not status_counts_df.empty:
        fig = px.bar(
            status_counts_df,
            x="status",
            y="count",
            text="count",
            title="Alert Events by Status",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Alert Event Severity Distribution")

    if not severity_counts_df.empty:
        fig = px.bar(
            severity_counts_df,
            x="severity",
            y="count",
            text="count",
            title="Alert Events by Severity",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Alert Event Summary")

    st.dataframe(
        alert_summary_df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Recent Alert Event History")

    st.dataframe(
        recent_alerts_df,
        use_container_width=True,
        hide_index=True,
        column_config=get_alert_link_column_config(),
    )


def generate_incident_report_from_dashboard() -> str:
    INCIDENT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    INCIDENT_REPORT_PATH.write_text(report, encoding="utf-8")

    return report


def read_incident_report() -> str | None:
    if not INCIDENT_REPORT_PATH.exists():
        return None

    return INCIDENT_REPORT_PATH.read_text(encoding="utf-8")


def generate_model_card_from_dashboard() -> str | None:
    from src.reporting.generate_model_card import main as generate_model_card_main

    generate_model_card_main()

    return read_model_card()


def read_model_card() -> str | None:
    if not MODEL_CARD_PATH.exists():
        return None

    return MODEL_CARD_PATH.read_text(encoding="utf-8")


def get_model_card_updated_at() -> str:
    if not MODEL_CARD_PATH.exists():
        return "-"

    updated_at = MODEL_CARD_PATH.stat().st_mtime

    return pd.to_datetime(updated_at, unit="s").strftime("%Y-%m-%d %H:%M:%S")


def get_incident_report_updated_at() -> str:
    if not INCIDENT_REPORT_PATH.exists():
        return "-"

    updated_at = INCIDENT_REPORT_PATH.stat().st_mtime

    return pd.to_datetime(updated_at, unit="s").strftime("%Y-%m-%d %H:%M:%S")


def render_incident_report_section() -> None:
    st.header("Incident Response Report")

    st.caption(
        "Alert events, current alert states, acknowledgements, silences, "
        "MTTA/MTTR, pipeline failures, API quality를 하나의 Markdown 리포트로 생성합니다."
    )

    col1, col2, col3 = st.columns(3)

    report_exists = INCIDENT_REPORT_PATH.exists()
    report_updated_at = get_incident_report_updated_at()

    col1.metric("Report file", "Exists" if report_exists else "Not found")
    col2.metric("Updated at", report_updated_at)
    col3.metric("Path", str(INCIDENT_REPORT_PATH.relative_to(PROJECT_ROOT)))

    button_col1, button_col2 = st.columns([1, 3])

    with button_col1:
        generate_clicked = st.button(
            "Generate incident report",
            type="primary",
        )

    if generate_clicked:
        try:
            report = generate_incident_report_from_dashboard()
            st.success("Incident response report generated.")
        except Exception as exc:
            st.error(f"Incident response report 생성 실패: {exc}")
            return
    else:
        report = read_incident_report()

    if report is None:
        st.info("아직 생성된 incident response report가 없습니다.")
        st.code(
            "make incident-report",
            language="bash",
        )
        return

    st.download_button(
        label="Download Markdown report",
        data=report,
        file_name="latest_incident_response_report.md",
        mime="text/markdown",
    )

    st.subheader("Report Preview")

    st.markdown(report)


def render_model_card_section() -> None:
    st.header("Model Card")

    st.caption(
        "현재 PROMOTED 모델의 성능, 학습 데이터, MLflow run, archive/rollback 정보를 "
        "Markdown Model Card로 조회합니다."
    )

    col1, col2, col3 = st.columns(3)

    model_card_exists = MODEL_CARD_PATH.exists()
    model_card_updated_at = get_model_card_updated_at()

    col1.metric("Model Card file", "Exists" if model_card_exists else "Not found")
    col2.metric("Updated at", model_card_updated_at)
    col3.metric("Path", str(MODEL_CARD_PATH.relative_to(PROJECT_ROOT)))

    button_col1, button_col2 = st.columns([1, 3])

    with button_col1:
        generate_clicked = st.button(
            "Generate model card",
            type="primary",
        )

    if generate_clicked:
        try:
            model_card = generate_model_card_from_dashboard()
            st.success("Model card generated.")
        except Exception as exc:
            st.error(f"Model card 생성 실패: {exc}")
            return
    else:
        model_card = read_model_card()

    if model_card is None:
        st.info("아직 생성된 Model Card가 없습니다.")
        st.code(
            "make model-card",
            language="bash",
        )
        return

    st.download_button(
        label="Download Markdown model card",
        data=model_card,
        file_name="latest_model_card.md",
        mime="text/markdown",
    )

    st.subheader("Model Card Preview")

    st.markdown(model_card)


def render_model_lifecycle_section() -> None:
    st.header("Model Lifecycle")

    st.caption(
        "현재 promoted model, promoted model archive 이력, rollback action 이력을 조회합니다. "
        "실제 rollback은 안전을 위해 CLI 명령으로 수행합니다."
    )

    current_model_df = fetch_current_promoted_model()
    archive_df = fetch_model_promotion_archives()
    rollback_df = fetch_model_rollback_actions()
    summary = fetch_model_lifecycle_summary()

    st.subheader("Current Promoted Model")

    if current_model_df.empty:
        st.warning("현재 PROMOTED 상태의 모델이 없습니다.")
    else:
        current_model = current_model_df.iloc[0]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Registry ID", str(current_model.get("id")))
        col2.metric("Accuracy", str(current_model.get("accuracy")))
        col3.metric("F1 Weighted", str(current_model.get("f1_weighted")))
        col4.metric("Status", str(current_model.get("status")))

        st.dataframe(current_model_df, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Model Lifecycle Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Archived Models", summary["archive_count"])
    col2.metric("Rollback Actions", summary["rollback_count"])
    col3.metric("Latest Archive", summary["latest_archive_at"])
    col4.metric("Latest Rollback", summary["latest_rollback_at"])

    st.divider()

    st.subheader("Promoted Model Archives")

    if archive_df.empty:
        st.info("아직 promoted model archive 이력이 없습니다.")
        st.code("make model-archive", language="bash")
    else:
        st.dataframe(archive_df, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Rollback Plan Helper")

    if archive_df.empty:
        st.info("Rollback plan을 만들 archive가 없습니다.")
    else:
        selected_archive_index = st.selectbox(
            "Rollback 대상 archive 선택",
            options=archive_df.index.tolist(),
            format_func=lambda index: format_archive_option(archive_df.loc[index]),
            key="model_lifecycle_rollback_archive",
        )

        selected_archive = archive_df.loc[selected_archive_index]
        archive_id = int(selected_archive["id"])
        target_model_registry_id = selected_archive.get("model_registry_id")

        current_promoted_id = None

        if not current_model_df.empty:
            current_promoted_id = current_model_df.iloc[0].get("id")

        st.write("선택한 archive 기준 rollback plan입니다.")

        plan_rows = [
            {
                "item": "archive_id",
                "value": archive_id,
            },
            {
                "item": "target_model_registry_id",
                "value": target_model_registry_id,
            },
            {
                "item": "current_promoted_id",
                "value": current_promoted_id,
            },
            {
                "item": "archived_model_path",
                "value": selected_archive.get("archived_model_path"),
            },
            {
                "item": "target_accuracy",
                "value": selected_archive.get("accuracy"),
            },
            {
                "item": "target_f1_weighted",
                "value": selected_archive.get("f1_weighted"),
            },
        ]

        st.dataframe(pd.DataFrame(plan_rows), use_container_width=True, hide_index=True)

        if current_promoted_id == target_model_registry_id:
            st.info(
                "선택한 archive의 model_registry_id가 현재 PROMOTED 모델과 같습니다. "
                "현재 상태에서는 실제 rollback 의미가 크지 않습니다."
            )
        else:
            st.warning(
                "선택한 archive는 현재 PROMOTED 모델과 다릅니다. "
                "rollback 대상 후보로 사용할 수 있습니다."
            )

        st.caption("실제 rollback은 파일 복구와 DB 상태 변경이 포함되므로 CLI에서 명시적으로 실행합니다.")

        st.code(
            f"""MODEL_ROLLBACK_ARCHIVE_ID={archive_id} make model-rollback-plan

MODEL_ROLLBACK_ARCHIVE_ID={archive_id} make model-rollback

curl -X POST http://localhost:8000/reload-model
curl -fsS http://localhost:8000/model | jq
curl -fsS http://localhost:8000/ready | jq""",
            language="bash",
        )

    st.divider()

    st.subheader("Recent Rollback Actions")

    if rollback_df.empty:
        st.info("아직 rollback action 이력이 없습니다.")
    else:
        st.dataframe(rollback_df, use_container_width=True, hide_index=True)


def render_model_evaluation_section():
    st.subheader("Model Evaluation")

    st.caption(
        "Class-level model performance gate results based on MLflow evaluation metrics."
    )

    checks_df = fetch_latest_model_class_performance_checks()

    if checks_df.empty:
        st.info(
            "No MODEL_CLASS_PERFORMANCE check results found. "
            "Run `make model-class-performance-check` or execute the Airflow DAG after training."
        )
        return

    latest_checked_at = checks_df["checked_at"].max()
    latest_run_id = checks_df["run_id"].dropna().iloc[0] if checks_df["run_id"].notna().any() else "manual"

    total_checks = len(checks_df)
    failed_checks = int((checks_df["status"] == "FAIL").sum())
    passed_checks = int((checks_df["status"] == "PASS").sum())

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Latest check time", str(latest_checked_at))
    col2.metric("Run", str(latest_run_id))
    col3.metric("Passed checks", passed_checks)
    col4.metric("Failed checks", failed_checks)

    summary_df = build_class_performance_summary(checks_df)

    st.markdown("### Class-level performance summary")

    if summary_df.empty:
        st.warning("Class-level summary could not be built from the latest check results.")
    else:
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
        )

        if "overall_status" in summary_df.columns:
            status_counts = summary_df["overall_status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]

            st.markdown("### Class gate status distribution")
            st.bar_chart(
                status_counts,
                x="status",
                y="count",
                use_container_width=True,
            )

        if "f1" in summary_df.columns:
            st.markdown("### F1 score by class")
            f1_chart_df = summary_df[["label", "f1"]].dropna()
            st.bar_chart(
                f1_chart_df,
                x="label",
                y="f1",
                use_container_width=True,
            )

        if "recall" in summary_df.columns:
            st.markdown("### Recall by class")
            recall_chart_df = summary_df[["label", "recall"]].dropna()
            st.bar_chart(
                recall_chart_df,
                x="label",
                y="recall",
                use_container_width=True,
            )

    st.markdown("### Raw class performance check results")
    st.dataframe(
        checks_df,
        use_container_width=True,
        hide_index=True,
    )


def fetch_production_feedback_summary() -> pd.DataFrame:
    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            COUNT(*) AS feedback_total,
            COUNT(*) FILTER (
                WHERE pf.actual_category = mp.predicted_category
            ) AS correct_count,
            COUNT(*) FILTER (
                WHERE pf.actual_category <> mp.predicted_category
            ) AS incorrect_count,
            ROUND(
                AVG(
                    CASE
                        WHEN pf.actual_category = mp.predicted_category THEN 1.0
                        ELSE 0.0
                    END
                )::numeric,
                4
            ) AS accuracy
        FROM prediction_feedbacks pf
        JOIN model_predictions mp
            ON pf.prediction_id = mp.id
    """)


def fetch_latest_production_feedback_checks(limit: int = 20) -> pd.DataFrame:
    if not dashboard_table_exists("pipeline_check_results"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            check_name,
            status,
            ROUND(metric_value::numeric, 4) AS metric_value,
            ROUND(threshold_value::numeric, 4) AS threshold_value,
            message,
            checked_at
        FROM pipeline_check_results
        WHERE check_type = 'PRODUCTION_FEEDBACK'
        ORDER BY checked_at DESC, id DESC
        LIMIT :limit
    """, params={"limit": limit})


def fetch_production_feedback_evaluation_history(limit: int = 100) -> pd.DataFrame:
    if not dashboard_table_exists("pipeline_check_results"):
        return pd.DataFrame()

    return read_sql("""
        WITH normalized_checks AS (
            SELECT
                COALESCE(run_id, 'manual') AS run_id,
                date_trunc('second', checked_at) AS evaluated_at,
                check_name,
                status,
                metric_value,
                threshold_value
            FROM pipeline_check_results
            WHERE check_type = 'PRODUCTION_FEEDBACK'
              AND check_name IN (
                  'production_feedback_count',
                  'production_accuracy',
                  'production_f1_weighted'
              )
        )
        SELECT
            run_id,
            evaluated_at,
            ROUND(
                MAX(metric_value) FILTER (
                    WHERE check_name = 'production_feedback_count'
                )::numeric,
                4
            ) AS feedback_count,
            ROUND(
                MAX(metric_value) FILTER (
                    WHERE check_name = 'production_accuracy'
                )::numeric,
                4
            ) AS accuracy,
            ROUND(
                MAX(threshold_value) FILTER (
                    WHERE check_name = 'production_accuracy'
                )::numeric,
                4
            ) AS accuracy_threshold,
            ROUND(
                MAX(metric_value) FILTER (
                    WHERE check_name = 'production_f1_weighted'
                )::numeric,
                4
            ) AS f1_weighted,
            ROUND(
                MAX(threshold_value) FILTER (
                    WHERE check_name = 'production_f1_weighted'
                )::numeric,
                4
            ) AS f1_threshold,
            CASE
                WHEN COUNT(*) FILTER (WHERE status = 'FAIL') > 0 THEN 'FAIL'
                WHEN COUNT(*) FILTER (WHERE status = 'SKIPPED') > 0 THEN 'SKIPPED'
                WHEN COUNT(*) FILTER (WHERE status = 'PASS') > 0 THEN 'PASS'
                ELSE 'UNKNOWN'
            END AS overall_status
        FROM normalized_checks
        GROUP BY
            run_id,
            evaluated_at
        ORDER BY evaluated_at DESC
        LIMIT :limit
    """, params={"limit": limit})


def render_production_feedback_evaluation_history_section(
    history_df: pd.DataFrame,
) -> None:
    st.subheader("Production Feedback Evaluation History")

    st.caption(
        "production feedback 평가 결과가 시간에 따라 좋아지는지, "
        "나빠지는지 확인합니다. "
        "평가 단위는 pipeline_check_results의 PRODUCTION_FEEDBACK 결과입니다."
    )

    if history_df.empty:
        st.info("아직 production feedback 평가 이력이 없습니다.")
        st.code("make production-feedback-check", language="bash")
        return

    latest_row = history_df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Status", str(latest_row.get("overall_status") or "-"))
    col2.metric(
        "Latest Feedback Count",
        "-" if pd.isna(latest_row.get("feedback_count")) else int(latest_row.get("feedback_count")),
    )
    col3.metric(
        "Latest Accuracy",
        "-" if pd.isna(latest_row.get("accuracy")) else f"{float(latest_row.get('accuracy')):.4f}",
    )
    col4.metric(
        "Latest Weighted F1",
        "-" if pd.isna(latest_row.get("f1_weighted")) else f"{float(latest_row.get('f1_weighted')):.4f}",
    )

    chart_df = history_df.sort_values("evaluated_at")

    metric_chart_df = chart_df.melt(
        id_vars=["evaluated_at", "run_id"],
        value_vars=["accuracy", "f1_weighted"],
        var_name="metric",
        value_name="value",
    ).dropna(subset=["value"])

    if metric_chart_df.empty:
        st.info("accuracy 또는 weighted F1 trend를 표시할 데이터가 없습니다.")
    else:
        fig = px.line(
            metric_chart_df,
            x="evaluated_at",
            y="value",
            color="metric",
            markers=True,
            title="Production feedback quality trend",
        )
        st.plotly_chart(fig, use_container_width=True)

    count_chart_df = chart_df.dropna(subset=["feedback_count"])

    if not count_chart_df.empty:
        fig = px.bar(
            count_chart_df,
            x="evaluated_at",
            y="feedback_count",
            color="overall_status",
            text="feedback_count",
            title="Production feedback count by evaluation",
        )
        st.plotly_chart(fig, use_container_width=True)

    status_df = (
        history_df.groupby("overall_status")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    st.markdown("### Evaluation status distribution")
    st.dataframe(
        status_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Raw evaluation history")
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )


def build_production_feedback_retraining_decision(
    history_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    min_feedback_rows: int,
    min_accuracy: float,
    min_f1_weighted: float,
    trend_drop_threshold: float,
    min_history_points: int,
) -> dict[str, object]:
    if summary_df.empty:
        return {
            "candidate": False,
            "status": "UNKNOWN",
            "severity": "info",
            "reasons": ["production feedback summary를 조회할 수 없습니다."],
            "latest_feedback_count": 0,
            "latest_accuracy": 0.0,
            "latest_f1_weighted": 0.0,
            "accuracy_delta": 0.0,
            "f1_delta": 0.0,
        }

    summary = summary_df.iloc[0]
    latest_feedback_count = int(summary.get("feedback_total") or 0)
    latest_accuracy = float(summary.get("accuracy") or 0.0)

    latest_f1_weighted = 0.0
    latest_status = "UNKNOWN"
    accuracy_delta = 0.0
    f1_delta = 0.0
    reasons: list[str] = []

    if not history_df.empty:
        latest_history = history_df.iloc[0]
        latest_status = str(latest_history.get("overall_status") or "UNKNOWN")

        if not pd.isna(latest_history.get("f1_weighted")):
            latest_f1_weighted = float(latest_history.get("f1_weighted"))

        trend_df = history_df.sort_values("evaluated_at").dropna(
            subset=["accuracy", "f1_weighted"]
        )

        if len(trend_df) >= min_history_points:
            previous_row = trend_df.iloc[-min_history_points]
            current_row = trend_df.iloc[-1]

            accuracy_delta = float(current_row["accuracy"]) - float(previous_row["accuracy"])
            f1_delta = float(current_row["f1_weighted"]) - float(previous_row["f1_weighted"])

            if accuracy_delta <= -trend_drop_threshold:
                reasons.append(
                    "최근 평가 이력 기준 accuracy가 "
                    f"{abs(accuracy_delta):.4f} 이상 하락했습니다."
                )

            if f1_delta <= -trend_drop_threshold:
                reasons.append(
                    "최근 평가 이력 기준 weighted F1이 "
                    f"{abs(f1_delta):.4f} 이상 하락했습니다."
                )

    if latest_feedback_count < min_feedback_rows:
        return {
            "candidate": False,
            "status": "INSUFFICIENT_FEEDBACK",
            "severity": "info",
            "reasons": [
                "재학습 후보 판단에 필요한 feedback 수가 부족합니다. "
                f"현재 {latest_feedback_count}건, 기준 {min_feedback_rows}건입니다."
            ],
            "latest_feedback_count": latest_feedback_count,
            "latest_accuracy": latest_accuracy,
            "latest_f1_weighted": latest_f1_weighted,
            "accuracy_delta": accuracy_delta,
            "f1_delta": f1_delta,
        }

    if latest_accuracy < min_accuracy:
        reasons.append(
            f"production accuracy가 기준보다 낮습니다. "
            f"현재 {latest_accuracy:.4f}, 기준 {min_accuracy:.4f}입니다."
        )

    if latest_f1_weighted < min_f1_weighted:
        reasons.append(
            f"production weighted F1이 기준보다 낮습니다. "
            f"현재 {latest_f1_weighted:.4f}, 기준 {min_f1_weighted:.4f}입니다."
        )

    if latest_status == "FAIL":
        reasons.append("최신 PRODUCTION_FEEDBACK 평가 상태가 FAIL입니다.")

    candidate = bool(reasons)

    return {
        "candidate": candidate,
        "status": "RETRAINING_CANDIDATE" if candidate else "STABLE",
        "severity": "warning" if candidate else "success",
        "reasons": reasons or ["현재 기준에서는 재학습 후보로 판단되지 않습니다."],
        "latest_feedback_count": latest_feedback_count,
        "latest_accuracy": latest_accuracy,
        "latest_f1_weighted": latest_f1_weighted,
        "accuracy_delta": accuracy_delta,
        "f1_delta": f1_delta,
    }



def insert_retraining_candidate_check_result(
    conn,
    check_name: str,
    status: str,
    metric_value: float,
    threshold_value: float,
    message: str,
    run_id: str,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO pipeline_check_results (
                check_type,
                check_name,
                status,
                metric_value,
                threshold_value,
                message,
                dag_id,
                task_id,
                run_id,
                checked_at
            )
            VALUES (
                'RETRAINING_CANDIDATE',
                :check_name,
                :status,
                :metric_value,
                :threshold_value,
                :message,
                'dashboard',
                'save_retraining_candidate_decision',
                :run_id,
                NOW()
            )
            """
        ),
        {
            "check_name": check_name,
            "status": status,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "message": message,
            "run_id": run_id,
        },
    )


def save_retraining_candidate_decision(
    decision: dict[str, object],
    min_feedback_rows: int,
    min_accuracy: float,
    min_f1_weighted: float,
    trend_drop_threshold: float,
    min_history_points: int,
) -> str:
    engine = get_engine()
    run_id = f"dashboard_retraining__{datetime.now().strftime('%Y%m%dT%H%M%S')}"

    candidate = bool(decision.get("candidate"))
    decision_status = str(decision.get("status") or "UNKNOWN")
    latest_feedback_count = float(decision.get("latest_feedback_count") or 0.0)
    latest_accuracy = float(decision.get("latest_accuracy") or 0.0)
    latest_f1_weighted = float(decision.get("latest_f1_weighted") or 0.0)
    accuracy_delta = float(decision.get("accuracy_delta") or 0.0)
    f1_delta = float(decision.get("f1_delta") or 0.0)
    reasons = decision.get("reasons") or []
    reason_text = " | ".join(str(reason) for reason in reasons)

    if decision_status == "INSUFFICIENT_FEEDBACK":
        overall_status = "SKIPPED"
    elif candidate:
        overall_status = "FAIL"
    else:
        overall_status = "PASS"

    feedback_count_status = (
        "PASS" if latest_feedback_count >= float(min_feedback_rows) else "SKIPPED"
    )
    accuracy_status = "PASS" if latest_accuracy >= float(min_accuracy) else "FAIL"
    f1_status = "PASS" if latest_f1_weighted >= float(min_f1_weighted) else "FAIL"
    accuracy_trend_status = (
        "FAIL" if accuracy_delta <= -float(trend_drop_threshold) else "PASS"
    )
    f1_trend_status = (
        "FAIL" if f1_delta <= -float(trend_drop_threshold) else "PASS"
    )

    with engine.begin() as conn:
        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_candidate_flag",
            status=overall_status,
            metric_value=1.0 if candidate else 0.0,
            threshold_value=0.0,
            message=(
                f"decision={decision_status}, candidate={candidate}, "
                f"history_points={min_history_points}, reasons={reason_text}"
            ),
            run_id=run_id,
        )

        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_feedback_count",
            status=feedback_count_status,
            metric_value=latest_feedback_count,
            threshold_value=float(min_feedback_rows),
            message=(
                f"feedback_count={latest_feedback_count:.0f}, "
                f"required={min_feedback_rows}"
            ),
            run_id=run_id,
        )

        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_accuracy",
            status=accuracy_status,
            metric_value=latest_accuracy,
            threshold_value=float(min_accuracy),
            message=(
                f"production_accuracy={latest_accuracy:.4f}, "
                f"threshold={min_accuracy:.4f}"
            ),
            run_id=run_id,
        )

        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_f1_weighted",
            status=f1_status,
            metric_value=latest_f1_weighted,
            threshold_value=float(min_f1_weighted),
            message=(
                f"production_f1_weighted={latest_f1_weighted:.4f}, "
                f"threshold={min_f1_weighted:.4f}"
            ),
            run_id=run_id,
        )

        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_accuracy_delta",
            status=accuracy_trend_status,
            metric_value=accuracy_delta,
            threshold_value=-float(trend_drop_threshold),
            message=(
                f"accuracy_delta={accuracy_delta:.4f}, "
                f"drop_threshold=-{trend_drop_threshold:.4f}"
            ),
            run_id=run_id,
        )

        insert_retraining_candidate_check_result(
            conn=conn,
            check_name="retraining_f1_delta",
            status=f1_trend_status,
            metric_value=f1_delta,
            threshold_value=-float(trend_drop_threshold),
            message=(
                f"f1_delta={f1_delta:.4f}, "
                f"drop_threshold=-{trend_drop_threshold:.4f}"
            ),
            run_id=run_id,
        )

    return run_id


def fetch_latest_retraining_candidate_checks(limit: int = 30) -> pd.DataFrame:
    if not dashboard_table_exists("pipeline_check_results"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            check_name,
            status,
            ROUND(metric_value::numeric, 4) AS metric_value,
            ROUND(threshold_value::numeric, 4) AS threshold_value,
            message,
            run_id,
            checked_at
        FROM pipeline_check_results
        WHERE check_type = 'RETRAINING_CANDIDATE'
        ORDER BY checked_at DESC, id DESC
        LIMIT :limit
    """, params={"limit": limit})

def render_production_feedback_retraining_candidate_section(
    history_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    wrong_df: pd.DataFrame,
    confusion_df: pd.DataFrame,
) -> None:
    st.subheader("Retraining Candidate")

    st.caption(
        "production feedback 평가 결과와 평가 이력 추세를 기준으로 "
        "현재 모델을 재학습 후보로 볼지 판단합니다. "
        "이 기능은 자동 재학습을 실행하지 않고, 운영 판단 근거를 제공합니다."
    )

    with st.expander("판단 기준 설정", expanded=False):
        col1, col2, col3, col4, col5 = st.columns(5)

        min_feedback_rows = col1.number_input(
            "min feedback rows",
            key="retraining_candidate_min_feedback_rows",
            min_value=1,
            max_value=10000,
            value=get_dashboard_int_env("MIN_PRODUCTION_FEEDBACK_ROWS", 10),
            step=1,
        )

        min_accuracy = col2.number_input(
            "min accuracy",
            key="retraining_candidate_min_accuracy",
            min_value=0.0,
            max_value=1.0,
            value=get_dashboard_float_env("MIN_PRODUCTION_ACCURACY", 0.70),
            step=0.01,
            format="%.2f",
        )

        min_f1_weighted = col3.number_input(
            "min weighted F1",
            key="retraining_candidate_min_f1_weighted",
            min_value=0.0,
            max_value=1.0,
            value=get_dashboard_float_env("MIN_PRODUCTION_F1_WEIGHTED", 0.70),
            step=0.01,
            format="%.2f",
        )

        trend_drop_threshold = col4.number_input(
            "trend drop threshold",
            key="retraining_candidate_trend_drop_threshold",
            min_value=0.0,
            max_value=1.0,
            value=get_dashboard_float_env("PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD", 0.05),
            step=0.01,
            format="%.2f",
        )

        min_history_points = col5.number_input(
            "history points",
            key="retraining_candidate_min_history_points",
            min_value=2,
            max_value=20,
            value=get_dashboard_int_env("PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS", 3),
            step=1,
        )

    decision = build_production_feedback_retraining_decision(
        history_df=history_df,
        summary_df=summary_df,
        min_feedback_rows=int(min_feedback_rows),
        min_accuracy=float(min_accuracy),
        min_f1_weighted=float(min_f1_weighted),
        trend_drop_threshold=float(trend_drop_threshold),
        min_history_points=int(min_history_points),
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Decision", str(decision["status"]))
    col2.metric("Feedback", int(decision["latest_feedback_count"]))
    col3.metric("Accuracy", f"{float(decision['latest_accuracy']):.4f}")
    col4.metric("Weighted F1", f"{float(decision['latest_f1_weighted']):.4f}")
    col5.metric("F1 Delta", f"{float(decision['f1_delta']):.4f}")

    if decision["candidate"]:
        st.warning("현재 모델은 production feedback 기준 재학습 후보입니다.")
    elif decision["status"] == "INSUFFICIENT_FEEDBACK":
        st.info("아직 재학습 후보 판단에 필요한 feedback 수가 부족합니다.")
    else:
        st.success("현재 기준에서는 재학습 후보로 판단되지 않습니다.")

    st.markdown("### 판단 근거")
    for reason in decision["reasons"]:
        st.write(f"- {reason}")

    st.markdown("### 판단 결과 저장")
    st.caption(
        "현재 화면의 재학습 후보 판단 결과를 pipeline_check_results에 "
        "RETRAINING_CANDIDATE check_type으로 저장합니다."
    )

    if st.button(
        "Save retraining candidate decision",
        key="save_retraining_candidate_decision_button",
        type="primary",
    ):
        saved_run_id = save_retraining_candidate_decision(
            decision=decision,
            min_feedback_rows=int(min_feedback_rows),
            min_accuracy=float(min_accuracy),
            min_f1_weighted=float(min_f1_weighted),
            trend_drop_threshold=float(trend_drop_threshold),
            min_history_points=int(min_history_points),
        )
        st.success(f"Retraining candidate decision saved. run_id={saved_run_id}")

    latest_retraining_checks_df = fetch_latest_retraining_candidate_checks()

    if latest_retraining_checks_df.empty:
        st.info("아직 저장된 RETRAINING_CANDIDATE 판단 이력이 없습니다.")
    else:
        st.markdown("### 최근 저장된 재학습 후보 판단 이력")
        st.dataframe(
            latest_retraining_checks_df,
            use_container_width=True,
            hide_index=True,
        )

    if decision["candidate"]:
        st.markdown("### 권장 조치")
        st.write("1. 오분류가 특정 클래스에 집중되는지 확인합니다.")
        st.write("2. feedback_source가 sample 중심인지 실제 운영 feedback 중심인지 확인합니다.")
        st.write("3. 실제 운영 feedback 기준 저하라면 재학습 또는 rollback을 검토합니다.")

        st.code(
            """
make production-feedback-check
make dag-trigger
make model-lifecycle-check
""".strip(),
            language="bash",
        )

        st.markdown("### rollback 검토 명령어")
        st.code(
            """
make model-rollback-plan
MODEL_ROLLBACK_ARCHIVE_ID=<archive_id> make model-rollback
curl -X POST http://localhost:8000/reload-model
""".strip(),
            language="bash",
        )
    else:
        st.markdown("### 다음 확인")
        st.code(
            """
make production-feedback-check
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
""".strip(),
            language="bash",
        )

    if not wrong_df.empty:
        st.markdown("### 최근 오분류 샘플")
        st.dataframe(
            wrong_df.head(20),
            use_container_width=True,
            hide_index=True,
        )

    if not confusion_df.empty:
        st.markdown("### 오분류 집중도")
        wrong_confusion_df = confusion_df[
            confusion_df["actual_category"] != confusion_df["predicted_category"]
        ]

        if wrong_confusion_df.empty:
            st.success("confusion table 기준 오분류 집중 패턴이 없습니다.")
        else:
            st.dataframe(
                wrong_confusion_df.sort_values("count", ascending=False).head(20),
                use_container_width=True,
                hide_index=True,
            )


def fetch_recent_production_feedbacks(limit: int = 100) -> pd.DataFrame:
    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            pf.id AS feedback_id,
            pf.prediction_id,
            mp.predicted_category,
            pf.actual_category,
            CASE
                WHEN mp.predicted_category = pf.actual_category THEN 'CORRECT'
                ELSE 'WRONG'
            END AS result,
            ROUND(mp.confidence::numeric, 4) AS confidence,
            pf.feedback_source,
            pf.feedback_note,
            pf.created_by,
            pf.updated_at
        FROM prediction_feedbacks pf
        JOIN model_predictions mp
            ON pf.prediction_id = mp.id
        ORDER BY pf.updated_at DESC, pf.id DESC
        LIMIT :limit
    """, params={"limit": limit})


def fetch_wrong_production_feedbacks(limit: int = 100) -> pd.DataFrame:
    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            pf.prediction_id,
            mp.predicted_category,
            pf.actual_category,
            ROUND(mp.confidence::numeric, 4) AS confidence,
            pf.feedback_source,
            pf.feedback_note,
            pf.created_by,
            pf.updated_at
        FROM prediction_feedbacks pf
        JOIN model_predictions mp
            ON pf.prediction_id = mp.id
        WHERE mp.predicted_category <> pf.actual_category
        ORDER BY pf.updated_at DESC, pf.id DESC
        LIMIT :limit
    """, params={"limit": limit})


def fetch_production_feedback_confusion() -> pd.DataFrame:
    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            pf.actual_category,
            mp.predicted_category,
            COUNT(*) AS count
        FROM prediction_feedbacks pf
        JOIN model_predictions mp
            ON pf.prediction_id = mp.id
        GROUP BY
            pf.actual_category,
            mp.predicted_category
        ORDER BY pf.actual_category, count DESC
    """)


def fetch_production_feedback_sources() -> pd.DataFrame:
    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            feedback_source,
            created_by,
            COUNT(*) AS count
        FROM prediction_feedbacks
        GROUP BY
            feedback_source,
            created_by
        ORDER BY count DESC
    """)


PRODUCTION_FEEDBACK_LABELS = [
    "Data Engineer",
    "Backend Engineer",
    "ML Engineer",
    "DevOps Engineer",
    "Data Analyst",
    "Unknown",
]


def fetch_predictions_for_feedback(limit: int = 100) -> pd.DataFrame:
    if not dashboard_table_exists("model_predictions"):
        return pd.DataFrame()

    if not dashboard_table_exists("prediction_feedbacks"):
        return pd.DataFrame()

    return read_sql("""
        SELECT
            mp.id AS prediction_id,
            mp.prediction_source,
            mp.job_post_id,
            mp.predicted_category,
            ROUND(mp.confidence::numeric, 4) AS confidence,
            mp.confidence_level,
            mp.is_low_confidence,
            mp.model_name,
            mp.model_run_id,
            mp.model_registry_id,
            mp.predicted_at,
            pf.actual_category AS current_actual_category,
            pf.feedback_source AS current_feedback_source,
            pf.created_by AS current_feedback_created_by,
            pf.updated_at AS feedback_updated_at
        FROM model_predictions mp
        LEFT JOIN prediction_feedbacks pf
            ON pf.prediction_id = mp.id
        ORDER BY mp.id DESC
        LIMIT :limit
    """, params={"limit": limit})


def format_prediction_feedback_option(row: pd.Series) -> str:
    prediction_id = row.get("prediction_id")
    prediction_source = row.get("prediction_source") or "unknown"
    predicted_category = row.get("predicted_category") or "Unknown"
    confidence = row.get("confidence")
    current_actual_category = row.get("current_actual_category")

    if pd.isna(confidence):
        confidence_text = "-"
    else:
        confidence_text = str(confidence)

    if pd.isna(current_actual_category) or not current_actual_category:
        actual_text = "not_set"
    else:
        actual_text = str(current_actual_category)

    return (
        f"id={prediction_id} | "
        f"source={prediction_source} | "
        f"predicted={predicted_category} | "
        f"actual={actual_text} | "
        f"confidence={confidence_text}"
    )


def get_feedback_label_index(label: str | None) -> int:
    if label in PRODUCTION_FEEDBACK_LABELS:
        return PRODUCTION_FEEDBACK_LABELS.index(label)

    return PRODUCTION_FEEDBACK_LABELS.index("Unknown")


def upsert_prediction_feedback(
    prediction_id: int,
    actual_category: str,
    feedback_source: str,
    feedback_note: str | None,
    created_by: str,
) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO prediction_feedbacks (
                    prediction_id,
                    actual_category,
                    feedback_source,
                    feedback_note,
                    created_by,
                    created_at,
                    updated_at
                )
                VALUES (
                    :prediction_id,
                    :actual_category,
                    :feedback_source,
                    :feedback_note,
                    :created_by,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (prediction_id)
                DO UPDATE SET
                    actual_category = EXCLUDED.actual_category,
                    feedback_source = EXCLUDED.feedback_source,
                    feedback_note = EXCLUDED.feedback_note,
                    created_by = EXCLUDED.created_by,
                    updated_at = NOW()
                """
            ),
            {
                "prediction_id": prediction_id,
                "actual_category": actual_category,
                "feedback_source": feedback_source,
                "feedback_note": feedback_note,
                "created_by": created_by,
            },
        )


def get_dashboard_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    return int(raw_value)


def get_dashboard_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    return float(raw_value)


def calculate_weighted_f1_score(actual_values: list[str], predicted_values: list[str]) -> float:
    if not actual_values:
        return 0.0

    labels = sorted(set(actual_values) | set(predicted_values))
    total_support = len(actual_values)
    weighted_f1_sum = 0.0

    for label in labels:
        true_positive = sum(
            1
            for actual, predicted in zip(actual_values, predicted_values, strict=False)
            if actual == label and predicted == label
        )
        false_positive = sum(
            1
            for actual, predicted in zip(actual_values, predicted_values, strict=False)
            if actual != label and predicted == label
        )
        false_negative = sum(
            1
            for actual, predicted in zip(actual_values, predicted_values, strict=False)
            if actual == label and predicted != label
        )
        support = sum(1 for actual in actual_values if actual == label)

        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive > 0
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative > 0
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0.0
        )

        weighted_f1_sum += f1 * support

    return weighted_f1_sum / total_support


def insert_production_feedback_check_result(
    conn,
    check_name: str,
    status: str,
    metric_value: float,
    threshold_value: float,
    message: str,
    run_id: str,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO pipeline_check_results (
                check_type,
                check_name,
                status,
                metric_value,
                threshold_value,
                message,
                dag_id,
                task_id,
                run_id,
                checked_at
            )
            VALUES (
                'PRODUCTION_FEEDBACK',
                :check_name,
                :status,
                :metric_value,
                :threshold_value,
                :message,
                'dashboard',
                'run_production_feedback_evaluation',
                :run_id,
                NOW()
            )
            """
        ),
        {
            "check_name": check_name,
            "status": status,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "message": message,
            "run_id": run_id,
        },
    )


def run_production_feedback_evaluation_from_dashboard(
    min_feedback_rows: int,
    min_accuracy: float,
    min_f1_weighted: float,
    feedback_window_days: int,
) -> dict[str, object]:
    engine = get_engine()
    cutoff = datetime.now() - timedelta(days=feedback_window_days)
    run_id = f"dashboard__{datetime.now().strftime('%Y%m%dT%H%M%S')}"

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    pf.prediction_id,
                    pf.actual_category,
                    mp.predicted_category,
                    pf.updated_at
                FROM prediction_feedbacks pf
                JOIN model_predictions mp
                    ON pf.prediction_id = mp.id
                WHERE pf.updated_at >= :cutoff
                ORDER BY pf.updated_at DESC, pf.id DESC
                """
            ),
            {"cutoff": cutoff},
        ).mappings().all()

        feedback_count = len(rows)

        if feedback_count < min_feedback_rows:
            message = (
                "Production feedback row count is not enough for evaluation. "
                f"feedback_count={feedback_count}, "
                f"required={min_feedback_rows}, "
                f"window_days={feedback_window_days}"
            )

            insert_production_feedback_check_result(
                conn=conn,
                check_name="production_feedback_count",
                status="SKIPPED",
                metric_value=float(feedback_count),
                threshold_value=float(min_feedback_rows),
                message=message,
                run_id=run_id,
            )

            return {
                "overall_status": "SKIPPED",
                "run_id": run_id,
                "feedback_count": feedback_count,
                "min_feedback_rows": min_feedback_rows,
                "accuracy": None,
                "min_accuracy": min_accuracy,
                "f1_weighted": None,
                "min_f1_weighted": min_f1_weighted,
                "window_days": feedback_window_days,
                "message": message,
            }

        actual_values = [str(row["actual_category"]) for row in rows]
        predicted_values = [str(row["predicted_category"]) for row in rows]

        correct_count = sum(
            1
            for actual, predicted in zip(actual_values, predicted_values, strict=False)
            if actual == predicted
        )
        accuracy = correct_count / feedback_count
        f1_weighted = calculate_weighted_f1_score(actual_values, predicted_values)

        accuracy_status = "PASS" if accuracy >= min_accuracy else "FAIL"
        f1_status = "PASS" if f1_weighted >= min_f1_weighted else "FAIL"
        overall_status = (
            "PASS"
            if accuracy_status == "PASS" and f1_status == "PASS"
            else "FAIL"
        )

        insert_production_feedback_check_result(
            conn=conn,
            check_name="production_feedback_count",
            status="PASS",
            metric_value=float(feedback_count),
            threshold_value=float(min_feedback_rows),
            message=(
                "Production feedback row count is sufficient. "
                f"feedback_count={feedback_count}, required={min_feedback_rows}"
            ),
            run_id=run_id,
        )

        insert_production_feedback_check_result(
            conn=conn,
            check_name="production_accuracy",
            status=accuracy_status,
            metric_value=float(accuracy),
            threshold_value=float(min_accuracy),
            message=(
                f"Production feedback accuracy={accuracy:.4f}, "
                f"threshold={min_accuracy:.4f}, feedback_count={feedback_count}"
            ),
            run_id=run_id,
        )

        insert_production_feedback_check_result(
            conn=conn,
            check_name="production_f1_weighted",
            status=f1_status,
            metric_value=float(f1_weighted),
            threshold_value=float(min_f1_weighted),
            message=(
                f"Production feedback weighted_f1={f1_weighted:.4f}, "
                f"threshold={min_f1_weighted:.4f}, feedback_count={feedback_count}"
            ),
            run_id=run_id,
        )

    return {
        "overall_status": overall_status,
        "run_id": run_id,
        "feedback_count": feedback_count,
        "min_feedback_rows": min_feedback_rows,
        "accuracy": round(accuracy, 4),
        "min_accuracy": min_accuracy,
        "f1_weighted": round(f1_weighted, 4),
        "min_f1_weighted": min_f1_weighted,
        "window_days": feedback_window_days,
        "message": "Production feedback evaluation completed.",
    }


def render_production_feedback_evaluation_runner_section() -> None:
    st.subheader("Run Production Feedback Evaluation")

    st.caption(
        "Dashboard에서 현재 prediction feedback을 기준으로 production accuracy와 "
        "weighted F1을 계산하고 pipeline_check_results에 저장합니다. "
        "CLI의 `make production-feedback-check`와 같은 운영 확인 용도입니다."
    )

    default_min_feedback_rows = get_dashboard_int_env(
        "MIN_PRODUCTION_FEEDBACK_ROWS",
        10,
    )
    default_min_accuracy = get_dashboard_float_env(
        "MIN_PRODUCTION_ACCURACY",
        0.70,
    )
    default_min_f1_weighted = get_dashboard_float_env(
        "MIN_PRODUCTION_F1_WEIGHTED",
        0.70,
    )
    default_window_days = get_dashboard_int_env(
        "PRODUCTION_FEEDBACK_WINDOW_DAYS",
        30,
    )

    col1, col2, col3, col4 = st.columns(4)

    min_feedback_rows = col1.number_input(
        "min feedback rows",
        min_value=1,
        max_value=10000,
        value=default_min_feedback_rows,
        step=1,
    )
    min_accuracy = col2.number_input(
        "min accuracy",
        min_value=0.0,
        max_value=1.0,
        value=default_min_accuracy,
        step=0.01,
        format="%.2f",
    )
    min_f1_weighted = col3.number_input(
        "min weighted F1",
        min_value=0.0,
        max_value=1.0,
        value=default_min_f1_weighted,
        step=0.01,
        format="%.2f",
    )
    feedback_window_days = col4.number_input(
        "window days",
        min_value=1,
        max_value=365,
        value=default_window_days,
        step=1,
    )

    if "production_feedback_last_evaluation" in st.session_state:
        st.markdown("### Last dashboard evaluation result")
        st.json(st.session_state["production_feedback_last_evaluation"])

    if st.button(
        "Run production feedback evaluation",
        type="primary",
    ):
        try:
            result = run_production_feedback_evaluation_from_dashboard(
                min_feedback_rows=int(min_feedback_rows),
                min_accuracy=float(min_accuracy),
                min_f1_weighted=float(min_f1_weighted),
                feedback_window_days=int(feedback_window_days),
            )
        except Exception as exc:
            st.error(f"Production feedback evaluation failed: {exc}")
            return

        st.session_state["production_feedback_last_evaluation"] = result
        st.cache_data.clear()
        st.rerun()

    st.markdown("### CLI equivalent")
    st.code(
        "make production-feedback-check",
        language="bash",
    )


def render_production_feedback_input_section() -> None:
    st.subheader("Create or Update Prediction Feedback")

    st.caption(
        "최근 prediction을 선택한 뒤 실제 정답 label을 저장합니다. "
        "이미 feedback이 있는 prediction은 같은 prediction_id 기준으로 update됩니다."
    )

    candidate_df = fetch_predictions_for_feedback(limit=100)

    if candidate_df.empty:
        st.info("feedback을 입력할 prediction이 없습니다. 먼저 API sample 또는 batch inference를 실행하세요.")
        st.code("make api-sample", language="bash")
        return

    selected_index = st.selectbox(
        "Feedback 대상 prediction",
        options=candidate_df.index.tolist(),
        format_func=lambda index: format_prediction_feedback_option(
            candidate_df.loc[index]
        ),
        key="production_feedback_prediction_target",
    )

    selected_prediction = candidate_df.loc[selected_index]

    st.dataframe(
        pd.DataFrame([selected_prediction.to_dict()]),
        use_container_width=True,
        hide_index=True,
    )

    default_label = selected_prediction.get("current_actual_category")

    if pd.isna(default_label) or not default_label:
        default_label = selected_prediction.get("predicted_category")

    with st.form("production_feedback_input_form", clear_on_submit=False):
        actual_category = st.selectbox(
            "actual_category",
            options=PRODUCTION_FEEDBACK_LABELS,
            index=get_feedback_label_index(str(default_label)),
            help="운영 feedback 기준 실제 정답 label입니다.",
        )

        feedback_source = st.selectbox(
            "feedback_source",
            options=[
                "manual",
                "review",
                "ground_truth",
                "sample",
            ],
            index=0,
            help="manual/review는 사람이 검토한 feedback, sample은 테스트용 feedback입니다.",
        )

        created_by = st.text_input(
            "created_by",
            value=os.getenv("USER", "local-user"),
        )

        feedback_note = st.text_area(
            "feedback_note",
            placeholder=(
                "예: 실제로는 Data Engineer 공고인데 Backend Engineer로 예측됨. "
                "Kafka/Spark/ETL 키워드가 description에 포함되어 있음."
            ),
            height=120,
        )

        submitted = st.form_submit_button("Save production feedback")

        if submitted:
            upsert_prediction_feedback(
                prediction_id=int(selected_prediction["prediction_id"]),
                actual_category=actual_category,
                feedback_source=feedback_source,
                feedback_note=feedback_note.strip() or None,
                created_by=created_by.strip() or "local-user",
            )

            st.success(
                f"prediction_id={int(selected_prediction['prediction_id'])} feedback saved."
            )
            st.cache_data.clear()
            st.rerun()


def get_latest_production_feedback_metric(
    checks_df: pd.DataFrame,
    check_name: str,
    default: float = 0.0,
) -> float:
    if checks_df.empty:
        return default

    target_df = checks_df[checks_df["check_name"] == check_name]

    if target_df.empty:
        return default

    value = target_df.iloc[0]["metric_value"]

    if pd.isna(value):
        return default

    return float(value)


def get_latest_production_feedback_status(
    checks_df: pd.DataFrame,
    check_name: str,
    default: str = "UNKNOWN",
) -> str:
    if checks_df.empty:
        return default

    target_df = checks_df[checks_df["check_name"] == check_name]

    if target_df.empty:
        return default

    value = target_df.iloc[0]["status"]

    if pd.isna(value):
        return default

    return str(value)


def render_production_feedback_section() -> None:
    st.header("Production Feedback")

    st.caption(
        "운영 예측 결과에 연결된 feedback을 기준으로 모델의 production accuracy, "
        "weighted F1, 오분류, confusion table, feedback source 분포를 확인합니다."
    )

    if not dashboard_table_exists("prediction_feedbacks"):
        st.warning("prediction_feedbacks 테이블이 아직 생성되지 않았습니다.")

        st.code(
            """
make create-tables
make api-sample
make production-feedback-sample
make production-feedback-check
docker compose up -d --force-recreate dashboard
""".strip(),
            language="bash",
        )
        return

    summary_df = fetch_production_feedback_summary()
    checks_df = fetch_latest_production_feedback_checks()
    history_df = fetch_production_feedback_evaluation_history()
    recent_df = fetch_recent_production_feedbacks()
    wrong_df = fetch_wrong_production_feedbacks()
    confusion_df = fetch_production_feedback_confusion()
    source_df = fetch_production_feedback_sources()

    if summary_df.empty:
        st.info("Production feedback summary를 조회할 수 없습니다.")
        return

    summary = summary_df.iloc[0]

    feedback_total = int(summary.get("feedback_total") or 0)
    correct_count = int(summary.get("correct_count") or 0)
    incorrect_count = int(summary.get("incorrect_count") or 0)
    accuracy = float(summary.get("accuracy") or 0.0)

    latest_f1_weighted = get_latest_production_feedback_metric(
        checks_df,
        "production_f1_weighted",
        default=0.0,
    )
    latest_accuracy_status = get_latest_production_feedback_status(
        checks_df,
        "production_accuracy",
    )
    latest_f1_status = get_latest_production_feedback_status(
        checks_df,
        "production_f1_weighted",
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Feedback", f"{feedback_total:,}")
    col2.metric(
        "Production Accuracy",
        f"{accuracy:.4f}",
        help=f"Latest check status: {latest_accuracy_status}",
    )
    col3.metric(
        "Production Weighted F1",
        f"{latest_f1_weighted:.4f}",
        help=f"Latest check status: {latest_f1_status}",
    )
    col4.metric(
        "Incorrect Predictions",
        f"{incorrect_count:,}",
        delta=f"Correct {correct_count:,}",
    )

    if feedback_total == 0:
        st.info(
            "아직 feedback 데이터가 없습니다. "
            "Feedback Input 탭에서 직접 입력하거나 샘플 feedback을 생성하세요."
        )

        st.code(
            """
make api-sample
make production-feedback-sample
make production-feedback-check
docker compose up -d --force-recreate dashboard
""".strip(),
            language="bash",
        )

    st.divider()

    feedback_tab1, feedback_tab2, feedback_tab3, feedback_tab4, feedback_tab5, feedback_tab6, feedback_tab7, feedback_tab8, feedback_tab9 = st.tabs(
        [
            "Feedback Input",
            "Evaluation Runner",
            "Evaluation History",
            "Retraining Candidate",
            "Recent Feedback",
            "Wrong Predictions",
            "Confusion Table",
            "Feedback Source",
            "Evaluation Checks",
        ]
    )

    with feedback_tab1:
        render_production_feedback_input_section()

    with feedback_tab2:
        render_production_feedback_evaluation_runner_section()

    with feedback_tab3:
        render_production_feedback_evaluation_history_section(history_df)

    with feedback_tab4:
        render_production_feedback_retraining_candidate_section(
            history_df=history_df,
            summary_df=summary_df,
            wrong_df=wrong_df,
            confusion_df=confusion_df,
        )

    with feedback_tab5:
        st.subheader("Recent Production Feedback")

        if recent_df.empty:
            st.info("최근 feedback 데이터가 없습니다.")
        else:
            st.dataframe(
                recent_df,
                use_container_width=True,
                hide_index=True,
            )

    with feedback_tab6:
        st.subheader("Wrong Predictions")

        if wrong_df.empty:
            st.success("현재 feedback 기준 오분류가 없습니다.")
        else:
            st.dataframe(
                wrong_df,
                use_container_width=True,
                hide_index=True,
            )

    with feedback_tab7:
        st.subheader("Actual Category vs Predicted Category")

        if confusion_df.empty:
            st.info("Confusion table을 표시할 데이터가 없습니다.")
        else:
            confusion_pivot = confusion_df.pivot_table(
                index="actual_category",
                columns="predicted_category",
                values="count",
                aggfunc="sum",
                fill_value=0,
            )

            st.dataframe(
                confusion_pivot,
                use_container_width=True,
            )

            st.markdown("### Raw confusion rows")
            st.dataframe(
                confusion_df,
                use_container_width=True,
                hide_index=True,
            )

    with feedback_tab8:
        st.subheader("Feedback Source Distribution")

        if source_df.empty:
            st.info("feedback source 데이터가 없습니다.")
        else:
            source_summary_df = (
                source_df.groupby("feedback_source", as_index=False)["count"]
                .sum()
                .sort_values("count", ascending=False)
            )

            fig = px.bar(
                source_summary_df,
                x="feedback_source",
                y="count",
                text="count",
                title="Production feedback count by source",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                source_df,
                use_container_width=True,
                hide_index=True,
            )

    with feedback_tab9:
        st.subheader("Latest Production Feedback Evaluation Checks")

        if checks_df.empty:
            st.info("아직 PRODUCTION_FEEDBACK 평가 결과가 없습니다.")
            st.code("make production-feedback-check", language="bash")
        else:
            st.dataframe(
                checks_df,
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### 수동 확인 명령어")
        st.code(
            """
make production-feedback-check
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
""".strip(),
            language="bash",
        )


def main():
    st.set_page_config(
        page_title="JobSkill MLOps Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("JobSkill MLOps Dashboard")

    st.caption(
        "Airflow, MLflow, PostgreSQL, FastAPI 기반 채용공고 직무 분류 파이프라인 모니터링 대시보드"
    )

    render_metric_cards()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs(
        [
            "Model Lifecycle",
            "Model Evaluation",
            "Production Feedback",
            "Model Card",
            "Data Quality",
            "Prediction Quality",
            "Pipeline Checks",
            "API Logs",
            "Current Alerts",
            "Alert History",
            "Incident Report",
            "Recent Predictions",
        ]
    )

    with tab1:
        render_model_lifecycle_section()

    with tab2:
        render_model_evaluation_section()

    with tab3:
        render_production_feedback_section()

    with tab4:
        render_model_card_section()

    with tab5:
        render_source_quality()

    with tab6:
        render_prediction_quality()

    with tab7:
        render_pipeline_checks()

    with tab8:
        render_api_logs()

    with tab9:
        render_current_alerts_section()

    with tab10:
        render_alert_history_section()

    with tab11:
        render_incident_report_section()

    with tab12:
        render_recent_predictions()

if __name__ == "__main__":
    main()
