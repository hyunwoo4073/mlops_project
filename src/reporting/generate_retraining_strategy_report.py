from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


REPORT_PATH = Path(
    os.getenv(
        "RETRAINING_STRATEGY_REPORT_PATH",
        "reports/latest_retraining_strategy_report.md",
    )
)


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True, pool_recycle=1800, pool_timeout=30)


def fetch_rows(engine: Engine, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.begin() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def fetch_scalar(engine: Engine, query: str, params: dict[str, Any] | None = None) -> Any:
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


def fetch_strategy_checks(engine: Engine) -> list[dict[str, Any]]:
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
        WHERE check_type = 'RETRAINING_STRATEGY'
        ORDER BY checked_at DESC, check_name ASC
        LIMIT 30
        """,
    )


def fetch_latest_strategy_decisions(strategy_checks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for row in strategy_checks:
        check_name = str(row["check_name"])
        if check_name not in decisions:
            decisions[check_name] = row
    return decisions


def fetch_category_distribution(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "cleaned_job_posts"):
        return []
    columns = get_table_columns(engine, "cleaned_job_posts")
    category_column = first_existing_column(columns, ["category", "job_category", "label", "target_category"])
    if category_column is None:
        return []
    category_sql = quote_ident(category_column)
    query = f"""
        SELECT
            {category_sql} AS category,
            COUNT(*) AS row_count
        FROM cleaned_job_posts
        WHERE {category_sql} IS NULL
           OR {category_sql} NOT IN ('Unknown', 'UNKNOWN', 'unknown')
        GROUP BY {category_sql}
        ORDER BY row_count DESC, category ASC
    """
    return fetch_rows(engine, query)


def fetch_source_distribution(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "cleaned_job_posts"):
        return []
    columns = get_table_columns(engine, "cleaned_job_posts")
    source_column = first_existing_column(columns, ["source", "data_source", "source_type", "ingest_source"])
    if source_column is None:
        return []
    source_sql = quote_ident(source_column)
    query = f"""
        SELECT
            {source_sql} AS source,
            COUNT(*) AS row_count
        FROM cleaned_job_posts
        GROUP BY {source_sql}
        ORDER BY row_count DESC, source ASC
    """
    return fetch_rows(engine, query)


def fetch_table_profile(engine: Engine) -> list[dict[str, Any]]:
    tables = ["cleaned_job_posts", "prediction_feedbacks", "pipeline_check_results", "model_registry"]
    rows = []
    for table_name in tables:
        if not table_exists(engine, table_name):
            rows.append({"table_name": table_name, "row_count": "MISSING"})
            continue
        count = fetch_scalar(engine, f"SELECT COUNT(*) FROM {quote_ident(table_name)}")
        rows.append({"table_name": table_name, "row_count": int(count)})
    return rows


def yes_no_from_decision(decisions: dict[str, dict[str, Any]], check_name: str) -> str:
    row = decisions.get(check_name)
    if row is None:
        return "UNKNOWN"
    metric_value = row.get("metric_value")
    if metric_value is None:
        return "UNKNOWN"
    return "YES" if float(metric_value) >= 1.0 else "NO"


def build_recommendation(decisions: dict[str, dict[str, Any]]) -> str:
    full_retrain_status = decisions.get("full_retrain_row_policy", {}).get("status")
    window_retrain = yes_no_from_decision(decisions, "window_retrain_policy")
    sampling_retrain = yes_no_from_decision(decisions, "sampling_retrain_recommended")
    incremental_experiment = yes_no_from_decision(decisions, "incremental_experiment_recommended")

    lines = []
    if full_retrain_status == "PASS":
        lines.append("- 현재 row 수 기준으로는 full retrain을 유지하는 것이 가장 단순하고 안전합니다.")
    elif full_retrain_status == "WARN":
        lines.append("- 전체 학습 row 수가 기준을 초과했으므로 full retrain 비용 증가를 주의해야 합니다.")
    else:
        lines.append("- full retrain 정책 판단 결과가 아직 충분하지 않습니다.")

    if window_retrain == "YES":
        lines.append("- 최근 window 데이터가 충분하므로 window retrain 실험이 가능합니다.")
    else:
        lines.append("- 최근 window만으로는 class coverage가 부족할 수 있어 full retrain을 우선 유지합니다.")

    if sampling_retrain == "YES":
        lines.append("- 최근 데이터 전체와 과거 class-balanced sample을 섞는 sampling retrain을 검토합니다.")

    if incremental_experiment == "YES":
        lines.append("- 데이터 규모 기준상 incremental retraining shadow experiment를 검토할 단계입니다.")
    else:
        lines.append("- incremental retraining은 아직 운영 모델이 아니라 향후 shadow experiment 후보로 둡니다.")

    return "\n".join(lines)


def build_report() -> str:
    engine = get_engine()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strategy_checks = fetch_strategy_checks(engine)
    decisions = fetch_latest_strategy_decisions(strategy_checks)
    table_profile = fetch_table_profile(engine)
    category_distribution = fetch_category_distribution(engine)
    source_distribution = fetch_source_distribution(engine)

    full_retrain_allowed = "YES" if decisions.get("full_retrain_row_policy", {}).get("status") == "PASS" else "WARN/NO"
    window_retrain_allowed = yes_no_from_decision(decisions, "window_retrain_policy")
    sampling_recommended = yes_no_from_decision(decisions, "sampling_retrain_recommended")
    incremental_recommended = yes_no_from_decision(decisions, "incremental_experiment_recommended")

    lines = [
        "# JobSkill Retraining Strategy Report",
        "",
        f"- Generated at: `{generated_at}`",
        "",
        "## Summary",
        "",
        f"- Full retrain allowed: `{full_retrain_allowed}`",
        f"- Window retrain allowed: `{window_retrain_allowed}`",
        f"- Sampling retrain recommended: `{sampling_recommended}`",
        f"- Incremental experiment recommended: `{incremental_recommended}`",
        "",
        "## Recommendation",
        "",
        build_recommendation(decisions),
        "",
        "## Latest Retraining Strategy Checks",
        "",
        markdown_table(
            ["check_name", "status", "metric_value", "threshold_value", "message", "checked_at"],
            strategy_checks,
        ),
        "",
        "## Table Profile",
        "",
        markdown_table(["table_name", "row_count"], table_profile),
        "",
        "## Category Distribution",
        "",
        markdown_table(["category", "row_count"], category_distribution),
        "",
        "## Source Distribution",
        "",
        markdown_table(["source", "row_count"], source_distribution),
        "",
        "## Follow-up Commands",
        "",
        "```bash",
        "make retraining-strategy-check",
        "make retraining-strategy-report",
        "make ops-report",
        "make ops-evidence-bundle",
        "make ops-evidence-check",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("Retraining strategy report generated")
    print(f"path={REPORT_PATH}")


if __name__ == "__main__":
    main()

