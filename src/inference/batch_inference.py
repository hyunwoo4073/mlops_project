import sys
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


MODEL_PATH = "models/job_classifier.pkl"


def main():
    engine = get_engine()

    model = joblib.load(MODEL_PATH)

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
                "model_name": "tfidf_logistic_regression",
                "model_version": "local",
                "predicted_category": str(pred),
                "confidence": float(confidence) if confidence is not None else None,
            }
        )

    insert_sql = text("""
        INSERT INTO model_predictions (
            job_post_id,
            model_name,
            model_version,
            predicted_category,
            confidence
        )
        VALUES (
            :job_post_id,
            :model_name,
            :model_version,
            :predicted_category,
            :confidence
        )
    """)

    with engine.begin() as conn:
        # MVP 단계에서는 batch inference 결과를 매번 새로 만든다.
        conn.execute(text("TRUNCATE TABLE model_predictions RESTART IDENTITY"))
        conn.execute(insert_sql, prediction_rows)

    print(f"Inserted batch predictions: {len(prediction_rows)}")


if __name__ == "__main__":
    main()
