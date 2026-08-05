from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


REPORT_PATH = Path(
    os.getenv(
        "TRAINING_COST_REPORT_PATH",
        "reports/latest_training_cost_report.md",
    )
)


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
        lines.append(
            "| "
            + " | ".join(format_value(row.get(header)) for header in headers)
            + " |"
        )

    return "\n".join(lines)


def fetch_latest_training_cost_checks(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "pipeline_check_results"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT DISTINCT ON (check_name)
            check_name,
            status,
            metric_value,
            threshold_value,
            message,
            run_id,
            checked_at
        FROM pipeline_check_results
        WHERE check_type = 'TRAINING_COST'
        ORDER BY check_name, checked_at DESC
        """,
    )


def fetch_training_cost_history(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "pipeline_check_results"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT
            checked_at,
            MAX(CASE WHEN check_name = 'training_duration_seconds'
                THEN metric_value END) AS training_duration_seconds,
            MAX(CASE WHEN check_name = 'training_rows'
                THEN metric_value END) AS training_rows,
            MAX(CASE WHEN check_name = 'training_throughput_rows_per_second'
                THEN metric_value END) AS training_throughput_rows_per_second,
            MAX(CASE WHEN check_name = 'model_size_bytes'
                THEN metric_value END) AS model_size_bytes,
            MAX(run_id) AS run_id
        FROM pipeline_check_results
        WHERE check_type = 'TRAINING_COST'
        GROUP BY checked_at
        ORDER BY checked_at DESC
        LIMIT 20
        """,
    )


def fetch_retraining_strategy_latest(engine: Engine) -> list[dict[str, Any]]:
    if not table_exists(engine, "pipeline_check_results"):
        return []

    return fetch_rows(
        engine,
        """
        SELECT DISTINCT ON (check_name)
            check_name,
            status,
            metric_value,
            threshold_value,
            message,
            checked_at
        FROM pipeline_check_results
        WHERE check_type = 'RETRAINING_STRATEGY'
          AND check_name IN (
              'full_retrain_row_policy',
              'window_retrain_policy',
              'sampling_retrain_recommended',
              'incremental_experiment_recommended'
          )
        ORDER BY check_name, checked_at DESC
        """,
    )


def build_recommendation(latest_checks: list[dict[str, Any]]) -> str:
    by_name = {row["check_name"]: row for row in latest_checks}

    duration_row = by_name.get("training_duration_seconds")
    rows_row = by_name.get("training_rows")
    incremental_row = by_name.get("incremental_experiment_by_duration")

    lines = []

    if duration_row is None:
        lines.append("- 아직 TRAINING_COST 기록이 없습니다. 먼저 baseline training을 1회 실행하세요.")
        return "\n".join(lines)

    duration = float(duration_row.get("metric_value") or 0)
    threshold = float(duration_row.get("threshold_value") or 0)
    training_rows = float(rows_row.get("metric_value") or 0) if rows_row else 0

    if duration_row.get("status") == "PASS":
        lines.append(
            f"- 현재 full retrain 시간은 {duration:.2f}s로 기준 {threshold:.2f}s 이하입니다. "
            "현재 단계에서는 full retrain을 유지하는 것이 가장 안전합니다."
        )
    else:
        lines.append(
            f"- full retrain 시간이 {duration:.2f}s로 기준 {threshold:.2f}s를 초과했습니다. "
            "window retrain 또는 sampling retrain 검토가 필요합니다."
        )

    lines.append(f"- 마지막 학습 row 수는 {training_rows:.0f}건입니다.")

    if incremental_row and incremental_row.get("status") == "WARN":
        lines.append("- 학습 시간이 incremental shadow experiment 기준에 도달했습니다.")
    else:
        lines.append("- incremental retraining은 아직 shadow experiment 후보로만 유지합니다.")

    return "\n".join(lines)


def build_report() -> str:
    engine = get_engine()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    latest_checks = fetch_latest_training_cost_checks(engine)
    history = fetch_training_cost_history(engine)
    retraining_strategy = fetch_retraining_strategy_latest(engine)

    lines = [
        "# JobSkill Training Cost Report",
        "",
        f"- Generated at: `{generated_at}`",
        "",
        "## Summary Recommendation",
        "",
        build_recommendation(latest_checks),
        "",
        "## Latest Training Cost Checks",
        "",
        markdown_table(
            [
                "check_name",
                "status",
                "metric_value",
                "threshold_value",
                "message",
                "run_id",
                "checked_at",
            ],
            latest_checks,
        ),
        "",
        "## Training Cost History",
        "",
        markdown_table(
            [
                "checked_at",
                "training_duration_seconds",
                "training_rows",
                "training_throughput_rows_per_second",
                "model_size_bytes",
                "run_id",
            ],
            history,
        ),
        "",
        "## Related Retraining Strategy Signals",
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
            retraining_strategy,
        ),
        "",
        "## Follow-up Commands",
        "",
        "```bash",
        "make retraining-strategy-check",
        "make training-cost-report",
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

    print("Training cost report generated")
    print(f"path={REPORT_PATH}")


if __name__ == "__main__":
    main()

