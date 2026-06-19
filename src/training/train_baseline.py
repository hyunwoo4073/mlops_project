# import os
# import joblib
# import pandas as pd
# import mlflow
# import mlflow.sklearn

# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.linear_model import LogisticRegression
# from sklearn.pipeline import Pipeline
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import accuracy_score, f1_score, classification_report


# DATA_PATH = "data/processed/cleaned_jobs.csv"
# MODEL_PATH = "models/job_classifier.pkl"


# def main():
#     if not os.path.exists(DATA_PATH):
#         raise FileNotFoundError(
#             f"Processed file not found: {DATA_PATH}. Run preprocess.py first."
#         )

#     df = pd.read_csv(DATA_PATH)
#     df = df[df["job_category"] != "Unknown"].copy()

#     if len(df) < 5:
#         raise ValueError("Training data is too small.")

#     X = df["text_for_model"]
#     y = df["job_category"]

#     # 현재 샘플 데이터가 작기 때문에 stratify는 일단 제외
#     X_train, X_test, y_train, y_test = train_test_split(
#         X,
#         y,
#         test_size=0.3,
#         random_state=42,
#         stratify=y,
#     )

#     model = Pipeline(
#         [
#             (
#                 "tfidf",
#                 TfidfVectorizer(
#                     max_features=5000,
#                     ngram_range=(1, 2),
#                 ),
#             ),
#             (
#                 "clf",
#                 LogisticRegression(
#                     max_iter=1000,
#                 ),
#             ),
#         ]
#     )

#     mlflow.set_tracking_uri("sqlite:///mlflow.db")
#     mlflow.set_experiment("jobskill-classifier")

#     with mlflow.start_run():
#         model.fit(X_train, y_train)

#         preds = model.predict(X_test)

#         acc = accuracy_score(y_test, preds)
#         f1 = f1_score(y_test, preds, average="weighted")

#         print("accuracy:", acc)
#         print("f1_weighted:", f1)
#         print()
#         print(classification_report(y_test, preds))

#         mlflow.log_param("model_type", "tfidf_logistic_regression")
#         mlflow.log_param("max_features", 5000)
#         mlflow.log_param("ngram_range", "1,2")
#         mlflow.log_metric("accuracy", acc)
#         mlflow.log_metric("f1_weighted", f1)

#         mlflow.sklearn.log_model(model, "model")

#         os.makedirs("models", exist_ok=True)
#         joblib.dump(model, MODEL_PATH)

#         print(f"Saved model: {MODEL_PATH}")


# if __name__ == "__main__":
#     main()


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
        raise ValueError(
            "No training data found. Run preprocess_db.py first."
        )

    if len(df) < 5:
        raise ValueError("Training data is too small.")

    print("Training data count:", len(df))
    print()
    print(df["job_category"].value_counts())
    print()

    X = df["text_for_model"]
    y = df["job_category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
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

    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("jobskill-classifier")

    with mlflow.start_run():
        model.fit(X_train, y_train)

        preds = model.predict(X_test)

        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average="weighted")

        print("accuracy:", acc)
        print("f1_weighted:", f1)
        print()
        print(classification_report(y_test, preds))

        mlflow.log_param("data_source", "postgresql")
        mlflow.log_param("model_type", "tfidf_logistic_regression")
        mlflow.log_param("max_features", 5000)
        mlflow.log_param("ngram_range", "1,2")
        mlflow.log_param("test_size", 0.3)

        mlflow.log_metric("training_rows", len(df))
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_weighted", f1)

        mlflow.sklearn.log_model(model, "model")

        os.makedirs("models", exist_ok=True)
        joblib.dump(model, MODEL_PATH)

        print(f"Saved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()