from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import text


@dataclass
class PipelineCheckLog:
    check_type: str
    check_name: str
    status: str
    metric_value: float | None
    threshold_value: float | None
    message: str


def get_airflow_context() -> dict[str, str | None]:
    return {
        "dag_id": os.getenv("AIRFLOW_CTX_DAG_ID"),
        "task_id": os.getenv("AIRFLOW_CTX_TASK_ID"),
        "run_id": os.getenv("AIRFLOW_CTX_DAG_RUN_ID"),
    }


def save_check_results(conn, results: list[PipelineCheckLog]) -> None:
    if not results:
        return

    context = get_airflow_context()

    insert_sql = text(
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
            run_id
        )
        VALUES (
            :check_type,
            :check_name,
            :status,
            :metric_value,
            :threshold_value,
            :message,
            :dag_id,
            :task_id,
            :run_id
        )
        """
    )

    payload = []
    for result in results:
        payload.append(
            {
                "check_type": result.check_type,
                "check_name": result.check_name,
                "status": result.status,
                "metric_value": result.metric_value,
                "threshold_value": result.threshold_value,
                "message": result.message,
                "dag_id": context["dag_id"],
                "task_id": context["task_id"],
                "run_id": context["run_id"],
            }
        )

    conn.execute(insert_sql, payload)
