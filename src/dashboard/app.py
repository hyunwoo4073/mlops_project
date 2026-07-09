import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text



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
        """
    )

    count_map = dict(zip(counts_df["table_name"], counts_df["row_count"]))

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Raw jobs", int(count_map.get("raw_job_posts", 0)))
    col2.metric("Cleaned jobs", int(count_map.get("cleaned_job_posts", 0)))
    col3.metric("Predictions", int(count_map.get("model_predictions", 0)))
    col4.metric("API logs", int(count_map.get("api_prediction_logs", 0)))


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


def fetch_recent_firing_alerts() -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        SELECT
            alert_name,
            severity,
            service,
            summary,
            created_at
        FROM alert_events
        WHERE status = 'firing'
        ORDER BY id DESC
        LIMIT 10
        """
    )

    with engine.begin() as conn:
        return pd.read_sql(query, conn)

def render_alert_history_section() -> None:
    st.header("Alert History")

    alert_summary_df = fetch_alert_summary()
    recent_alerts_df = fetch_recent_alert_events()
    status_counts_df = fetch_alert_status_counts()
    severity_counts_df = fetch_alert_severity_counts()
    recent_firing_df = fetch_recent_firing_alerts()

    if alert_summary_df.empty:
        st.info("No alert events found.")
        return

    total_alert_count = int(alert_summary_df["alert_count"].sum())
    firing_count = int(
        alert_summary_df.loc[
            alert_summary_df["status"].str.lower() == "firing",
            "alert_count",
        ].sum()
    )
    resolved_count = int(
        alert_summary_df.loc[
            alert_summary_df["status"].str.lower() == "resolved",
            "alert_count",
        ].sum()
    )
    latest_created_at = alert_summary_df["latest_created_at"].max()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Alert Events", total_alert_count)
    col2.metric("Firing Events", firing_count)
    col3.metric("Resolved Events", resolved_count)
    col4.metric("Latest Alert Event", str(latest_created_at))

    st.subheader("Alert Status Distribution")

    if not status_counts_df.empty:
        fig = px.bar(
            status_counts_df,
            x="status",
            y="count",
            text="count",
            title="Alert Events by Status",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Alert Severity Distribution")

    if not severity_counts_df.empty:
        fig = px.bar(
            severity_counts_df,
            x="severity",
            y="count",
            text="count",
            title="Alert Events by Severity",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Firing Alerts")

    if recent_firing_df.empty:
        st.success("No recent firing alerts.")
    else:
        st.dataframe(
            recent_firing_df,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Alert Summary")

    st.dataframe(
        alert_summary_df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Recent Alert Events")

    st.dataframe(
        recent_alerts_df,
        use_container_width=True,
        hide_index=True,
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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Model",
            "Data Quality",
            "Prediction Quality",
            "Pipeline Checks",
            "API Logs",
            "Alert History",
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
        render_alert_history_section()

    with tab7:
        render_recent_predictions()


if __name__ == "__main__":
    main()
