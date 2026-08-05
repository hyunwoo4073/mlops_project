from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


CHECK_TYPE = "TRAINING_COST"


@dataclass
class TrainingCostSnapshot:
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    training_rows: int | None = None
    category_count: int | None = None
    model_size_bytes: int | None = None
    mlflow_run_id: str | None = None


class TrainingCostTimer:
    def __init__(self) -> None:
        self._started_perf = time.perf_counter()
        self.snapshot = TrainingCostSnapshot(started_at=datetime.now())

    def finish(
        self,
        *,
        training_rows: int | None = None,
        category_count: int | None = None,
        model_path: str | Path | None = None,
        mlflow_run_id: str | None = None,
    ) -> TrainingCostSnapshot:
        finished_perf = time.perf_counter()
        self.snapshot.finished_at = datetime.now()
        self.snapshot.duration_seconds = finished_perf - self._started_perf
        self.snapshot.training_rows = training_rows
        self.snapshot.category_count = category_count
        self.snapshot.mlflow_run_id = mlflow_run_id

        if model_path is not None:
            self.snapshot.model_size_bytes = get_file_size_bytes(model_path)

        return self.snapshot


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


def table_exists(engine: Engine, table_name: str) -> bool:
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
    """

    with engine.begin() as conn:
        return bool(conn.execute(text(query), {"table_name": table_name}).scalar())


def get_table_columns(engine: Engine, table_name: str) -> set[str]:
    if not table_exists(engine, table_name):
        return set()

    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """

    with engine.begin() as conn:
        rows = conn.execute(text(query), {"table_name": table_name}).mappings().all()

    return {str(row["column_name"]) for row in rows}


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def get_file_size_bytes(path: str | Path | None) -> int:
    if path is None:
        return 0

    file_path = Path(path)

    if not file_path.exists():
        return 0

    return file_path.stat().st_size


def _status_for_threshold(
    *,
    metric_value: float | None,
    threshold_value: float | None,
    lower_is_better: bool = True,
) -> str:
    if metric_value is None or threshold_value is None:
        return "SKIPPED"

    if lower_is_better:
        return "PASS" if metric_value <= threshold_value else "WARN"

    return "PASS" if metric_value >= threshold_value else "WARN"


def _build_training_cost_rows(
    snapshot: TrainingCostSnapshot,
    *,
    max_full_retrain_seconds: float,
    incremental_seconds_threshold: float,
) -> list[dict[str, Any]]:
    duration_seconds = snapshot.duration_seconds or 0.0
    training_rows = snapshot.training_rows or 0
    category_count = snapshot.category_count or 0
    model_size_bytes = snapshot.model_size_bytes or 0

    throughput_rows_per_second = (
        training_rows / duration_seconds
        if duration_seconds > 0 and training_rows > 0
        else 0.0
    )

    duration_status = _status_for_threshold(
        metric_value=duration_seconds,
        threshold_value=max_full_retrain_seconds,
        lower_is_better=True,
    )

    incremental_status = (
        "WARN"
        if duration_seconds >= incremental_seconds_threshold
        else "PASS"
    )

    return [
        {
            "check_name": "training_duration_seconds",
            "status": duration_status,
            "metric_value": duration_seconds,
            "threshold_value": max_full_retrain_seconds,
            "message": "End-to-end baseline training duration in seconds.",
        },
        {
            "check_name": "training_rows",
            "status": "PASS" if training_rows > 0 else "FAIL",
            "metric_value": float(training_rows),
            "threshold_value": 1.0,
            "message": "Number of rows used for baseline model training.",
        },
        {
            "check_name": "training_category_count",
            "status": "PASS" if category_count >= 2 else "FAIL",
            "metric_value": float(category_count),
            "threshold_value": 2.0,
            "message": "Number of categories used for baseline model training.",
        },
        {
            "check_name": "training_throughput_rows_per_second",
            "status": "PASS" if throughput_rows_per_second > 0 else "SKIPPED",
            "metric_value": throughput_rows_per_second,
            "threshold_value": None,
            "message": "Training throughput calculated as rows divided by duration seconds.",
        },
        {
            "check_name": "model_size_bytes",
            "status": "PASS" if model_size_bytes > 0 else "WARN",
            "metric_value": float(model_size_bytes),
            "threshold_value": None,
            "message": "Serialized baseline model artifact size in bytes.",
        },
        {
            "check_name": "incremental_experiment_by_duration",
            "status": incremental_status,
            "metric_value": duration_seconds,
            "threshold_value": incremental_seconds_threshold,
            "message": (
                "Incremental retraining shadow experiment is recommended when "
                "full retrain duration exceeds the configured threshold."
                if incremental_status == "WARN"
                else "Full retrain duration is still below the incremental experiment threshold."
            ),
        },
    ]


def record_training_cost_snapshot(
    snapshot: TrainingCostSnapshot,
    *,
    dag_id: str = "manual",
    task_id: str = "train_baseline",
    run_id: str | None = None,
    engine: Engine | None = None,
) -> None:
    db_engine = engine or get_engine()

    if not table_exists(db_engine, "pipeline_check_results"):
        return

    columns = get_table_columns(db_engine, "pipeline_check_results")

    max_full_retrain_seconds = float(
        os.getenv("RETRAINING_MAX_FULL_RETRAIN_SECONDS", "1800")
    )
    incremental_seconds_threshold = float(
        os.getenv("RETRAINING_INCREMENTAL_EXPERIMENT_SECONDS_THRESHOLD", "3600")
    )

    rows = _build_training_cost_rows(
        snapshot,
        max_full_retrain_seconds=max_full_retrain_seconds,
        incremental_seconds_threshold=incremental_seconds_threshold,
    )

    checked_at = snapshot.finished_at or datetime.now()
    resolved_run_id = run_id or snapshot.mlflow_run_id or "manual_training_cost"

    insert_rows: list[dict[str, Any]] = []

    for row in rows:
        insert_row = {
            "check_type": CHECK_TYPE,
            "check_name": row["check_name"],
            "status": row["status"],
            "metric_value": row["metric_value"],
            "threshold_value": row["threshold_value"],
            "message": row["message"],
            "dag_id": dag_id,
            "task_id": task_id,
            "run_id": resolved_run_id,
            "checked_at": checked_at,
        }
        insert_rows.append(
            {
                key: value
                for key, value in insert_row.items()
                if key in columns
            }
        )

    if not insert_rows:
        return

    insert_columns = list(insert_rows[0].keys())
    column_sql = ", ".join(quote_ident(column) for column in insert_columns)
    value_sql = ", ".join(f":{column}" for column in insert_columns)

    query = f"""
        INSERT INTO pipeline_check_results ({column_sql})
        VALUES ({value_sql})
    """

    with db_engine.begin() as conn:
        for row in insert_rows:
            conn.execute(text(query), row)


def log_training_cost_to_mlflow(
    snapshot: TrainingCostSnapshot,
    *,
    mlflow_module: Any,
) -> None:
    metrics = {
        "training_duration_seconds": snapshot.duration_seconds or 0.0,
        "training_rows": float(snapshot.training_rows or 0),
        "training_category_count": float(snapshot.category_count or 0),
        "training_model_size_bytes": float(snapshot.model_size_bytes or 0),
    }

    duration_seconds = snapshot.duration_seconds or 0.0
    training_rows = snapshot.training_rows or 0

    if duration_seconds > 0 and training_rows > 0:
        metrics["training_throughput_rows_per_second"] = (
            training_rows / duration_seconds
        )

    for name, value in metrics.items():
        mlflow_module.log_metric(name, value)

