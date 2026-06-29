from src.preprocessing.label_jobs import label_job, get_label_scores


def test_label_job_data_engineer():
    label = label_job(
        title="데이터 엔지니어 채용",
        description="Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
    )

    assert label == "Data Engineer"


def test_label_job_backend_engineer():
    label = label_job(
        title="백엔드 개발자 채용",
        description="Java Spring Boot REST API 서버 개발 경험이 필요합니다.",
    )

    assert label == "Backend Engineer"


def test_label_job_ml_engineer():
    label = label_job(
        title="ML 엔지니어 채용",
        description="TensorFlow PyTorch MLflow 기반 모델 학습과 서빙 경험이 필요합니다.",
    )

    assert label == "ML Engineer"


def test_label_job_devops_engineer():
    label = label_job(
        title="DevOps Engineer",
        description="Kubernetes Docker Prometheus Grafana CI/CD 운영 경험이 필요합니다.",
    )

    assert label == "DevOps Engineer"


def test_label_job_data_analyst():
    label = label_job(
        title="데이터 분석가",
        description="SQL Tableau dashboard KPI 분석 업무를 담당합니다.",
    )

    assert label == "Data Analyst"


def test_label_job_unknown_when_no_signal():
    label = label_job(
        title="운영 담당자 채용",
        description="다양한 업무를 수행하고 여러 부서와 협업할 인재를 찾습니다.",
    )

    assert label == "Unknown"


def test_get_label_scores_returns_sorted_scores():
    scores = get_label_scores(
        title="데이터 엔지니어 채용",
        description="Airflow Kafka Spark 데이터 파이프라인 업무",
    )

    assert list(scores.keys())[0] == "Data Engineer"
    assert scores["Data Engineer"] > 0
