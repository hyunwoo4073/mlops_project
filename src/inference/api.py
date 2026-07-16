import json
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any
import os

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from fastapi.responses import Response, HTMLResponse, PlainTextResponse
import markdown as markdown_lib
from src.monitoring.prometheus_metrics import build_metrics_text

# 프로젝트 루트를 import path에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.common.model_registry import ModelMetadata, get_current_model_metadata
from src.common.prediction_quality import build_prediction_quality
from src.preprocessing.clean_text import clean_text
from src.preprocessing.extract_skills import extract_skills

from datetime import datetime
from typing import Any



app = FastAPI(title="JobSkill MLOps API")

DEFAULT_RUNBOOK_DIR = Path(__file__).resolve().parents[2] / "docs" / "runbooks"
RUNBOOK_DIR = Path(os.getenv("RUNBOOK_DIR", str(DEFAULT_RUNBOOK_DIR))).resolve()

engine = get_engine()

PREDICTION_SOURCE_API = "API"

class AlertmanagerAlert(BaseModel):
    status: str
    labels: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhookPayload(BaseModel):
    receiver: str | None = None
    status: str
    alerts: list[AlertmanagerAlert] = Field(default_factory=list)
    groupLabels: dict[str, Any] = Field(default_factory=dict)
    commonLabels: dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: dict[str, Any] = Field(default_factory=dict)
    externalURL: str | None = None
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = None


def parse_alertmanager_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
    top_predictions: list[dict] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    prediction_id: int | None
    prediction_source: str | None = None
    api_log_id: int | None = None

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


def check_database_ready() -> dict:
    try:
        engine = get_engine()

        with engine.begin() as conn:
            result = conn.execute(text("SELECT 1")).scalar()

        return {
            "status": "ok",
            "result": result,
        }

    except Exception as exc:
        return {
            "status": "fail",
            "error": str(exc),
        }

def check_promoted_model_ready() -> dict:
    try:
        engine = get_engine()

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        id,
                        model_name,
                        status,
                        promoted_model_path,
                        created_at
                    FROM model_registry
                    WHERE status = 'PROMOTED'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()

        if row is None:
            return {
                "status": "fail",
                "reason": "No PROMOTED model found in model_registry.",
            }

        promoted_model_path = row.get("promoted_model_path")

        if not promoted_model_path:
            return {
                "status": "fail",
                "reason": "PROMOTED model exists but promoted_model_path is empty.",
                "model_registry_id": row.get("id"),
            }

        model_path = Path(promoted_model_path)

        if not model_path.exists():
            return {
                "status": "fail",
                "reason": "Promoted model file does not exist.",
                "model_registry_id": row.get("id"),
                "promoted_model_path": promoted_model_path,
            }

        return {
            "status": "ok",
            "model_registry_id": row.get("id"),
            "model_name": row.get("model_name"),
            "promoted_model_path": promoted_model_path,
            "created_at": str(row.get("created_at")),
        }

    except Exception as exc:
        return {
            "status": "fail",
            "error": str(exc),
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

@app.get("/metrics")
def metrics():
    return Response(
        content=build_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )

@app.post("/alertmanager/webhook")
def receive_alertmanager_webhook(payload: AlertmanagerWebhookPayload):
    engine = get_engine()
    inserted_count = 0
    raw_payload = payload.model_dump(mode="json")

    with engine.begin() as conn:
        for alert in payload.alerts:
            labels = alert.labels
            annotations = alert.annotations

            conn.execute(
                text(
                    """
                    INSERT INTO alert_events (
                        receiver,
                        status,
                        alert_name,
                        severity,
                        service,
                        instance,
                        fingerprint,
                        starts_at,
                        ends_at,
                        generator_url,
                        summary,
                        description,
                        labels,
                        annotations,
                        raw_payload
                    )
                    VALUES (
                        :receiver,
                        :status,
                        :alert_name,
                        :severity,
                        :service,
                        :instance,
                        :fingerprint,
                        :starts_at,
                        :ends_at,
                        :generator_url,
                        :summary,
                        :description,
                        CAST(:labels AS jsonb),
                        CAST(:annotations AS jsonb),
                        CAST(:raw_payload AS jsonb)
                    )
                    """
                ),
                {
                    "receiver": payload.receiver,
                    "status": alert.status,
                    "alert_name": labels.get("alertname"),
                    "severity": labels.get("severity"),
                    "service": labels.get("service"),
                    "instance": labels.get("instance"),
                    "fingerprint": alert.fingerprint,
                    "starts_at": parse_alertmanager_timestamp(alert.startsAt),
                    "ends_at": parse_alertmanager_timestamp(alert.endsAt),
                    "generator_url": alert.generatorURL,
                    "summary": annotations.get("summary"),
                    "description": annotations.get("description"),
                    "labels": json.dumps(labels, ensure_ascii=False),
                    "annotations": json.dumps(annotations, ensure_ascii=False),
                    "raw_payload": json.dumps(raw_payload, ensure_ascii=False),
                },
            )
            inserted_count += 1

            conn.execute(
                text(
                    """
                    INSERT INTO alert_current_states (
                        fingerprint,
                        status,
                        alert_name,
                        severity,
                        service,
                        instance,
                        starts_at,
                        ends_at,
                        last_received_at,
                        summary,
                        description,
                        labels,
                        annotations,
                        updated_at
                    )
                    VALUES (
                        :fingerprint,
                        :status,
                        :alert_name,
                        :severity,
                        :service,
                        :instance,
                        :starts_at,
                        :ends_at,
                        CURRENT_TIMESTAMP,
                        :summary,
                        :description,
                        CAST(:labels AS jsonb),
                        CAST(:annotations AS jsonb),
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (fingerprint)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        alert_name = EXCLUDED.alert_name,
                        severity = EXCLUDED.severity,
                        service = EXCLUDED.service,
                        instance = EXCLUDED.instance,
                        starts_at = EXCLUDED.starts_at,
                        ends_at = EXCLUDED.ends_at,
                        last_received_at = CURRENT_TIMESTAMP,
                        summary = EXCLUDED.summary,
                        description = EXCLUDED.description,
                        labels = EXCLUDED.labels,
                        annotations = EXCLUDED.annotations,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "fingerprint": alert.fingerprint,
                    "status": alert.status,
                    "alert_name": labels.get("alertname"),
                    "severity": labels.get("severity"),
                    "service": labels.get("service"),
                    "instance": labels.get("instance"),
                    "starts_at": parse_alertmanager_timestamp(alert.startsAt),
                    "ends_at": parse_alertmanager_timestamp(alert.endsAt),
                    "summary": annotations.get("summary"),
                    "description": annotations.get("description"),
                    "labels": json.dumps(labels, ensure_ascii=False),
                    "annotations": json.dumps(annotations, ensure_ascii=False),
                },
            )
    return {
        "status": "ok",
        "inserted_alert_events": inserted_count,
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


def insert_api_prediction_log(
    *,
    req: PredictRequest,
    prediction_id: int | None,
    response_payload: dict | None,
    metadata: ModelMetadata | None,
    status: str,
    error_message: str | None,
    latency_ms: float,
) -> int:
    insert_sql = text("""
        INSERT INTO api_prediction_logs (
            prediction_id,
            request_title,
            request_description,
            request_job_post_id,

            response_category,
            response_confidence,
            response_confidence_level,
            response_is_low_confidence,
            response_top_predictions,
            response_skills,

            model_name,
            model_run_id,
            model_registry_id,
            model_path,

            status,
            error_message,
            latency_ms
        )
        VALUES (
            :prediction_id,
            :request_title,
            :request_description,
            :request_job_post_id,

            :response_category,
            :response_confidence,
            :response_confidence_level,
            :response_is_low_confidence,
            CAST(:response_top_predictions AS jsonb),
            CAST(:response_skills AS jsonb),

            :model_name,
            :model_run_id,
            :model_registry_id,
            :model_path,

            :status,
            :error_message,
            :latency_ms
        )
        RETURNING id
    """)

    response_payload = response_payload or {}

    with engine.begin() as conn:
        result = conn.execute(
            insert_sql,
            {
                "prediction_id": prediction_id,
                "request_title": req.title,
                "request_description": req.description,
                "request_job_post_id": req.job_post_id,

                "response_category": response_payload.get("job_category"),
                "response_confidence": response_payload.get("confidence"),
                "response_confidence_level": response_payload.get("confidence_level"),
                "response_is_low_confidence": response_payload.get("is_low_confidence"),
                "response_top_predictions": json.dumps(
                    response_payload.get("top_predictions") or [],
                    ensure_ascii=False,
                ),
                "response_skills": json.dumps(
                    response_payload.get("skills") or [],
                    ensure_ascii=False,
                ),

                "model_name": metadata.model_name if metadata else None,
                "model_run_id": metadata.run_id if metadata else None,
                "model_registry_id": metadata.model_registry_id if metadata else None,
                "model_path": str(metadata.model_path) if metadata else None,

                "status": status,
                "error_message": error_message,
                "latency_ms": latency_ms,
            },
        )

        return result.scalar_one()


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    started_at = time.perf_counter()

    metadata = None
    prediction_id = None
    response_payload = None

    try:
        model, metadata = model_store.load_if_needed()

        cleaned_title = clean_text(req.title)
        cleaned_description = clean_text(req.description)

        text_for_model = f"{cleaned_title} {cleaned_description}".strip()

        pred = model.predict([text_for_model])[0]

        quality = build_prediction_quality(model, [text_for_model])[0]
        confidence = quality.confidence

        skills = extract_skills(text_for_model)

        insert_prediction_sql = text("""
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
            RETURNING id
        """)

        with engine.begin() as conn:
            result = conn.execute(
                insert_prediction_sql,
                {
                    "job_post_id": req.job_post_id,
                    "prediction_source": PREDICTION_SOURCE_API,
                    "model_name": metadata.model_name,
                    "model_version": metadata.run_id or metadata.status,
                    "model_run_id": metadata.run_id,
                    "model_registry_id": metadata.model_registry_id,
                    "model_path": str(metadata.model_path),
                    "predicted_category": str(pred),
                    "confidence": confidence,
                    "confidence_level": quality.confidence_level,
                    "is_low_confidence": quality.is_low_confidence,
                    "top_predictions": json.dumps(
                        quality.top_predictions,
                        ensure_ascii=False,
                    ),
                },
            )

            prediction_id = result.scalar_one()

        response_payload = {
            "job_category": str(pred),
            "confidence": confidence,
            "confidence_level": quality.confidence_level,
            "is_low_confidence": quality.is_low_confidence,
            "top_predictions": quality.top_predictions,
            "skills": skills,
            "prediction_id": prediction_id,
            "prediction_source": PREDICTION_SOURCE_API,
            "model_name": metadata.model_name,
            "model_run_id": metadata.run_id,
            "model_registry_id": metadata.model_registry_id,
            "model_path": str(metadata.model_path),
        }

        latency_ms = (time.perf_counter() - started_at) * 1000

        api_log_id = insert_api_prediction_log(
            req=req,
            prediction_id=prediction_id,
            response_payload=response_payload,
            metadata=metadata,
            status="SUCCESS",
            error_message=None,
            latency_ms=latency_ms,
        )

        response_payload["api_log_id"] = api_log_id

        return response_payload

    except Exception as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        try:
            insert_api_prediction_log(
                req=req,
                prediction_id=prediction_id,
                response_payload=response_payload,
                metadata=metadata,
                status="FAILED",
                error_message=f"{type(exc).__name__}: {exc}",
                latency_ms=latency_ms,
            )
        except Exception as log_exc:
            print(
                "Failed to write api_prediction_logs: "
                f"{type(log_exc).__name__}: {log_exc}"
            )

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {type(exc).__name__}: {exc}",
        )

DEFAULT_RUNBOOK_DIR = Path(__file__).resolve().parents[2] / "docs" / "runbooks"
RUNBOOK_DIR = Path(os.getenv("RUNBOOK_DIR", str(DEFAULT_RUNBOOK_DIR))).resolve()


def get_runbook_path(filename: str) -> Path:
    if Path(filename).name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid runbook filename.",
        )

    if not filename.endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="Only markdown runbooks are supported.",
        )

    runbook_path = (RUNBOOK_DIR / filename).resolve()

    try:
        runbook_path.relative_to(RUNBOOK_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid runbook path.",
        ) from exc

    if not runbook_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Runbook not found: {filename}",
        )

    return runbook_path


@app.get("/runbooks")
def list_runbooks():
    if not RUNBOOK_DIR.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Runbook directory does not exist: {RUNBOOK_DIR}",
        )

    runbooks = sorted(RUNBOOK_DIR.glob("*.md"))

    return {
        "runbook_dir": str(RUNBOOK_DIR),
        "runbooks": [
            {
                "filename": runbook.name,
                "url": f"/runbooks/{runbook.name}",
                "raw_url": f"/runbooks/{runbook.name}/raw",
            }
            for runbook in runbooks
        ],
    }


@app.get("/runbooks/{filename}", response_class=HTMLResponse)
def get_runbook(filename: str):
    runbook_path = get_runbook_path(filename)
    markdown_text = runbook_path.read_text(encoding="utf-8")

    rendered_body = markdown_lib.markdown(
        markdown_text,
        extensions=[
            "fenced_code",
            "tables",
            "toc",
        ],
    )

    html = f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{filename}</title>
  <style>
    body {{
      max-width: 960px;
      margin: 40px auto;
      padding: 0 24px 64px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.7;
      color: #1f2937;
      background: #f9fafb;
    }}

    .container {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      padding: 32px 40px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}

    h1 {{
      margin-top: 0;
      padding-bottom: 12px;
      border-bottom: 2px solid #e5e7eb;
      color: #111827;
    }}

    h2 {{
      margin-top: 36px;
      padding-bottom: 6px;
      border-bottom: 1px solid #e5e7eb;
      color: #111827;
    }}

    p {{
      margin: 12px 0;
    }}

    ul {{
      padding-left: 24px;
    }}

    li {{
      margin: 6px 0;
    }}

    code {{
      padding: 2px 6px;
      border-radius: 6px;
      background: #f3f4f6;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.92em;
    }}

    pre {{
      overflow-x: auto;
      padding: 16px;
      border-radius: 12px;
      background: #111827;
      color: #f9fafb;
      line-height: 1.5;
    }}

    pre code {{
      padding: 0;
      background: transparent;
      color: inherit;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
    }}

    th, td {{
      border: 1px solid #e5e7eb;
      padding: 10px 12px;
      text-align: left;
    }}

    th {{
      background: #f3f4f6;
    }}

    a {{
      color: #2563eb;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .meta {{
      margin-bottom: 24px;
      font-size: 14px;
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="meta">Runbook: {filename}</div>
    {rendered_body}
  </div>
</body>
</html>
"""

    return HTMLResponse(content=html)


@app.get("/runbooks/{filename}/raw", response_class=PlainTextResponse)
def get_runbook_raw(filename: str):
    runbook_path = get_runbook_path(filename)

    return PlainTextResponse(
        runbook_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "jobskill-api",
    }

@app.get("/ready")
def readiness_check():
    database_status = check_database_ready()
    model_status = check_promoted_model_ready()

    checks = {
        "database": database_status,
        "promoted_model": model_status,
    }

    ready = all(check["status"] == "ok" for check in checks.values())

    response = {
        "status": "ready" if ready else "not_ready",
        "service": "jobskill-api",
        "checks": checks,
    }

    if not ready:
        raise HTTPException(
            status_code=503,
            detail=response,
        )

    return response