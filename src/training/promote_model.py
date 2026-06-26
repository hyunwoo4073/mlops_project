from __future__ import annotations

import os
import shutil
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient
from sqlalchemy import create_engine, text


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def get_latest_run_metrics() -> dict:
    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow",
    )
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "jobskill-classifier")

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise RuntimeError(f"MLflow experiment not found: {experiment_name}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )

    if not runs:
        raise RuntimeError(f"No MLflow runs found in experiment: {experiment_name}")

    latest_run = runs[0]
    metrics = latest_run.data.metrics

    if "accuracy" not in metrics:
        raise RuntimeError("accuracy metric not found in latest MLflow run")

    if "f1_weighted" not in metrics:
        raise RuntimeError("f1_weighted metric not found in latest MLflow run")

    return {
        "experiment_name": experiment_name,
        "run_id": latest_run.info.run_id,
        "accuracy": float(metrics["accuracy"]),
        "f1_weighted": float(metrics["f1_weighted"]),
    }


def get_current_best(conn, model_name: str):
    return conn.execute(
        text(
            """
            SELECT
                id,
                run_id,
                accuracy,
                f1_weighted,
                promoted_model_path,
                created_at
            FROM model_registry
            WHERE model_name = :model_name
              AND status = 'PROMOTED'
            ORDER BY f1_weighted DESC, accuracy DESC, created_at DESC
            LIMIT 1
            """
        ),
        {"model_name": model_name},
    ).mappings().first()


def insert_model_registry_record(
    conn,
    *,
    model_name: str,
    run_id: str,
    experiment_name: str,
    accuracy: float,
    f1_weighted: float,
    model_path: str,
    promoted_model_path: str,
    status: str,
    message: str,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO model_registry (
                model_name,
                run_id,
                experiment_name,
                accuracy,
                f1_weighted,
                model_path,
                promoted_model_path,
                status,
                message
            )
            VALUES (
                :model_name,
                :run_id,
                :experiment_name,
                :accuracy,
                :f1_weighted,
                :model_path,
                :promoted_model_path,
                :status,
                :message
            )
            """
        ),
        {
            "model_name": model_name,
            "run_id": run_id,
            "experiment_name": experiment_name,
            "accuracy": accuracy,
            "f1_weighted": f1_weighted,
            "model_path": model_path,
            "promoted_model_path": promoted_model_path,
            "status": status,
            "message": message,
        },
    )


def main() -> None:
    model_name = os.getenv("MODEL_NAME", "job_classifier")

    candidate_model_path = Path(
        os.getenv("MODEL_PATH", "models/job_classifier.pkl")
    )

    best_model_path = Path(
        os.getenv("BEST_MODEL_PATH", "models/best/job_classifier.pkl")
    )

    if not candidate_model_path.exists():
        raise FileNotFoundError(f"Candidate model not found: {candidate_model_path}")

    best_model_path.parent.mkdir(parents=True, exist_ok=True)

    latest = get_latest_run_metrics()

    database_url = get_database_url()
    engine = create_engine(database_url)

    with engine.begin() as conn:
        current_best = get_current_best(conn, model_name)

        should_promote = False

        if current_best is None:
            should_promote = True
            message = "No existing promoted model. Promoting current model."
        else:
            current_best_f1 = float(current_best["f1_weighted"] or 0.0)
            current_best_accuracy = float(current_best["accuracy"] or 0.0)

            latest_f1 = latest["f1_weighted"]
            latest_accuracy = latest["accuracy"]

            if latest_f1 > current_best_f1:
                should_promote = True
                message = (
                    f"Current model f1_weighted={latest_f1:.4f} "
                    f"is better than best f1_weighted={current_best_f1:.4f}."
                )
            elif latest_f1 == current_best_f1 and latest_accuracy > current_best_accuracy:
                should_promote = True
                message = (
                    f"Current model accuracy={latest_accuracy:.4f} "
                    f"is better than best accuracy={current_best_accuracy:.4f} "
                    f"with same f1_weighted."
                )
            else:
                message = (
                    f"Current model was not promoted. "
                    f"current f1_weighted={latest['f1_weighted']:.4f}, "
                    f"best f1_weighted={current_best_f1:.4f}, "
                    f"current accuracy={latest['accuracy']:.4f}, "
                    f"best accuracy={current_best_accuracy:.4f}."
                )

        if should_promote:
            shutil.copy2(candidate_model_path, best_model_path)
            status = "PROMOTED"
        else:
            status = "REJECTED"

        insert_model_registry_record(
            conn,
            model_name=model_name,
            run_id=latest["run_id"],
            experiment_name=latest["experiment_name"],
            accuracy=latest["accuracy"],
            f1_weighted=latest["f1_weighted"],
            model_path=str(candidate_model_path),
            promoted_model_path=str(best_model_path),
            status=status,
            message=message,
        )

    print("\n[Model Promotion Result]")
    print(f"model_name          : {model_name}")
    print(f"run_id              : {latest['run_id']}")
    print(f"accuracy            : {latest['accuracy']:.4f}")
    print(f"f1_weighted         : {latest['f1_weighted']:.4f}")
    print(f"candidate_model_path: {candidate_model_path}")
    print(f"best_model_path     : {best_model_path}")
    print(f"status              : {status}")
    print(f"message             : {message}")


if __name__ == "__main__":
    main()
