import os
import sys
from pathlib import Path

import joblib
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report


# 프로젝트 루트를 import path에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


MODEL_PATH = "models/job_classifier.pkl"


def main():
    engine = get_engine()

    query = """
        SELECT
            id,
            text_for_model,
            job_category
        FROM cleaned_job_posts
        WHERE job_category IS NOT NULL
          AND job_category != 'Unknown'
          AND text_for_model IS NOT NULL
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError("No training data found. Run preprocess_db.py first.")

    if len(df) < 5:
        raise ValueError("Training data is too small.")

    print("Training data count before filtering:", len(df))
    print()
    print("[Class distribution before filtering]")
    print(df["job_category"].value_counts())
    print()

    # stratified train_test_split은 클래스별 최소 2건 이상 필요하다.
    # crawler_only 모드에서는 특정 클래스가 1건만 들어올 수 있으므로,
    # 학습이 불가능한 rare class는 제외한다.
    min_samples_per_class = int(os.getenv("MIN_SAMPLES_PER_CLASS", "2"))

    class_counts = df["job_category"].value_counts()
    rare_classes = class_counts[class_counts < min_samples_per_class]

    if not rare_classes.empty:
        print("[Rare classes excluded from training]")
        print(rare_classes)
        print()

        df = df[~df["job_category"].isin(rare_classes.index)].copy()

    if df.empty:
        raise ValueError("No training data left after rare-class filtering.")

    class_counts_after_filter = df["job_category"].value_counts()

    if class_counts_after_filter.shape[0] < 2:
        raise ValueError(
            "Training requires at least 2 classes after rare-class filtering. "
            f"Current classes: {class_counts_after_filter.to_dict()}"
        )

    if len(df) < 5:
        raise ValueError(
            f"Training data is too small after rare-class filtering. rows={len(df)}"
        )

    print("Training data count after filtering:", len(df))
    print()
    print("[Class distribution after filtering]")
    print(class_counts_after_filter)
    print()

    X = df["text_for_model"]
    y = df["job_category"]

    # test set에는 각 class가 최소 1건씩 들어갈 수 있어야 한다.
    # 그래서 test_count를 class 개수 이상으로 보정한다.
    test_size = float(os.getenv("TEST_SIZE", "0.3"))

    num_classes = y.nunique()
    test_count = max(int(len(y) * test_size), num_classes)

    if test_count >= len(y):
        raise ValueError(
            "Not enough data for stratified split. "
            f"rows={len(y)}, classes={num_classes}, test_count={test_count}"
        )

    adjusted_test_size = test_count / len(y)

    print(f"train_test_split test_size: {adjusted_test_size:.4f}")
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=adjusted_test_size,
        random_state=42,
        stratify=y,
    )

    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 2),
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                ),
            ),
        ]
    )

    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "postgresql+psycopg2://jobskill:jobskill@localhost:5432/mlflow",
    )

    artifact_root = os.getenv("MLFLOW_ARTIFACT_ROOT", "./mlartifacts")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "jobskill-classifier")

    mlflow.set_tracking_uri(tracking_uri)

    experiment = mlflow.get_experiment_by_name(experiment_name)

    if experiment is None:
        mlflow.create_experiment(
            name=experiment_name,
            artifact_location=artifact_root,
        )

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        model.fit(X_train, y_train)

        preds = model.predict(X_test)

        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average="weighted")

        print("accuracy:", acc)
        print("f1_weighted:", f1)
        print()
        print(classification_report(y_test, preds, zero_division=0))

        mlflow.log_param("data_source", "postgresql")
        mlflow.log_param("model_type", "tfidf_logistic_regression")
        mlflow.log_param("max_features", 5000)
        mlflow.log_param("ngram_range", "1,2")
        mlflow.log_param("test_size", adjusted_test_size)
        mlflow.log_param("min_samples_per_class", min_samples_per_class)
        mlflow.log_param(
            "excluded_rare_classes",
            ",".join(rare_classes.index.tolist()) if not rare_classes.empty else "",
        )

        mlflow.log_metric("training_rows_before_filtering", len(class_counts.index) and int(class_counts.sum()))
        mlflow.log_metric("training_rows", len(df))
        mlflow.log_metric("num_classes", num_classes)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_weighted", f1)

        mlflow.sklearn.log_model(model, "model")

        os.makedirs("models", exist_ok=True)
        joblib.dump(model, MODEL_PATH)

        print(f"Saved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()