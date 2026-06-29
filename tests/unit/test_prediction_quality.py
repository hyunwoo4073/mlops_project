from src.common.prediction_quality import (
    build_prediction_quality,
    get_confidence_level,
)


class FakeModel:
    classes_ = ["Data Engineer", "Backend Engineer", "ML Engineer"]

    def predict_proba(self, texts):
        return [
            [0.85, 0.10, 0.05],
            [0.55, 0.30, 0.15],
        ]


class FakeModelWithoutProba:
    pass


def test_get_confidence_level_high():
    assert get_confidence_level(0.8) == "HIGH"
    assert get_confidence_level(0.95) == "HIGH"


def test_get_confidence_level_medium():
    assert get_confidence_level(0.6) == "MEDIUM"
    assert get_confidence_level(0.75) == "MEDIUM"


def test_get_confidence_level_low():
    assert get_confidence_level(0.59) == "LOW"


def test_get_confidence_level_unknown():
    assert get_confidence_level(None) == "UNKNOWN"


def test_build_prediction_quality_with_proba(monkeypatch):
    monkeypatch.setenv("PREDICTION_TOP_K", "2")
    monkeypatch.setenv("LOW_CONFIDENCE_THRESHOLD", "0.6")

    results = build_prediction_quality(
        model=FakeModel(),
        texts=["sample 1", "sample 2"],
    )

    assert len(results) == 2

    first = results[0]
    assert first.confidence == 0.85
    assert first.confidence_level == "HIGH"
    assert first.is_low_confidence is False
    assert first.top_predictions[0]["category"] == "Data Engineer"
    assert first.top_predictions[0]["probability"] == 0.85
    assert len(first.top_predictions) == 2

    second = results[1]
    assert second.confidence == 0.55
    assert second.confidence_level == "LOW"
    assert second.is_low_confidence is True
    assert second.top_predictions[0]["category"] == "Data Engineer"


def test_build_prediction_quality_without_proba():
    results = build_prediction_quality(
        model=FakeModelWithoutProba(),
        texts=["sample"],
    )

    assert len(results) == 1
    assert results[0].confidence is None
    assert results[0].confidence_level == "UNKNOWN"
    assert results[0].is_low_confidence is False
    assert results[0].top_predictions == []
