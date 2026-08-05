from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


CHECK_TYPE = "RETRAINING_STRATEGY"
DAG_ID = "manual"
TASK_ID = "check_retraining_strategy"
RUN_ID = "manual_retraining_strategy_check"


@dataclass(frozen=True)
class StrategyConfig:
    lookback_days: int
    recent_days: int
    max_full_retrain_rows: int
    min_window_rows: int
    min_rows_per_class: int
    feedback_required: bool
    feedback_lookback_days: int
    incremental_experiment_row_threshold: int


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    status: str
    metric_value: float | None
    threshold_value: float | None
    message: str


def getenv_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. value={raw_value}") from exc


def getenv_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config() -> StrategyConfig:
    return StrategyConfig(
        lookback_days=getenv_int("RETRAINING_LOOKBACK_DAYS", 180),
        recent_days=getenv_int("RETRAINING_RECENT_DAYS", 90),
        max_full_retrain_rows=getenv_int("RETRAINING_MAX_FULL_RETRAIN_ROWS", 100_000),
        min_window_rows=getenv_int("RETRAINING_MIN_WINDOW_ROWS", 1_000),
        min_rows_per_class=getenv_int("RETRAINING_MIN_ROWS_PER_CLASS", 100),
        feedback_required=getenv_bool("RETRAINING_FEEDBACK_REQUIRED", False),
        feedback_lookback_days=getenv_int("RETRAINING_FEEDBACK_LOOKBACK_DAYS", 90),
        incremental_experiment_row_threshold=getenv_int(
            "RETRAINING_INCREMENTAL_EXPERIMENT_ROW_THRESHOLD",
            500_000,
        ),
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


def build_training_where_clause(
    category_column: str | None,
    date_column: str | None,
    days: int | None,
) -> tuple[str, dict[str, Any]]:
    conditions = []
    params: dict[str, Any] = {}

    if category_column is not None:
        category_sql = quote_ident(category_column)
        conditions.append(
            f"({category_sql} IS NULL OR {category_sql} NOT IN "
            "('Unknown', 'UNKNOWN', 'unknown'))"
        )

    if date_column is not None and days is not None and days > 0:
        date_sql = quote_ident(date_column)
        conditions.append(f"{date_sql} >= NOW() - (:days * INTERVAL '1 day')")
        params["days"] = days

    if not conditions:
        return "", params
    return "WHERE " + " AND ".join(conditions), params


def count_rows(
    engine: Engine,
    table_name: str,
    where_clause: str = "",
    params: dict[str, Any] | None = None,
) -> int:
    query = f"SELECT COUNT(*) FROM {quote_ident(table_name)} {where_clause}"
    return int(fetch_scalar(engine, query, params or {}))


def get_category_counts(
    engine: Engine,
    table_name: str,
    category_column: str | None,
    date_column: str | None,
    days: int | None,
) -> list[dict[str, Any]]:
    if category_column is None:
        return []

    where_clause, params = build_training_where_clause(
        category_column=category_column,
        date_column=date_column,
        days=days,
    )
    category_sql = quote_ident(category_column)
    query = f"""
        SELECT
            {category_sql} AS category,
            COUNT(*) AS row_count
        FROM {quote_ident(table_name)}
        {where_clause}
        GROUP BY {category_sql}
        ORDER BY row_count DESC, category ASC
    """
    return fetch_rows(engine, query, params)


def count_feedback_rows(engine: Engine, config: StrategyConfig) -> int:
    if not table_exists(engine, "prediction_feedbacks"):
        return 0

    columns = get_table_columns(engine, "prediction_feedbacks")
    created_column = first_existing_column(columns, ["created_at", "feedback_at", "updated_at"])

    if created_column is None:
        return count_rows(engine, "prediction_feedbacks")

    where_clause = f"WHERE {quote_ident(created_column)} >= NOW() - (:days * INTERVAL '1 day')"
    return count_rows(engine, "prediction_feedbacks", where_clause, {"days": config.feedback_lookback_days})


def get_training_profile(engine: Engine, config: StrategyConfig) -> dict[str, Any]:
    if not table_exists(engine, "cleaned_job_posts"):
        raise RuntimeError("Required table is missing: cleaned_job_posts")

    columns = get_table_columns(engine, "cleaned_job_posts")
    category_column = first_existing_column(columns, ["category", "job_category", "label", "target_category"])
    date_column = first_existing_column(columns, ["created_at", "updated_at", "posted_at", "ingested_at", "loaded_at"])

    total_where, total_params = build_training_where_clause(category_column, None, None)
    lookback_where, lookback_params = build_training_where_clause(category_column, date_column, config.lookback_days)
    recent_where, recent_params = build_training_where_clause(category_column, date_column, config.recent_days)

    total_rows = count_rows(engine, "cleaned_job_posts", total_where, total_params)
    lookback_rows = count_rows(engine, "cleaned_job_posts", lookback_where, lookback_params)
    recent_rows = count_rows(engine, "cleaned_job_posts", recent_where, recent_params)

    category_counts = get_category_counts(engine, "cleaned_job_posts", category_column, date_column, config.lookback_days)
    category_row_counts = [int(row["row_count"]) for row in category_counts]
    category_min_rows = min(category_row_counts) if category_row_counts else 0
    category_max_rows = max(category_row_counts) if category_row_counts else 0
    category_count = len(category_row_counts)
    imbalance_ratio = category_max_rows / category_min_rows if category_min_rows > 0 else None
    feedback_rows = count_feedback_rows(engine, config)

    return {
        "category_column": category_column,
        "date_column": date_column,
        "total_rows": total_rows,
        "lookback_rows": lookback_rows,
        "recent_rows": recent_rows,
        "category_count": category_count,
        "category_min_rows": category_min_rows,
        "category_max_rows": category_max_rows,
        "category_imbalance_ratio": imbalance_ratio,
        "feedback_rows": feedback_rows,
        "category_counts": category_counts,
    }


def build_check_results(profile: dict[str, Any], config: StrategyConfig) -> list[CheckResult]:
    total_rows = int(profile["total_rows"])
    lookback_rows = int(profile["lookback_rows"])
    recent_rows = int(profile["recent_rows"])
    category_min_rows = int(profile["category_min_rows"])
    category_count = int(profile["category_count"])
    feedback_rows = int(profile["feedback_rows"])
    imbalance_ratio = profile["category_imbalance_ratio"]

    full_retrain_allowed = total_rows <= config.max_full_retrain_rows
    window_retrain_allowed = (
        recent_rows >= config.min_window_rows
        and category_min_rows >= config.min_rows_per_class
        and category_count >= 2
    )
    sampling_retrain_recommended = (
        not full_retrain_allowed and recent_rows >= config.min_window_rows and category_count >= 2
    )
    incremental_experiment_recommended = total_rows >= config.incremental_experiment_row_threshold

    feedback_status = "PASS"
    feedback_message = "Production feedback is available."
    if feedback_rows == 0 and config.feedback_required:
        feedback_status = "WARN"
        feedback_message = "Production feedback is required by policy, but no feedback rows were found."
    elif feedback_rows == 0:
        feedback_status = "SKIPPED"
        feedback_message = "No production feedback rows found. Feedback is optional."

    return [
        CheckResult("training_total_rows", "PASS" if total_rows > 0 else "FAIL", float(total_rows), 1.0, "Training table has candidate rows."),
        CheckResult("training_lookback_rows", "PASS" if lookback_rows > 0 else "FAIL", float(lookback_rows), 1.0, f"Rows available in RETRAINING_LOOKBACK_DAYS={config.lookback_days} window."),
        CheckResult("training_recent_window_rows", "PASS" if recent_rows >= config.min_window_rows else "WARN", float(recent_rows), float(config.min_window_rows), f"Rows available in RETRAINING_RECENT_DAYS={config.recent_days} window."),
        CheckResult("training_category_count", "PASS" if category_count >= 2 else "FAIL", float(category_count), 2.0, "Number of trainable categories excluding Unknown."),
        CheckResult("training_category_min_rows", "PASS" if category_min_rows >= config.min_rows_per_class else "WARN", float(category_min_rows), float(config.min_rows_per_class), "Minimum row count among trainable categories."),
        CheckResult("training_category_imbalance_ratio", "PASS" if imbalance_ratio is not None and imbalance_ratio <= 10 else "WARN", float(imbalance_ratio) if imbalance_ratio is not None else None, 10.0, "Max category rows divided by min category rows."),
        CheckResult("training_feedback_rows", feedback_status, float(feedback_rows), 1.0 if config.feedback_required else 0.0, feedback_message),
        CheckResult("full_retrain_row_policy", "PASS" if full_retrain_allowed else "WARN", float(total_rows), float(config.max_full_retrain_rows), "Full retrain is still row-count acceptable." if full_retrain_allowed else "Training rows exceed preferred full retrain row threshold."),
        CheckResult("window_retrain_policy", "PASS" if window_retrain_allowed else "WARN", 1.0 if window_retrain_allowed else 0.0, 1.0, "Recent window has enough rows and category coverage." if window_retrain_allowed else "Recent window is not ready to replace full retrain."),
        CheckResult("sampling_retrain_recommended", "WARN" if sampling_retrain_recommended else "PASS", 1.0 if sampling_retrain_recommended else 0.0, 1.0, "Use recent data plus historical class-balanced samples." if sampling_retrain_recommended else "Sampling retrain is not required yet."),
        CheckResult("incremental_experiment_recommended", "WARN" if incremental_experiment_recommended else "PASS", 1.0 if incremental_experiment_recommended else 0.0, 1.0, "Run incremental retraining as a shadow experiment." if incremental_experiment_recommended else "Incremental shadow experiment is not required yet."),
    ]


def insert_check_results(engine: Engine, results: list[CheckResult]) -> None:
    if not table_exists(engine, "pipeline_check_results"):
        raise RuntimeError("Required table is missing: pipeline_check_results")

    columns = get_table_columns(engine, "pipeline_check_results")
    checked_at = datetime.now()
    rows = []

    for result in results:
        row = {
            "check_type": CHECK_TYPE,
            "check_name": result.check_name,
            "status": result.status,
            "metric_value": result.metric_value,
            "threshold_value": result.threshold_value,
            "message": result.message,
            "dag_id": DAG_ID,
            "task_id": TASK_ID,
            "run_id": RUN_ID,
            "checked_at": checked_at,
        }
        rows.append({key: value for key, value in row.items() if key in columns})

    if not rows:
        raise RuntimeError("pipeline_check_results has no compatible columns.")

    insert_columns = list(rows[0])
    column_sql = ", ".join(quote_ident(column) for column in insert_columns)
    value_sql = ", ".join(f":{column}" for column in insert_columns)
    query = f"INSERT INTO pipeline_check_results ({column_sql}) VALUES ({value_sql})"

    with engine.begin() as conn:
        for row in rows:
            conn.execute(text(query), row)


def print_summary(profile: dict[str, Any], results: list[CheckResult]) -> None:
    print("")
    print("Retraining Strategy Check")
    print("=========================")
    print(f"category_column={profile['category_column']}")
    print(f"date_column={profile['date_column']}")
    print(f"total_rows={profile['total_rows']}")
    print(f"lookback_rows={profile['lookback_rows']}")
    print(f"recent_rows={profile['recent_rows']}")
    print(f"category_count={profile['category_count']}")
    print(f"category_min_rows={profile['category_min_rows']}")
    print(f"category_max_rows={profile['category_max_rows']}")
    print(f"category_imbalance_ratio={profile['category_imbalance_ratio']}")
    print(f"feedback_rows={profile['feedback_rows']}")
    print("")
    for result in results:
        print(
            f"{result.status:7s} {result.check_name} "
            f"metric={result.metric_value} threshold={result.threshold_value} "
            f"message={result.message}"
        )


def main() -> None:
    config = load_config()
    engine = get_engine()
    profile = get_training_profile(engine, config)
    results = build_check_results(profile, config)
    insert_check_results(engine, results)
    print_summary(profile, results)

    failed_results = [result for result in results if result.status == "FAIL"]
    if failed_results:
        raise SystemExit(1)

    print("")
    print("PASS: Retraining strategy check completed.")


if __name__ == "__main__":
    main()

