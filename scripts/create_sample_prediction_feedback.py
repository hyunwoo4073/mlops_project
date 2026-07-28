from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.db import get_engine


FALLBACK_LABELS = [
    "Data Engineer",
    "Backend Engineer",
    "ML Engineer",
    "DevOps Engineer",
    "Data Analyst",
]


def choose_wrong_label(predicted_category: str) -> str:
    for label in FALLBACK_LABELS:
        if label != predicted_category:
            return label

    return "Unknown"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create sample production feedback records from recent predictions."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of recent predictions to create feedback for.",
    )
    parser.add_argument(
        "--wrong-every",
        type=int,
        default=5,
        help="Every Nth feedback will be intentionally wrong for demo evaluation.",
    )
    parser.add_argument(
        "--created-by",
        default="sample_feedback_script",
        help="created_by value for inserted feedback rows.",
    )

    args = parser.parse_args()

    limit = max(1, args.limit)
    wrong_every = max(0, args.wrong_every)

    engine = get_engine()

    with engine.begin() as conn:
        prediction_rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    COALESCE(predicted_category, 'Unknown') AS predicted_category,
                    prediction_source,
                    confidence
                FROM model_predictions
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

        if not prediction_rows:
            print("[FAIL] No model_predictions rows found.")
            raise SystemExit(1)

        inserted_count = 0
        correct_count = 0
        wrong_count = 0

        for index, row in enumerate(prediction_rows, start=1):
            predicted_category = row["predicted_category"]

            should_make_wrong = wrong_every > 0 and index % wrong_every == 0

            if should_make_wrong:
                actual_category = choose_wrong_label(predicted_category)
                wrong_count += 1
            else:
                actual_category = predicted_category
                correct_count += 1

            conn.execute(
                text(
                    """
                    INSERT INTO prediction_feedbacks (
                        prediction_id,
                        actual_category,
                        feedback_source,
                        feedback_note,
                        created_by,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :prediction_id,
                        :actual_category,
                        'sample',
                        :feedback_note,
                        :created_by,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (prediction_id)
                    DO UPDATE SET
                        actual_category = EXCLUDED.actual_category,
                        feedback_source = EXCLUDED.feedback_source,
                        feedback_note = EXCLUDED.feedback_note,
                        created_by = EXCLUDED.created_by,
                        updated_at = NOW()
                    """
                ),
                {
                    "prediction_id": row["id"],
                    "actual_category": actual_category,
                    "feedback_note": (
                        "sample feedback generated for production evaluation"
                    ),
                    "created_by": args.created_by,
                },
            )

            inserted_count += 1

    print("")
    print("Sample Prediction Feedback")
    print("==========================")
    print(f"target_predictions : {len(prediction_rows)}")
    print(f"upserted_feedbacks : {inserted_count}")
    print(f"correct_feedbacks  : {correct_count}")
    print(f"wrong_feedbacks    : {wrong_count}")
    print("")


if __name__ == "__main__":
    main()
