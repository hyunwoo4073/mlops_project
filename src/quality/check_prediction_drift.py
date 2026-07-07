from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


CHECK_TYPE = "PREDICTION_DRIFT"
PREDICTION_SOURCE_BATCH = "BATCH"


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    return float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    return int(value)


def fetch_label_distribution(conn) -> dict[str, int]:
    rows = conn.execute(
        text(
            """
            SELECT
                COALESCE(job_category, 'Unknown') AS category,
                COUNT(*) AS count
            FROM cleaned_job_posts
            GROUP BY COALESCE(job_category, 'Unknown')
            ORDER BY category
            """
        )
    ).mappings().all()

    return {str(row["category"]): int(row["count"]) for row in rows}


def fetch_prediction_distribution(conn) -> dict[str, int]:
    rows = conn.execute(
        text(
            """
            SELECT
                COALESCE(predicted_category, 'Unknown') AS category,
                COUNT(*) AS count
            FROM model_predictions
            WHERE COALESCE(prediction_source, 'BATCH') = :prediction_source
            GROUP BY COALESCE(predicted_category, 'Unknown')
            ORDER BY category
            """
        ),
        {"prediction_source": PREDICTION_SOURCE_BATCH},
    ).mappings().all()

    return {str(row["category"]): int(row["count"]) for row in rows}


def calculate_psi(
    expected_counts: dict[str, int],
    actual_counts: dict[str, int],
    epsilon: float = 0.0001,
) -> float:
    categories = sorted(set(expected_counts) | set(actual_counts))

    expected_total = sum(expected_counts.values())
    actual_total = sum(actual_counts.values())

    if expected_total <= 0 or actual_total <= 0:
        return 0.0

    psi = 0.0

    for category in categories:
        expected_ratio = expected_counts.get(category, 0) / expected_total
        actual_ratio = actual_counts.get(category, 0) / actual_total

        expected_ratio = max(expected_ratio, epsilon)
        actual_ratio = max(actual_ratio, epsilon)

        psi += (actual_ratio - expected_ratio) * math.log(actual_ratio / expected_ratio)

    return psi


def insert_check_result(
    conn,
    check_name: str,
    status: str,
    metric_value: float | int | None,
    threshold_value: float | int | None,
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
                message
            )
            VALUES (
                :check_type,
                :check_name,
                :status,
                :metric_value,
                :threshold_value,
                :message
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
        },
    )


def print_distribution(title: str, distribution: dict[str, int]) -> None:
    total = sum(distribution.values())

    print(title)

    if total <= 0:
        print("- empty")
        return

    for category, count in sorted(distribution.items()):
        ratio = count / total
        print(f"- {category}: count={count}, ratio={ratio:.4f}")


def main() -> None:
    max_prediction_distribution_psi = _env_float(
        "MAX_PREDICTION_DISTRIBUTION_PSI",
        0.25,
    )
    min_drift_check_rows = _env_int("MIN_DRIFT_CHECK_ROWS", 1)

    engine = get_engine()

    print()
    print("[Prediction Drift Check]")
    print(f"MAX_PREDICTION_DISTRIBUTION_PSI : {max_prediction_distribution_psi}")
    print(f"MIN_DRIFT_CHECK_ROWS            : {min_drift_check_rows}")
    print()

    failed_checks: list[str] = []

    with engine.begin() as conn:
        label_distribution = fetch_label_distribution(conn)
        prediction_distribution = fetch_prediction_distribution(conn)

        label_total = sum(label_distribution.values())
        prediction_total = sum(prediction_distribution.values())

        print_distribution("[Label Distribution]", label_distribution)
        print()
        print_distribution("[Batch Prediction Distribution]", prediction_distribution)
        print()

        label_status = "PASS" if label_total >= min_drift_check_rows else "FAIL"
        prediction_status = "PASS" if prediction_total >= min_drift_check_rows else "FAIL"

        insert_check_result(
            conn=conn,
            check_name="label_distribution_rows",
            status=label_status,
            metric_value=label_total,
            threshold_value=min_drift_check_rows,
            message=(
                f"label_total={label_total}, "
                f"required >= {min_drift_check_rows}"
            ),
        )

        insert_check_result(
            conn=conn,
            check_name="prediction_distribution_rows",
            status=prediction_status,
            metric_value=prediction_total,
            threshold_value=min_drift_check_rows,
            message=(
                f"prediction_total={prediction_total}, "
                f"required >= {min_drift_check_rows}"
            ),
        )

        if label_status == "FAIL":
            failed_checks.append("label_distribution_rows")

        if prediction_status == "FAIL":
            failed_checks.append("prediction_distribution_rows")

        psi = calculate_psi(
            expected_counts=label_distribution,
            actual_counts=prediction_distribution,
        )

        psi_status = "PASS" if psi <= max_prediction_distribution_psi else "FAIL"

        insert_check_result(
            conn=conn,
            check_name="prediction_distribution_psi",
            status=psi_status,
            metric_value=psi,
            threshold_value=max_prediction_distribution_psi,
            message=(
                f"prediction_distribution_psi={psi:.4f}, "
                f"allowed <= {max_prediction_distribution_psi:.4f}"
            ),
        )

        if psi_status == "FAIL":
            failed_checks.append("prediction_distribution_psi")

    print("[Prediction Drift Result]")
    print(f"label_total      : {label_total}")
    print(f"prediction_total : {prediction_total}")
    print(f"psi              : {psi:.4f}")
    print(f"status           : {'FAIL' if failed_checks else 'PASS'}")
    print()

    if failed_checks:
        raise ValueError(
            "Prediction drift check failed: "
            + ", ".join(failed_checks)
        )

    print("Prediction drift check passed.")


if __name__ == "__main__":
    main()
