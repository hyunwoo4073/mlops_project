from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text


# project root를 PYTHONPATH에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.quality.check_logger import PipelineCheckLog, save_check_results


PREDICTION_SOURCE_BATCH = "BATCH"


@dataclass
class CheckResult:
    name: str
    passed: bool
    metric_value: float | None
    threshold_value: float | None
    message: str


def main() -> None:
    min_avg_confidence = float(os.getenv("MIN_AVG_PREDICTION_CONFIDENCE", "0.6"))
    max_low_confidence_ratio = float(os.getenv("MAX_LOW_CONFIDENCE_RATIO", "0.4"))
    min_prediction_rows = int(os.getenv("MIN_PREDICTION_ROWS", "1"))

    engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS prediction_count,
                    AVG(confidence) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count,
                    COUNT(*) FILTER (WHERE confidence IS NULL) AS null_confidence_count
                FROM model_predictions
                WHERE COALESCE(prediction_source, 'BATCH') = :prediction_source
                  AND job_post_id IS NOT NULL
                """
            ),
            {"prediction_source": PREDICTION_SOURCE_BATCH},
        ).mappings().one()

        source_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(r.source, 'unknown') AS source,
                    COUNT(*) AS prediction_count,
                    AVG(mp.confidence) AS avg_confidence,
                    COUNT(*) FILTER (WHERE mp.is_low_confidence = true) AS low_confidence_count
                FROM model_predictions mp
                JOIN cleaned_job_posts c
                    ON mp.job_post_id = c.id
                JOIN raw_job_posts r
                    ON c.raw_id = r.id
                WHERE COALESCE(mp.prediction_source, 'BATCH') = :prediction_source
                  AND mp.job_post_id IS NOT NULL
                GROUP BY COALESCE(r.source, 'unknown')
                ORDER BY source
                """
            ),
            {"prediction_source": PREDICTION_SOURCE_BATCH},
        ).mappings().all()

        category_rows = conn.execute(
            text(
                """
                SELECT
                    predicted_category,
                    COUNT(*) AS prediction_count,
                    AVG(confidence) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count
                FROM model_predictions
                WHERE COALESCE(prediction_source, 'BATCH') = :prediction_source
                  AND job_post_id IS NOT NULL
                GROUP BY predicted_category
                ORDER BY prediction_count DESC
                """
            ),
            {"prediction_source": PREDICTION_SOURCE_BATCH},
        ).mappings().all()

    prediction_count = int(row["prediction_count"] or 0)
    avg_confidence = float(row["avg_confidence"] or 0.0)
    low_confidence_count = int(row["low_confidence_count"] or 0)
    null_confidence_count = int(row["null_confidence_count"] or 0)

    low_confidence_ratio = (
        low_confidence_count / prediction_count if prediction_count > 0 else 0.0
    )

    results: list[CheckResult] = []

    results.append(
        CheckResult(
            name="prediction_count",
            passed=prediction_count >= min_prediction_rows,
            metric_value=float(prediction_count),
            threshold_value=float(min_prediction_rows),
            message=(
                f"prediction_count={prediction_count}, "
                f"required >= {min_prediction_rows}"
            ),
        )
    )

    results.append(
        CheckResult(
            name="avg_prediction_confidence",
            passed=avg_confidence >= min_avg_confidence,
            metric_value=avg_confidence,
            threshold_value=min_avg_confidence,
            message=(
                f"avg_confidence={avg_confidence:.4f}, "
                f"required >= {min_avg_confidence:.4f}"
            ),
        )
    )

    results.append(
        CheckResult(
            name="low_confidence_ratio",
            passed=low_confidence_ratio <= max_low_confidence_ratio,
            metric_value=low_confidence_ratio,
            threshold_value=max_low_confidence_ratio,
            message=(
                f"low_confidence_count={low_confidence_count}, "
                f"prediction_count={prediction_count}, "
                f"low_confidence_ratio={low_confidence_ratio:.4f}, "
                f"allowed <= {max_low_confidence_ratio:.4f}"
            ),
        )
    )

    results.append(
        CheckResult(
            name="null_confidence_count",
            passed=null_confidence_count == 0,
            metric_value=float(null_confidence_count),
            threshold_value=0.0,
            message=f"null_confidence_count={null_confidence_count}, required = 0",
        )
    )

    print("\n[Prediction Quality Check]")
    print(f"prediction_source        : {PREDICTION_SOURCE_BATCH}")
    print(f"prediction_count         : {prediction_count}")
    print(f"avg_confidence           : {avg_confidence:.4f}")
    print(f"low_confidence_count     : {low_confidence_count}")
    print(f"low_confidence_ratio     : {low_confidence_ratio:.4f}")
    print(f"null_confidence_count    : {null_confidence_count}")

    print("\n[Prediction Quality by Source]")
    if not source_rows:
        print("No source-level batch prediction rows found.")

    for source_row in source_rows:
        source_prediction_count = int(source_row["prediction_count"] or 0)
        source_low_count = int(source_row["low_confidence_count"] or 0)
        source_low_ratio = (
            source_low_count / source_prediction_count
            if source_prediction_count > 0
            else 0.0
        )
        source_avg_confidence = float(source_row["avg_confidence"] or 0.0)

        print(
            f"{source_row['source']} | "
            f"count={source_prediction_count}, "
            f"avg_confidence={source_avg_confidence:.4f}, "
            f"low_ratio={source_low_ratio:.4f}"
        )

    print("\n[Prediction Quality by Category]")
    if not category_rows:
        print("No category-level batch prediction rows found.")

    for category_row in category_rows:
        category_prediction_count = int(category_row["prediction_count"] or 0)
        category_low_count = int(category_row["low_confidence_count"] or 0)
        category_low_ratio = (
            category_low_count / category_prediction_count
            if category_prediction_count > 0
            else 0.0
        )
        category_avg_confidence = float(category_row["avg_confidence"] or 0.0)

        print(
            f"{category_row['predicted_category']} | "
            f"count={category_prediction_count}, "
            f"avg_confidence={category_avg_confidence:.4f}, "
            f"low_ratio={category_low_ratio:.4f}"
        )

    check_logs = [
        PipelineCheckLog(
            check_type="PREDICTION_QUALITY",
            check_name=result.name,
            status="PASS" if result.passed else "FAIL",
            metric_value=result.metric_value,
            threshold_value=result.threshold_value,
            message=result.message,
        )
        for result in results
    ]

    with engine.begin() as conn:
        save_check_results(conn, check_logs)

    failed_results = [result for result in results if not result.passed]

    if failed_results:
        print("\n[Failed Prediction Quality Checks]")
        for result in failed_results:
            print(f"- {result.name}: {result.message}")

        raise ValueError("Prediction quality check failed.")

    print("\nPrediction quality check passed.")


if __name__ == "__main__":
    main()