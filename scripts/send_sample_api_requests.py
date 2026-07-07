from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "10"))


SAMPLE_REQUESTS: list[dict[str, Any]] = [
    {
        "title": "Data Engineer",
        "description": (
            "Build data pipelines using Python, SQL, Airflow, Kafka, Spark, "
            "and cloud-based data platforms."
        ),
        "job_post_id": None,
    },
    {
        "title": "Backend Engineer",
        "description": (
            "Develop REST APIs and backend services using Java, Spring Boot, "
            "MySQL, Redis, Docker, and Kubernetes."
        ),
        "job_post_id": None,
    },
    {
        "title": "Machine Learning Engineer",
        "description": (
            "Train and deploy machine learning models using Python, scikit-learn, "
            "MLflow, TensorFlow, and feature engineering pipelines."
        ),
        "job_post_id": None,
    },
    {
        "title": "DevOps Engineer",
        "description": (
            "Operate CI/CD pipelines, Docker containers, Kubernetes clusters, "
            "Prometheus monitoring, and infrastructure automation."
        ),
        "job_post_id": None,
    },
    {
        "title": "Data Analyst",
        "description": (
            "Analyze business data using SQL, Python, dashboards, statistics, "
            "BI tools, and reporting workflows."
        ),
        "job_post_id": None,
    },
]


def request_json(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{API_BASE_URL}{path}"

    response = requests.request(
        method=method,
        url=url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )

    response.raise_for_status()

    if not response.text:
        return {}

    return response.json()


def main() -> None:
    print()
    print("[Sample API Requests]")
    print(f"API_BASE_URL: {API_BASE_URL}")
    print()

    health = request_json("GET", "/")
    print("[Health]")
    print(json.dumps(health, indent=2, ensure_ascii=False))
    print()

    model = request_json("GET", "/model")
    print("[Model]")
    print(json.dumps(model, indent=2, ensure_ascii=False))
    print()

    for index, payload in enumerate(SAMPLE_REQUESTS, start=1):
        print(f"[Predict Request #{index}]")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        result = request_json(
            "POST",
            "/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        print("[Predict Response]")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()

    print("Sample API requests completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError as exc:
        print(f"Failed to connect to API server: {API_BASE_URL}", file=sys.stderr)
        print(exc, file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print("API request failed.", file=sys.stderr)
        print(exc, file=sys.stderr)

        if exc.response is not None:
            print(exc.response.text, file=sys.stderr)

        sys.exit(1)
