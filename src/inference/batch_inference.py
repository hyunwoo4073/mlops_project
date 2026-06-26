import sys
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text


# project root를 PYTHONPATH에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.common.model_registry import get_current_model_metadata


def main():
    engine = get_engine()

    # 현재 사용할 모델 metadata 조회
    # 우선순위:
    # 1. model_registry에서 PROMOTED 상태인 모델
    # 2. models/best/job_classifier.pkl
    # 3. models/job_classifier.pkl
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
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError("No cleaned job posts found. Run preprocess_db.py first.")

    texts = df["text_for_model"].tolist()

    preds = model.predict(texts)

    confidences = [None] * len(preds)
    if hasattr(model, "predict_proba"):
        probas = model.predict_proba(texts)
        confidences = probas.max(axis=1).tolist()

    prediction_rows = []

    for job_post_id, pred, confidence in zip(
        df["job_post_id"].tolist(),
        preds,
        confidences,
    ):
        prediction_rows.append(
            {
                "job_post_id": int(job_post_id),
                "model_name": model_metadata.model_name,
                "model_version": model_metadata.run_id or model_metadata.status,
                "model_run_id": model_metadata.run_id,
                "model_registry_id": model_metadata.model_registry_id,
                "model_path": str(model_metadata.model_path),
                "predicted_category": str(pred),
                "confidence": float(confidence) if confidence is not None else None,
            }
        )

    insert_sql = text("""
        INSERT INTO model_predictions (
            job_post_id,
            model_name,
            model_version,
            model_run_id,
            model_registry_id,
            model_path,
            predicted_category,
            confidence
        )
        VALUES (
            :job_post_id,
            :model_name,
            :model_version,
            :model_run_id,
            :model_registry_id,
            :model_path,
            :predicted_category,
            :confidence
        )
    """)

    with engine.begin() as conn:
        # MVP 단계에서는 batch inference 결과를 매번 새로 만든다.
        conn.execute(text("TRUNCATE TABLE model_predictions RESTART IDENTITY"))
        conn.execute(insert_sql, prediction_rows)

    print(f"\nInserted batch predictions: {len(prediction_rows)}")
    print(f"model_name        : {model_metadata.model_name}")
    print(f"model_run_id      : {model_metadata.run_id}")
    print(f"model_registry_id : {model_metadata.model_registry_id}")
    print(f"model_path        : {model_metadata.model_path}")


if __name__ == "__main__":
    main()