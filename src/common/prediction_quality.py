from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PredictionQuality:
    confidence: float | None
    confidence_level: str
    is_low_confidence: bool
    top_predictions: list[dict]


def get_confidence_level(confidence: float | None) -> str:
    if confidence is None:
        return "UNKNOWN"

    if confidence >= 0.8:
        return "HIGH"

    if confidence >= 0.6:
        return "MEDIUM"

    return "LOW"


def build_prediction_quality(model, texts: list[str]) -> list[PredictionQuality]:
    top_k = int(os.getenv("PREDICTION_TOP_K", "3"))
    low_confidence_threshold = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.6"))

    if not hasattr(model, "predict_proba"):
        return [
            PredictionQuality(
                confidence=None,
                confidence_level="UNKNOWN",
                is_low_confidence=False,
                top_predictions=[],
            )
            for _ in texts
        ]

    probas = model.predict_proba(texts)
    classes = list(model.classes_)

    results: list[PredictionQuality] = []

    for proba in probas:
        ranked = sorted(
            zip(classes, proba),
            key=lambda item: item[1],
            reverse=True,
        )

        top_predictions = [
            {
                "category": str(category),
                "probability": round(float(probability), 4),
            }
            for category, probability in ranked[:top_k]
        ]

        confidence = float(ranked[0][1])
        confidence_level = get_confidence_level(confidence)

        results.append(
            PredictionQuality(
                confidence=confidence,
                confidence_level=confidence_level,
                is_low_confidence=confidence < low_confidence_threshold,
                top_predictions=top_predictions,
            )
        )

    return results
