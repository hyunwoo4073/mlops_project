from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, f1_score
from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


CHECK_TYPE = "PRODUCTION_FEEDBACK"


def get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    return float(raw_value)


def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    return int(raw_value)


def get_bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def log_check_result(
    conn: Any,
    check_name: str,
    status: str,
    metric_value: float,
    threshold_value: float,
    message: str,
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
                :check_type,
                :check_name,
                :status,
                :metric_value,
                :threshold_value,
                :message,
                :dag_id,
                :task_id,
                :run_id,
                NOW()
            )
            """
        ),
        {
            "check_type": CHECK_TYPE,
            "check_name": check_name,
            "status": status,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "message": message,
            "dag_id": os.getenv("AIRFLOW_CTX_DAG_ID", "manual"),
            "task_id": os.getenv("AIRFLOW_CTX_TASK_ID", "check_production_feedback"),
            "run_id": os.getenv("AIRFLOW_CTX_DAG_RUN_ID", "manual"),
        },
    )


def main() -> None:
    min_feedback_rows = get_int_env("MIN_PRODUCTION_FEEDBACK_ROWS", 10)
    min_accuracy = get_float_env("MIN_PRODUCTION_ACCURACY", 0.70)
    min_f1_weighted = get_float_env("MIN_PRODUCTION_F1_WEIGHTED", 0.70)
    feedback_window_days = get_int_env("PRODUCTION_FEEDBACK_WINDOW_DAYS", 30)
    strict_mode = get_bool_env("PRODUCTION_FEEDBACK_STRICT", False)

    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    pf.prediction_id,
                    pf.actual_category,
                    mp.predicted_category,
                    mp.prediction_source,
                    mp.model_registry_id,
                    mp.model_run_id,
                    pf.feedback_source,
                    pf.created_at
                FROM prediction_feedbacks pf
                JOIN model_predictions mp
                    ON pf.prediction_id = mp.id
                WHERE pf.created_at >= NOW() - (:feedback_window_days * INTERVAL '1 day')
                ORDER BY pf.created_at DESC, pf.id DESC
                """
            ),
            {"feedback_window_days": feedback_window_days},
        ).mappings().all()

        feedback_count = len(rows)

        if feedback_count < min_feedback_rows:
            message = (
                f"Not enough production feedback rows. "
                f"feedback_count={feedback_count}, "
                f"required={min_feedback_rows}, "
                f"window_days={feedback_window_days}"
            )

            log_check_result(
                conn=conn,
                check_name="production_feedback_count",
                status="SKIPPED",
                metric_value=float(feedback_count),
                threshold_value=float(min_feedback_rows),
                message=message,
            )

            print("")
            print("Production Feedback Check")
            print("=========================")
            print(message)
            print("[SKIPPED] production feedback evaluation")
            print("")

            return

        actual_values = [row["actual_category"] for row in rows]
        predicted_values = [row["predicted_category"] for row in rows]

        accuracy = float(accuracy_score(actual_values, predicted_values))
        f1_weighted = float(
            f1_score(
                actual_values,
                predicted_values,
                average="weighted",
                zero_division=0,
            )
        )

        accuracy_status = "PASS" if accuracy >= min_accuracy else "FAIL"
        f1_status = "PASS" if f1_weighted >= min_f1_weighted else "FAIL"

        overall_status = (
            "PASS"
            if accuracy_status == "PASS" and f1_status == "PASS"
            else "FAIL"
        )

        log_check_result(
            conn=conn,
            check_name="production_feedback_count",
            status="PASS",
            metric_value=float(feedback_count),
            threshold_value=float(min_feedback_rows),
            message=(
                f"Production feedback count is sufficient. "
                f"feedback_count={feedback_count}, "
                f"required={min_feedback_rows}"
            ),
        )

        log_check_result(
            conn=conn,
            check_name="production_accuracy",
            status=accuracy_status,
            metric_value=accuracy,
            threshold_value=min_accuracy,
            message=(
                f"Production feedback accuracy={accuracy:.4f}, "
                f"threshold={min_accuracy:.4f}, "
                f"feedback_count={feedback_count}"
            ),
        )

        log_check_result(
            conn=conn,
            check_name="production_f1_weighted",
            status=f1_status,
            metric_value=f1_weighted,
            threshold_value=min_f1_weighted,
            message=(
                f"Production feedback weighted_f1={f1_weighted:.4f}, "
                f"threshold={min_f1_weighted:.4f}, "
                f"feedback_count={feedback_count}"
            ),
        )

    print("")
    print("Production Feedback Check")
    print("=========================")
    print(f"feedback_count         : {feedback_count}")
    print(f"min_feedback_rows      : {min_feedback_rows}")
    print(f"accuracy               : {accuracy:.4f}")
    print(f"min_accuracy           : {min_accuracy:.4f}")
    print(f"f1_weighted            : {f1_weighted:.4f}")
    print(f"min_f1_weighted        : {min_f1_weighted:.4f}")
    print(f"overall_status         : {overall_status}")
    print(f"strict_mode            : {strict_mode}")
    print("")

    if overall_status == "FAIL" and strict_mode:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
