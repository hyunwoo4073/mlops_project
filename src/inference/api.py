import sys
from pathlib import Path

import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text


# 프로젝트 루트를 import path에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.preprocessing.clean_text import clean_text
from src.preprocessing.extract_skills import extract_skills


MODEL_PATH = "models/job_classifier.pkl"

app = FastAPI(title="JobSkill MLOps API")

model = joblib.load(MODEL_PATH)
engine = get_engine()


class PredictRequest(BaseModel):
    title: str
    description: str
    job_post_id: int | None = None


class PredictResponse(BaseModel):
    job_category: str
    confidence: float | None
    skills: list[str]
    prediction_id: int | None


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    cleaned_title = clean_text(req.title)
    cleaned_description = clean_text(req.description)

    text_for_model = cleaned_title + " " + cleaned_description

    pred = model.predict([text_for_model])[0]

    confidence = None
    if hasattr(model, "predict_proba"):
        confidence = float(model.predict_proba([text_for_model])[0].max())

    skills = extract_skills(text_for_model)

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
        RETURNING id
    """)

    prediction_id = None

    with engine.begin() as conn:
        result = conn.execute(
            insert_sql,
            {
                "job_post_id": req.job_post_id,
                "model_name": "tfidf_logistic_regression",
                "model_version": "local",
                "predicted_category": pred,
                "confidence": confidence,
            },
        )

        prediction_id = result.scalar_one()

    return {
        "job_category": pred,
        "confidence": confidence,
        "skills": skills,
        "prediction_id": prediction_id,
    }