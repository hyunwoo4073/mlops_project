from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


CHECK_TYPE = "RETRAINING_CANDIDATE"
TASK_ID = "check_retraining_candidate"


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


def calculate_weighted_f1_score(
    actual_values: list[str],
    predicted_values: list[str],
) -> float:
    labels = sorted(set(actual_values) | set(predicted_values))

    if not labels:
        return 0.0

    actual_counter = Counter(actual_values)
    total_support = sum(actual_counter.values())

    if total_support == 0:
        return 0.0

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

        f1_score = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0.0
        )

        weighted_f1_sum += f1_score * actual_counter[label]

    return float(weighted_f1_sum / total_support)


def fetch_feedback_rows(conn: Any, feedback_window_days: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                pf.prediction_id,
                pf.actual_category,
                mp.predicted_category,
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

    return [dict(row) for row in rows]


def fetch_production_feedback_history(conn: Any, limit: int = 100) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                COALESCE(run_id, checked_at::text) AS run_id,
                MAX(checked_at) AS evaluated_at,
                MAX(CASE WHEN check_name = 'production_feedback_count' THEN metric_value END) AS feedback_count,
                MAX(CASE WHEN check_name = 'production_accuracy' THEN metric_value END) AS accuracy,
                MAX(CASE WHEN check_name = 'production_f1_weighted' THEN metric_value END) AS f1_weighted,
                STRING_AGG(DISTINCT status, ', ' ORDER BY status) AS statuses
            FROM pipeline_check_results
            WHERE check_type = 'PRODUCTION_FEEDBACK'
              AND check_name IN (
                  'production_feedback_count',
                  'production_accuracy',
                  'production_f1_weighted'
              )
            GROUP BY COALESCE(run_id, checked_at::text)
            ORDER BY MAX(checked_at) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    return [dict(row) for row in rows]


def calculate_trend_delta(
    history_rows: list[dict[str, Any]],
    metric_name: str,
    min_history_points: int,
) -> float:
    valid_rows = [
        row
        for row in history_rows
        if row.get(metric_name) is not None
    ]

    if len(valid_rows) < min_history_points:
        return 0.0

    recent_rows = valid_rows[:min_history_points]
    latest_value = float(recent_rows[0][metric_name])
    oldest_value = float(recent_rows[-1][metric_name])

    return latest_value - oldest_value


def build_decision(
    feedback_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    min_feedback_rows: int,
    min_accuracy: float,
    min_f1_weighted: float,
    trend_drop_threshold: float,
    min_history_points: int,
) -> dict[str, Any]:
    feedback_count = len(feedback_rows)
    reasons: list[str] = []
    actions: list[str] = []

    if feedback_count == 0:
        accuracy = 0.0
        f1_weighted = 0.0
    else:
        actual_values = [row["actual_category"] for row in feedback_rows]
        predicted_values = [row["predicted_category"] for row in feedback_rows]
        correct_count = sum(
            1
            for actual, predicted in zip(actual_values, predicted_values, strict=False)
            if actual == predicted
        )
        accuracy = float(correct_count / feedback_count)
        f1_weighted = calculate_weighted_f1_score(actual_values, predicted_values)

    accuracy_delta = calculate_trend_delta(
        history_rows=history_rows,
        metric_name="accuracy",
        min_history_points=min_history_points,
    )
    f1_delta = calculate_trend_delta(
        history_rows=history_rows,
        metric_name="f1_weighted",
        min_history_points=min_history_points,
    )

    if feedback_count < min_feedback_rows:
        decision = "INSUFFICIENT_FEEDBACK"
        status = "SKIPPED"
        candidate_flag = 0.0
        reasons.append(
            f"Not enough production feedback rows. feedback_count={feedback_count}, required={min_feedback_rows}."
        )
        actions.append("Collect more production feedback before deciding retraining candidacy.")
    else:
        candidate_flag = 0.0

        if accuracy < min_accuracy:
            candidate_flag = 1.0
            reasons.append(
                f"Production accuracy is below threshold. accuracy={accuracy:.4f}, threshold={min_accuracy:.4f}."
            )

        if f1_weighted < min_f1_weighted:
            candidate_flag = 1.0
            reasons.append(
                f"Production weighted F1 is below threshold. f1_weighted={f1_weighted:.4f}, threshold={min_f1_weighted:.4f}."
            )

        if accuracy_delta <= -trend_drop_threshold:
            candidate_flag = 1.0
            reasons.append(
                f"Production accuracy trend dropped. accuracy_delta={accuracy_delta:.4f}, threshold=-{trend_drop_threshold:.4f}."
            )

        if f1_delta <= -trend_drop_threshold:
            candidate_flag = 1.0
            reasons.append(
                f"Production weighted F1 trend dropped. f1_delta={f1_delta:.4f}, threshold=-{trend_drop_threshold:.4f}."
            )

        if candidate_flag >= 1:
            decision = "RETRAINING_CANDIDATE"
            status = "FAIL"
            actions.extend(
                [
                    "Review recent wrong predictions and concentrated misclassification patterns.",
                    "Compare production feedback quality with the current promoted model evaluation metrics.",
                    "Consider retraining or rollback if this is based on real production feedback.",
                ]
            )
        else:
            decision = "STABLE"
            status = "PASS"
            reasons.append("Production feedback quality is within retraining decision thresholds.")
            actions.append("Continue monitoring production feedback and evaluation history.")

    return {
        "decision": decision,
        "status": status,
        "candidate_flag": candidate_flag,
        "feedback_count": float(feedback_count),
        "accuracy": accuracy,
        "f1_weighted": f1_weighted,
        "accuracy_delta": accuracy_delta,
        "f1_delta": f1_delta,
        "reasons": reasons,
        "actions": actions,
    }


def insert_check_result(
    conn: Any,
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
            "task_id": os.getenv("AIRFLOW_CTX_TASK_ID", TASK_ID),
            "run_id": run_id,
        },
    )


def persist_decision(
    conn: Any,
    decision: dict[str, Any],
    min_feedback_rows: int,
    min_accuracy: float,
    min_f1_weighted: float,
    trend_drop_threshold: float,
    run_id: str,
) -> None:
    status = str(decision["status"])
    reason_message = " | ".join(decision["reasons"])

    insert_check_result(
        conn=conn,
        check_name="retraining_candidate_flag",
        status=status,
        metric_value=float(decision["candidate_flag"]),
        threshold_value=0.0,
        message=f"decision={decision['decision']}. {reason_message}",
        run_id=run_id,
    )

    insert_check_result(
        conn=conn,
        check_name="retraining_feedback_count",
        status="PASS" if decision["feedback_count"] >= min_feedback_rows else "SKIPPED",
        metric_value=float(decision["feedback_count"]),
        threshold_value=float(min_feedback_rows),
        message=f"feedback_count={decision['feedback_count']:.0f}, required={min_feedback_rows}",
        run_id=run_id,
    )

    insert_check_result(
        conn=conn,
        check_name="retraining_accuracy",
        status=(
            "SKIPPED"
            if status == "SKIPPED"
            else "PASS"
            if decision["accuracy"] >= min_accuracy
            else "FAIL"
        ),
        metric_value=float(decision["accuracy"]),
        threshold_value=float(min_accuracy),
        message=f"accuracy={decision['accuracy']:.4f}, threshold={min_accuracy:.4f}",
        run_id=run_id,
    )

    insert_check_result(
        conn=conn,
        check_name="retraining_f1_weighted",
        status=(
            "SKIPPED"
            if status == "SKIPPED"
            else "PASS"
            if decision["f1_weighted"] >= min_f1_weighted
            else "FAIL"
        ),
        metric_value=float(decision["f1_weighted"]),
        threshold_value=float(min_f1_weighted),
        message=f"f1_weighted={decision['f1_weighted']:.4f}, threshold={min_f1_weighted:.4f}",
        run_id=run_id,
    )

    insert_check_result(
        conn=conn,
        check_name="retraining_accuracy_delta",
        status=(
            "SKIPPED"
            if status == "SKIPPED"
            else "FAIL"
            if decision["accuracy_delta"] <= -trend_drop_threshold
            else "PASS"
        ),
        metric_value=float(decision["accuracy_delta"]),
        threshold_value=-float(trend_drop_threshold),
        message=(
            f"accuracy_delta={decision['accuracy_delta']:.4f}, "
            f"drop_threshold=-{trend_drop_threshold:.4f}"
        ),
        run_id=run_id,
    )

    insert_check_result(
        conn=conn,
        check_name="retraining_f1_delta",
        status=(
            "SKIPPED"
            if status == "SKIPPED"
            else "FAIL"
            if decision["f1_delta"] <= -trend_drop_threshold
            else "PASS"
        ),
        metric_value=float(decision["f1_delta"]),
        threshold_value=-float(trend_drop_threshold),
        message=(
            f"f1_delta={decision['f1_delta']:.4f}, "
            f"drop_threshold=-{trend_drop_threshold:.4f}"
        ),
        run_id=run_id,
    )


def main() -> None:
    min_feedback_rows = get_int_env("MIN_PRODUCTION_FEEDBACK_ROWS", 10)
    min_accuracy = get_float_env("MIN_PRODUCTION_ACCURACY", 0.70)
    min_f1_weighted = get_float_env("MIN_PRODUCTION_F1_WEIGHTED", 0.70)
    feedback_window_days = get_int_env("PRODUCTION_FEEDBACK_WINDOW_DAYS", 30)
    trend_drop_threshold = get_float_env("PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD", 0.05)
    min_history_points = get_int_env("PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS", 3)
    strict_mode = get_bool_env("RETRAINING_CANDIDATE_STRICT", False)

    run_id = os.getenv(
        "AIRFLOW_CTX_DAG_RUN_ID",
        f"manual__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
    )

    engine = get_engine()

    with engine.begin() as conn:
        feedback_rows = fetch_feedback_rows(
            conn=conn,
            feedback_window_days=feedback_window_days,
        )
        history_rows = fetch_production_feedback_history(conn=conn)
        decision = build_decision(
            feedback_rows=feedback_rows,
            history_rows=history_rows,
            min_feedback_rows=min_feedback_rows,
            min_accuracy=min_accuracy,
            min_f1_weighted=min_f1_weighted,
            trend_drop_threshold=trend_drop_threshold,
            min_history_points=min_history_points,
        )
        persist_decision(
            conn=conn,
            decision=decision,
            min_feedback_rows=min_feedback_rows,
            min_accuracy=min_accuracy,
            min_f1_weighted=min_f1_weighted,
            trend_drop_threshold=trend_drop_threshold,
            run_id=run_id,
        )

    print("")
    print("Retraining Candidate Check")
    print("==========================")
    print(f"decision              : {decision['decision']}")
    print(f"status                : {decision['status']}")
    print(f"candidate_flag        : {decision['candidate_flag']:.0f}")
    print(f"feedback_count        : {decision['feedback_count']:.0f}")
    print(f"min_feedback_rows     : {min_feedback_rows}")
    print(f"accuracy              : {decision['accuracy']:.4f}")
    print(f"min_accuracy          : {min_accuracy:.4f}")
    print(f"f1_weighted           : {decision['f1_weighted']:.4f}")
    print(f"min_f1_weighted       : {min_f1_weighted:.4f}")
    print(f"accuracy_delta        : {decision['accuracy_delta']:.4f}")
    print(f"f1_delta              : {decision['f1_delta']:.4f}")
    print(f"trend_drop_threshold  : {trend_drop_threshold:.4f}")
    print(f"strict_mode           : {strict_mode}")
    print("")
    print("Reasons")
    print("-------")
    for reason in decision["reasons"]:
        print(f"- {reason}")
    print("")
    print("Actions")
    print("-------")
    for action in decision["actions"]:
        print(f"- {action}")
    print("")

    if decision["status"] == "FAIL" and strict_mode:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

