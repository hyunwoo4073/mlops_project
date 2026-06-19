import csv
import random
from pathlib import Path


OUTPUT_PATH = Path("data/raw/sample_jobs.csv")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


LOCATIONS = ["서울", "판교", "성남", "부산", "대전", "대구", "광주", "인천", "원격", "하이브리드"]

CAREERS = [
    "신입",
    "1년 이상",
    "2년 이상",
    "3년 이상",
    "4년 이상",
    "5년 이상",
    "7년 이상",
]


COMPANIES = [
    "A회사", "B테크", "C랩스", "D데이터", "E소프트",
    "F플랫폼", "G클라우드", "H인사이트", "I시스템즈", "JAI",
    "K커머스", "L핀테크", "M게임즈", "N모빌리티", "O헬스케어",
]


JOB_TEMPLATES = {
    "Data Engineer": {
        "titles": [
            "데이터 엔지니어 채용",
            "Data Engineer",
            "데이터 플랫폼 엔지니어",
            "데이터 파이프라인 개발자",
            "빅데이터 엔지니어",
            "ETL 파이프라인 개발자",
        ],
        "skills": [
            "Python", "SQL", "Airflow", "Spark", "Kafka", "Hadoop",
            "Hive", "PostgreSQL", "MySQL", "Docker", "Linux", "AWS",
            "Flink", "dbt",
        ],
        "sentences": [
            "대용량 데이터 파이프라인을 설계하고 운영합니다.",
            "배치 데이터 처리와 ETL 워크플로우를 개발합니다.",
            "데이터 품질을 관리하고 장애 발생 시 원인을 분석합니다.",
            "DW와 데이터 마트를 구성하고 분석 가능한 형태로 데이터를 제공합니다.",
            "로그 데이터 수집, 정제, 적재 프로세스를 자동화합니다.",
        ],
    },
    "Backend Engineer": {
        "titles": [
            "백엔드 개발자 채용",
            "Backend Engineer",
            "서버 개발자",
            "백엔드 서버 엔지니어",
            "API 서버 개발자",
            "Spring 백엔드 개발자",
        ],
        "skills": [
            "Java", "Spring", "Spring Boot", "MySQL", "PostgreSQL",
            "Redis", "Docker", "Kubernetes", "AWS", "Linux",
            "Kafka", "Elasticsearch",
        ],
        "sentences": [
            "대용량 트래픽을 처리하는 API 서버를 개발합니다.",
            "서비스 백엔드 아키텍처를 설계하고 운영합니다.",
            "데이터베이스 스키마를 설계하고 쿼리 성능을 개선합니다.",
            "캐시와 메시지 큐를 활용해 시스템 성능을 개선합니다.",
            "REST API와 내부 어드민 서비스를 개발합니다.",
        ],
    },
    "ML Engineer": {
        "titles": [
            "ML 엔지니어 채용",
            "Machine Learning Engineer",
            "머신러닝 엔지니어",
            "AI 엔지니어",
            "모델링 엔지니어",
            "추천 시스템 엔지니어",
        ],
        "skills": [
            "Python", "PyTorch", "TensorFlow", "scikit-learn", "MLflow",
            "Pandas", "SQL", "Docker", "FastAPI", "AWS", "Linux",
            "Kubernetes",
        ],
        "sentences": [
            "머신러닝 모델을 학습하고 성능을 개선합니다.",
            "모델 실험을 관리하고 재현 가능한 학습 환경을 구성합니다.",
            "추천, 분류, 예측 모델을 개발하고 운영합니다.",
            "모델 서빙 API를 개발하고 추론 성능을 최적화합니다.",
            "데이터 전처리부터 학습, 평가, 배포까지 담당합니다.",
        ],
    },
    "DevOps Engineer": {
        "titles": [
            "DevOps 엔지니어 채용",
            "SRE Engineer",
            "인프라 엔지니어",
            "클라우드 인프라 엔지니어",
            "플랫폼 엔지니어",
            "시스템 엔지니어",
        ],
        "skills": [
            "Docker", "Kubernetes", "Linux", "AWS", "GCP", "Azure",
            "Prometheus", "Grafana", "Terraform", "Ansible", "Redis",
            "Nginx",
        ],
        "sentences": [
            "클라우드 인프라를 구축하고 운영합니다.",
            "서비스 배포 자동화와 CI/CD 파이프라인을 관리합니다.",
            "모니터링 시스템을 구축하고 장애 대응 프로세스를 개선합니다.",
            "컨테이너 기반 운영 환경을 관리합니다.",
            "시스템 안정성과 가용성을 높이기 위한 개선 작업을 수행합니다.",
        ],
    },
    "Data Analyst": {
        "titles": [
            "데이터 분석가 채용",
            "Data Analyst",
            "데이터 분석 담당자",
            "비즈니스 데이터 분석가",
            "서비스 데이터 분석가",
            "BI Analyst",
        ],
        "skills": [
            "SQL", "Python", "Pandas", "Tableau", "Excel",
            "PostgreSQL", "MySQL", "BigQuery", "statistics", "PowerBI",
        ],
        "sentences": [
            "서비스 지표를 분석하고 인사이트를 도출합니다.",
            "SQL을 활용해 데이터를 추출하고 리포트를 작성합니다.",
            "비즈니스 의사결정을 위한 대시보드를 운영합니다.",
            "실험 결과를 분석하고 개선 방향을 제안합니다.",
            "사용자 행동 데이터를 분석해 문제를 정의합니다.",
        ],
    },
}


def make_description(job_category: str) -> str:
    template = JOB_TEMPLATES[job_category]

    selected_skills = random.sample(
        template["skills"],
        k=random.randint(4, min(8, len(template["skills"])))
    )

    selected_sentences = random.sample(
        template["sentences"],
        k=random.randint(2, 4)
    )

    skill_text = " ".join(selected_skills)
    sentence_text = " ".join(selected_sentences)

    return f"{skill_text} 기반 업무 경험이 필요합니다. {sentence_text}"


def main():
    random.seed(42)

    rows = []
    source_job_id = 1

    # 직무별 50개씩 생성 = 총 250개
    for job_category, template in JOB_TEMPLATES.items():
        for _ in range(50):
            title = random.choice(template["titles"])
            company = random.choice(COMPANIES)
            location = random.choice(LOCATIONS)
            career = random.choice(CAREERS)
            description = make_description(job_category)

            rows.append({
                "source": "sample",
                "source_job_id": source_job_id,
                "title": title,
                "company": company,
                "location": location,
                "career": career,
                "description": description,
            })

            source_job_id += 1

    random.shuffle(rows)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "source_job_id",
                "title",
                "company",
                "location",
                "career",
                "description",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
