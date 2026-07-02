import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text


# 프로젝트 루트를 import path에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.common.model_registry import get_current_model_metadata
from src.common.prediction_quality import build_prediction_quality


PREDICTION_SOURCE_BATCH = "BATCH"


def main():
    engine = get_engine()

    model_metadata = get_current_model_metadata()

    print("\n[Inference Model]")
    print(f"model_name        : {model_metadata.model_name}")
    print(f"run_id            : {model_metadata.run_id}")
    print(f"model_registry_id : {model_metadata.model_registry_id}")
    print(f"model_path        : {model_metadata.model_path}")
    print(f"status            : {model_metadata.status}")

    model = joblib.load(model_metadata.model_path)

    query = """
        SELECT
            id AS job_post_id,
            text_for_model
        FROM cleaned_job_posts
        WHERE text_for_model IS NOT NULL
          AND text_for_model <> ''
        ORDER BY id
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError("No cleaned job posts found. Run preprocess_db.py first.")

    texts = df["text_for_model"].tolist()

    preds = model.predict(texts)
    qualities = build_prediction_quality(model, texts)

    prediction_rows = []

    for row, pred, quality in zip(df.itertuples(index=False), preds, qualities):
        prediction_rows.append(
            {
                "job_post_id": int(row.job_post_id),
                "prediction_source": PREDICTION_SOURCE_BATCH,
                "model_name": model_metadata.model_name,
                "model_version": model_metadata.run_id or model_metadata.status,
                "model_run_id": model_metadata.run_id,
                "model_registry_id": model_metadata.model_registry_id,
                "model_path": str(model_metadata.model_path),
                "predicted_category": str(pred),
                "confidence": quality.confidence,
                "confidence_level": quality.confidence_level,
                "is_low_confidence": quality.is_low_confidence,
                "top_predictions": json.dumps(
                    quality.top_predictions,
                    ensure_ascii=False,
                ),
            }
        )

    insert_sql = text("""
        INSERT INTO model_predictions (
            job_post_id,
            prediction_source,
            model_name,
            model_version,
            model_run_id,
            model_registry_id,
            model_path,
            predicted_category,
            confidence,
            confidence_level,
            is_low_confidence,
            top_predictions
        )
        VALUES (
            :job_post_id,
            :prediction_source,
            :model_name,
            :model_version,
            :model_run_id,
            :model_registry_id,
            :model_path,
            :predicted_category,
            :confidence,
            :confidence_level,
            :is_low_confidence,
            CAST(:top_predictions AS jsonb)
        )
    """)

    with engine.begin() as conn:
        # API 예측 로그는 보존하고, batch inference 결과만 새로 만든다.
        conn.execute(
            text("""
                DELETE FROM model_predictions
                WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH'
            """)
        )

        if prediction_rows:
            conn.execute(insert_sql, prediction_rows)

    print(f"Inserted batch predictions: {len(prediction_rows)}")

    if prediction_rows:
        confidence_values = [
            row["confidence"]
            for row in prediction_rows
            if row["confidence"] is not None
        ]

        low_confidence_count = sum(
            1
            for row in prediction_rows
            if row["is_low_confidence"] is True
        )

        avg_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        print()
        print("[Batch Prediction Quality]")
        print(f"prediction_count     : {len(prediction_rows)}")
        print(f"avg_confidence       : {avg_confidence:.4f}")
        print(f"low_confidence_count : {low_confidence_count}")
        print(
            "low_confidence_ratio : "
            f"{low_confidence_count / len(prediction_rows):.4f}"
        )


if __name__ == "__main__":
    main()