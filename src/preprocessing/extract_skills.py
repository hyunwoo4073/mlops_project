import re


SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "MongoDB",
    "Elasticsearch",
    "Hadoop",
    "Hive",
    "Spark",
    "Kafka",
    "Flink",
    "Airflow",
    "dbt",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "Linux",
    "Spring",
    "Spring Boot",
    "FastAPI",
    "Django",
    "Pandas",
    "PyTorch",
    "TensorFlow",
    "scikit-learn",
    "MLflow",
    "Tableau",
    "Excel",
    "Prometheus",
    "Grafana",
]


def extract_skills(text: str) -> list[str]:
    if text is None:
        return []

    text_lower = str(text).lower()
    found = []

    for skill in SKILLS:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.append(skill)

    return sorted(set(found))
