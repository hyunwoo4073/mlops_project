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


def save_alert_silence_action(
    silence_id: str,
    alert: pd.Series,
    duration_minutes: int,
    created_by: str,
    reason: str,
) -> None:
    engine = get_engine()

    now = datetime.now(timezone.utc)
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
                "fingerprint": alert.get("fingerprint"),
                "alert_name": alert.get("alert_name"),
                "severity": alert.get("severity"),
                "service": alert.get("service"),
                "instance": alert.get("instance"),
                "duration_minutes": duration_minutes,
                "starts_at": now.replace(tzinfo=None),
                "ends_at": ends_at.replace(tzinfo=None),
                "created_by": created_by,
                "reason": reason,
            },
        )


def fetch_recent_alert_silence_actions(limit: int = 30) -> pd.DataFrame:
    return read_sql(
        """
        SELECT
            id,
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
                )

                st.success(f"Alertmanager silence created: {silence_id}")
                st.rerun()

            except requests.RequestException as exc:
                st.error(f"Alertmanager silence 생성 실패: {exc}")


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

    st.subheader("Active Alertmanager Silences")

    silences_df = fetch_alertmanager_silences()

    if silences_df.empty:
        st.info("No Alertmanager silence found.")
    else:
        st.dataframe(
            silences_df,
            use_container_width=True,
            hide_index=True,
        )

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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
        [
            "Model",
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
        render_latest_model()

    with tab2:
        render_source_quality()

    with tab3:
        render_prediction_quality()

    with tab4:
        render_pipeline_checks()

    with tab5:
        render_api_logs()

    with tab6:
        render_current_alerts_section()

    with tab7:
        render_alert_history_section()

    with tab8:
        render_recent_predictions()

    with tab9:
        render_recent_predictions()

if __name__ == "__main__":
    main()
