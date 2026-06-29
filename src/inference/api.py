import sys
from pathlib import Path
from threading import Lock
from typing import Any

import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text

import json
from src.common.prediction_quality import build_prediction_quality

# 프로젝트 루트를 import path에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.common.model_registry import ModelMetadata, get_current_model_metadata
from src.preprocessing.clean_text import clean_text
from src.preprocessing.extract_skills import extract_skills


app = FastAPI(title="JobSkill MLOps API")

engine = get_engine()


class ModelStore:
    def __init__(self):
        self._lock = Lock()
        self._model: Any | None = None
        self._metadata: ModelMetadata | None = None
        self._signature: str | None = None

    @staticmethod
    def _build_signature(metadata: ModelMetadata) -> str:
        model_path = Path(metadata.model_path)
        mtime = model_path.stat().st_mtime if model_path.exists() else 0

        return "|".join(
            [
                str(metadata.model_registry_id),
                str(metadata.run_id),
                str(metadata.model_path),
                str(mtime),
            ]
        )

    def load_if_needed(self, force: bool = False):
        current_metadata = get_current_model_metadata()
        current_signature = self._build_signature(current_metadata)

        with self._lock:
            if (
                force
                or self._model is None
                or self._metadata is None
                or self._signature != current_signature
            ):
                print("\n[Reload API Model]")
                print(f"model_name        : {current_metadata.model_name}")
                print(f"run_id            : {current_metadata.run_id}")
                print(f"model_registry_id : {current_metadata.model_registry_id}")
                print(f"model_path        : {current_metadata.model_path}")
                print(f"status            : {current_metadata.status}")

                self._model = joblib.load(current_metadata.model_path)
                self._metadata = current_metadata
                self._signature = current_signature

        return self._model, self._metadata

    def get_loaded_metadata(self):
        if self._metadata is None:
            self.load_if_needed()

        return self._metadata


model_store = ModelStore()


class PredictRequest(BaseModel):
    title: str
    description: str
    job_post_id: int | None = None


class PredictResponse(BaseModel):
    job_category: str
    confidence: float | None
    confidence_level: str | None = None
    is_low_confidence: bool | None = None
    top_predictions: list[dict] = []
    skills: list[str]
    prediction_id: int | None
    model_name: str | None = None
    model_run_id: str | None = None
    model_registry_id: int | None = None
    model_path: str | None = None


@app.on_event("startup")
def startup_event():
    model_store.load_if_needed(force=True)


@app.get("/")
def health_check():
    metadata = model_store.get_loaded_metadata()

    return {
        "status": "ok",
        "model_name": metadata.model_name,
        "model_run_id": metadata.run_id,
        "model_registry_id": metadata.model_registry_id,
        "model_path": str(metadata.model_path),
        "model_status": metadata.status,
    }


@app.get("/model")
def get_model_info():
    metadata = model_store.get_loaded_metadata()

    return {
        "model_name": metadata.model_name,
        "model_run_id": metadata.run_id,
        "model_registry_id": metadata.model_registry_id,
        "model_path": str(metadata.model_path),
        "model_status": metadata.status,
    }


@app.post("/reload-model")
def reload_model():
    _, metadata = model_store.load_if_needed(force=True)

    return {
        "status": "reloaded",
        "model_name": metadata.model_name,
        "model_run_id": metadata.run_id,
        "model_registry_id": metadata.model_registry_id,
        "model_path": str(metadata.model_path),
        "model_status": metadata.status,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    model, metadata = model_store.load_if_needed()

    cleaned_title = clean_text(req.title)
    cleaned_description = clean_text(req.description)

    text_for_model = cleaned_title + " " + cleaned_description

    pred = model.predict([text_for_model])[0]

    quality = build_prediction_quality(model, [text_for_model])[0]
    confidence = quality.confidence

    skills = extract_skills(text_for_model)

    insert_sql = text("""
        INSERT INTO model_predictions (
            job_post_id,
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
        RETURNING id
    """)
    with engine.begin() as conn:
        result = conn.execute(
            insert_sql,
            {
                "job_post_id": req.job_post_id,
                "model_name": metadata.model_name,
                "model_version": metadata.run_id or metadata.status,
                "model_run_id": metadata.run_id,
                "model_registry_id": metadata.model_registry_id,
                "model_path": str(metadata.model_path),
                "predicted_category": str(pred),
                "confidence": confidence,
                "confidence_level": quality.confidence_level,
                "is_low_confidence": quality.is_low_confidence,
                "top_predictions": json.dumps(quality.top_predictions, ensure_ascii=False),
            }
        )

        prediction_id = result.scalar_one()

    return {
        "job_category": str(pred),
        "confidence": confidence,
        "confidence_level": quality.confidence_level,
        "is_low_confidence": quality.is_low_confidence,
        "top_predictions": quality.top_predictions,
        "skills": skills,
        "prediction_id": prediction_id,
        "model_name": metadata.model_name,
        "model_run_id": metadata.run_id,
        "model_registry_id": metadata.model_registry_id,
        "model_path": str(metadata.model_path),
    }