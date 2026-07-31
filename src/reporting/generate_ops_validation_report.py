from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


REPORT_PATH = Path(os.getenv("OPS_VALIDATION_REPORT_PATH", "reports/latest_ops_validation_report.md"))


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def get_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
    )


def fetch_rows(
    engine: Engine,
    query: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    with engine.begin() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def fetch_scalar(
    engine: Engine,
    query: str,
    params: dict[str, Any] | None = None,
) -> Any:
    with engine.begin() as conn:
        return conn.execute(text(query), params or {}).scalar()


def table_exists(engine: Engine, table_name: str) -> bool:
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
    """
    return bool(fetch_scalar(engine, query, {"table_name": table_name}))


def get_table_columns(engine: Engine, table_name: str) -> set[str]:
    if not table_exists(engine, table_name):
        return set()

    rows = fetch_rows(
        engine,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
        ORDER BY ordinal_position
        """,
        {"table_name": table_name},
    )

    return {str(row["column_name"]) for row in rows}


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def first_existing_column(columns: set[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def select_alias(
    columns: set[str],
    candidates: list[str],
    alias: str,
    default_sql: str = "NULL",
) -> str:
    column_name = first_existing_column(columns, candidates)

    if column_name is None:
        return f"{default_sql} AS {quote_ident(alias)}"

    return f"{quote_ident(column_name)} AS {quote_ident(alias)}"


def safe_count(engine: Engine, table_name: str) -> int | None:
    if not table_exists(engine, table_name):
        return None

    return int(fetch_scalar(engine, f"SELECT COUNT(*) FROM {quote_ident(table_name)}"))


def format_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value).replace("|", "\\|")


def markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows._"

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        values = [format_value(row.get(header)) for header in headers]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def fetch_latest_checks(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "pipeline_check_results"):
        return []

    return fetch_rows(
        engine,
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
        ORDER BY checked_at DESC
        LIMIT 20
        """,
    )


def fetch_check_type_rows(engine: Engine, check_type: str) -> list[dict[str, Any]]:
    if not table_exists(engine, "pipeline_check_results"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT
            check_name,
            status,
            metric_value,
            threshold_value,
            message,
            checked_at
        FROM pipeline_check_results
        WHERE check_type = :check_type
        ORDER BY checked_at DESC
        LIMIT 10
        """,
        {"check_type": check_type},
    )


def fetch_current_alerts(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "alert_current_states"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT
            alert_name,
            service,
            severity,
            status,
            starts_at,
            last_received_at
        FROM alert_current_states
        WHERE status = 'firing'
        ORDER BY starts_at ASC
        LIMIT 20
        """,
    )


def fetch_synthetic_alerts(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "alert_current_states"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT
            alert_name,
            service,
            severity,
            status,
            starts_at,
            last_received_at,
            fingerprint
        FROM alert_current_states
        WHERE service IN ('smoke-test', 'incident-drill')
           OR alert_name ILIKE '%smoke%'
           OR alert_name ILIKE '%drill%'
        ORDER BY last_received_at DESC NULLS LAST
        LIMIT 20
        """,
    )


def fetch_promoted_models(engine: Engine) -> list[dict[str, Any]]:
    columns = get_table_columns(engine, "model_registry")

    if not columns:
        return []

    select_parts = [
        select_alias(columns, ["id"], "id"),
        select_alias(columns, ["model_name", "name"], "model_name"),
        select_alias(
            columns,
            [
                "model_version",
                "version",
                "model_run_id",
                "run_id",
                "mlflow_run_id",
            ],
            "model_version",
        ),
        select_alias(columns, ["status", "model_status"], "status"),
        select_alias(
            columns,
            [
                "accuracy",
                "test_accuracy",
                "metric_accuracy",
                "model_accuracy",
            ],
            "accuracy",
        ),
        select_alias(
            columns,
            [
                "f1_weighted",
                "weighted_f1",
                "f1_score",
                "metric_f1_weighted",
                "model_f1_weighted",
            ],
            "f1_weighted",
        ),
        select_alias(
            columns,
            [
                "promoted_at",
                "created_at",
                "registered_at",
                "updated_at",
            ],
            "promoted_at",
        ),
    ]

    order_column = first_existing_column(
        columns,
        ["promoted_at", "created_at", "registered_at", "updated_at", "id"],
    )
    order_sql = f"ORDER BY {quote_ident(order_column)} DESC NULLS LAST" if order_column else ""

    if "id" in columns and order_column != "id":
        order_sql = f"{order_sql}, id DESC" if order_sql else "ORDER BY id DESC"

    query = f"""
        SELECT
            {",\n            ".join(select_parts)}
        FROM model_registry
        {order_sql}
        LIMIT 5
    """

    return fetch_rows(engine, query)


def build_report() -> str:
    engine = get_engine()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    core_tables = [
        "raw_job_posts",
        "cleaned_job_posts",
        "job_post_skills",
        "model_predictions",
        "prediction_feedbacks",
        "api_prediction_logs",
        "pipeline_check_results",
        "model_registry",
        "alert_events",
        "alert_current_states",
    ]

    table_rows = []
    for table_name in core_tables:
        count = safe_count(engine, table_name)
        table_rows.append(
            {
                "table_name": table_name,
                "row_count": "MISSING" if count is None else count,
            }
        )

    latest_checks = fetch_latest_checks(engine)
    production_feedback_checks = fetch_check_type_rows(engine, "PRODUCTION_FEEDBACK")
    retraining_checks = fetch_check_type_rows(engine, "RETRAINING_CANDIDATE")
    current_alerts = fetch_current_alerts(engine)
    synthetic_alerts = fetch_synthetic_alerts(engine)
    promoted_models = fetch_promoted_models(engine)

    lines = [
        "# JobSkill MLOps Ops Validation Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- API URL: `{os.getenv('API_URL', 'http://localhost:8000')}`",
        f"- Prometheus URL: `{os.getenv('PROMETHEUS_URL', 'http://localhost:9090')}`",
        f"- Alertmanager URL: `{os.getenv('ALERTMANAGER_URL', 'http://localhost:9093')}`",
        f"- Dashboard URL: `{os.getenv('DASHBOARD_URL', 'http://localhost:8501')}`",
        "",
        "## Summary",
        "",
        "This report captures the current local operations state after validation checks. "
        "It is intended to support portfolio review, troubleshooting, and regression tracking.",
        "",
        "## Core Table Row Counts",
        "",
        markdown_table(["table_name", "row_count"], table_rows),
        "",
        "## Latest Pipeline Check Results",
        "",
        markdown_table(
            [
                "check_type",
                "check_name",
                "status",
                "metric_value",
                "threshold_value",
                "message",
                "checked_at",
            ],
            latest_checks,
        ),
        "",
        "## Production Feedback Checks",
        "",
        markdown_table(
            [
                "check_name",
                "status",
                "metric_value",
                "threshold_value",
                "message",
                "checked_at",
            ],
            production_feedback_checks,
        ),
        "",
        "## Retraining Candidate Checks",
        "",
        markdown_table(
            [
                "check_name",
                "status",
                "metric_value",
                "threshold_value",
                "message",
                "checked_at",
            ],
            retraining_checks,
        ),
        "",
        "## Current Firing Alerts",
        "",
        markdown_table(
            [
                "alert_name",
                "service",
                "severity",
                "status",
                "starts_at",
                "last_received_at",
            ],
            current_alerts,
        ),
        "",
        "## Synthetic Alert Residue",
        "",
        markdown_table(
            [
                "alert_name",
                "service",
                "severity",
                "status",
                "starts_at",
                "last_received_at",
                "fingerprint",
            ],
            synthetic_alerts,
        ),
        "",
        "## Recent Model Registry Records",
        "",
        markdown_table(
            [
                "id",
                "model_name",
                "model_version",
                "status",
                "accuracy",
                "f1_weighted",
                "promoted_at",
            ],
            promoted_models,
        ),
        "",
        "## Recommended Follow-up Commands",
        "",
        "```bash",
        "make ops-static-check",
        "make smoke",
        "make synthetic-alert-check",
        "make ops-check",
        "```",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("Ops validation report generated")
    print(f"path={REPORT_PATH}")


if __name__ == "__main__":
    main()
