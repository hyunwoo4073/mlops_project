from __future__ import annotations

import re
from collections import defaultdict


UNKNOWN_LABEL = "Unknown"


CATEGORY_KEYWORDS: dict[str, dict[str, int]] = {
    "Data Engineer": {
        "data engineer": 5,
        "데이터 엔지니어": 5,
        "data pipeline": 4,
        "데이터 파이프라인": 4,
        "etl": 4,
        "elt": 4,
        "airflow": 4,
        "spark": 4,
        "pyspark": 4,
        "hadoop": 4,
        "hdfs": 4,
        "kafka": 4,
        "data warehouse": 3,
        "데이터 웨어하우스": 3,
        "lakehouse": 3,
        "data lake": 3,
        "데이터 레이크": 3,
        "batch": 2,
        "streaming": 2,
        "스트리밍": 2,
        "sql": 2,
        "python": 1,
    },
    "Backend Engineer": {
        "backend": 5,
        "back-end": 5,
        "백엔드": 5,
        "server": 4,
        "서버": 4,
        "api": 4,
        "rest api": 4,
        "spring": 4,
        "spring boot": 4,
        "java": 3,
        "kotlin": 3,
        "node.js": 3,
        "nodejs": 3,
        "fastapi": 3,
        "django": 3,
        "flask": 3,
        "msa": 3,
        "microservice": 3,
        "마이크로서비스": 3,
        "mysql": 2,
        "postgresql": 2,
        "redis": 2,
        "database": 2,
        "db": 1,
    },
    "ML Engineer": {
        "ml engineer": 5,
        "machine learning engineer": 5,
        "머신러닝 엔지니어": 5,
        "ml": 4,
        "machine learning": 4,
        "머신러닝": 4,
        "deep learning": 4,
        "딥러닝": 4,
        "tensorflow": 4,
        "pytorch": 4,
        "scikit-learn": 4,
        "sklearn": 4,
        "model training": 4,
        "모델 학습": 4,
        "model serving": 4,
        "모델 서빙": 4,
        "mlflow": 3,
        "kubeflow": 3,
        "feature engineering": 3,
        "피처": 2,
        "inference": 2,
        "추론": 2,
        "ai": 2,
        "python": 1,
    },
    "DevOps Engineer": {
        "devops": 5,
        "데브옵스": 5,
        "sre": 5,
        "site reliability": 5,
        "kubernetes": 4,
        "k8s": 4,
        "docker": 4,
        "ci/cd": 4,
        "cicd": 4,
        "jenkins": 3,
        "github actions": 3,
        "gitlab ci": 3,
        "terraform": 3,
        "ansible": 3,
        "helm": 3,
        "prometheus": 3,
        "grafana": 3,
        "monitoring": 3,
        "모니터링": 3,
        "linux": 2,
        "infra": 2,
        "infrastructure": 2,
        "인프라": 2,
        "cloud": 2,
        "aws": 2,
    },
    "Data Analyst": {
        "data analyst": 5,
        "데이터 분석가": 5,
        "analyst": 4,
        "analysis": 4,
        "analytics": 4,
        "분석": 4,
        "dashboard": 4,
        "대시보드": 4,
        "bi": 4,
        "tableau": 4,
        "power bi": 4,
        "looker": 4,
        "excel": 3,
        "spreadsheet": 3,
        "sql": 3,
        "kpi": 3,
        "metric": 3,
        "지표": 3,
        "report": 2,
        "리포트": 2,
        "visualization": 2,
        "시각화": 2,
        "python": 1,
    },
}


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""

    normalized = text.lower()
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def count_keyword(text: str, keyword: str) -> int:
    keyword = normalize_text(keyword)

    if not keyword:
        return 0

    # 짧은 단어는 단어 경계를 보고, 긴 phrase는 단순 포함 횟수로 계산한다.
    if len(keyword) <= 3 and keyword.isalpha():
        pattern = rf"\b{re.escape(keyword)}\b"
        return len(re.findall(pattern, text))

    return text.count(keyword)


def score_category(text: str, keywords: dict[str, int]) -> int:
    score = 0

    for keyword, weight in keywords.items():
        matched_count = count_keyword(text, keyword)
        score += matched_count * weight

    return score


def label_job(title: str | None = None, description: str | None = None) -> str:
    title_text = normalize_text(title)
    description_text = normalize_text(description)

    # title에 등장한 키워드는 description보다 중요하게 본다.
    combined_text = f"{title_text} {title_text} {description_text}".strip()

    if not combined_text:
        return UNKNOWN_LABEL

    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = score_category(combined_text, keywords)

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    # 너무 약한 매칭은 Unknown 처리
    min_score = 2

    if best_score < min_score:
        return UNKNOWN_LABEL

    return best_category


def label_job_from_text(text: str | None = None) -> str:
    return label_job(title="", description=text)


def label_job_category(title: str | None = None, description: str | None = None) -> str:
    # preprocess_db.py에서 기존에 이 함수명을 쓰고 있을 경우를 위한 alias
    return label_job(title=title, description=description)


def classify_job_category(title: str | None = None, description: str | None = None) -> str:
    # 다른 이름으로 import했을 경우를 대비한 alias
    return label_job(title=title, description=description)


def get_label_scores(title: str | None = None, description: str | None = None) -> dict[str, int]:
    title_text = normalize_text(title)
    description_text = normalize_text(description)
    combined_text = f"{title_text} {title_text} {description_text}".strip()

    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = score_category(combined_text, keywords)

    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))


if __name__ == "__main__":
    samples = [
        {
            "title": "데이터 엔지니어 채용",
            "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
        },
        {
            "title": "백엔드 개발자 채용",
            "description": "Java Spring Boot REST API 서버 개발 경험이 필요합니다.",
        },
        {
            "title": "ML 엔지니어 채용",
            "description": "TensorFlow PyTorch MLflow 기반 모델 학습과 서빙 경험이 필요합니다.",
        },
        {
            "title": "DevOps Engineer",
            "description": "Kubernetes Docker Prometheus Grafana CI/CD 운영 경험이 필요합니다.",
        },
        {
            "title": "데이터 분석가",
            "description": "SQL Tableau dashboard KPI 분석 업무를 담당합니다.",
        },
    ]

    for sample in samples:
        label = label_job(sample["title"], sample["description"])
        scores = get_label_scores(sample["title"], sample["description"])

        print("\n---")
        print(f"title : {sample['title']}")
        print(f"label : {label}")
        print(f"scores: {scores}")