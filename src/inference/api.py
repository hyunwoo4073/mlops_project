import sys
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.append("src/preprocessing")

from clean_text import clean_text
from extract_skills import extract_skills


MODEL_PATH = "models/job_classifier.pkl"

app = FastAPI(title="JobSkill MLOps API")

model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    title: str
    description: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    cleaned_title = clean_text(req.title)
    cleaned_description = clean_text(req.description)

    text = cleaned_title + " " + cleaned_description

    pred = model.predict([text])[0]

    confidence = None
    if hasattr(model, "predict_proba"):
        confidence = float(model.predict_proba([text])[0].max())

    skills = extract_skills(text)

    return {
        "job_category": pred,
        "confidence": confidence,
        "skills": skills,
    }
