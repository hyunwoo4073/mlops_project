# jobskill-mlops project


# 디렉터리 구조
```text
.
├── README.md
├── dags
├── data
│   ├── processed
│   │   └── cleaned_jobs.csv
│   └── raw
│       └── sample_jobs.csv
├── mlflow.db
├── mlruns
│   └── 1
│       └── models
│           ├── m-7f4cd8809b944aaf840a15e09b63bd3c
│           │   └── artifacts
│           │       ├── MLmodel
│           │       ├── conda.yaml
│           │       ├── model.skops
│           │       ├── python_env.yaml
│           │       └── requirements.txt
│           └── m-ad48fc1b5f934bf782294dc8c1dea8ba
│               └── artifacts
│                   ├── MLmodel
│                   ├── conda.yaml
│                   ├── model.skops
│                   ├── python_env.yaml
│                   └── requirements.txt
├── models
│   └── job_classifier.pkl
├── notebooks
├── requirements.txt
├── scripts
│   └── generate_sample_jobs.py
└── src
    ├── common
    ├── inference
    │   └── api.py
    ├── preprocessing
    │   ├── clean_text.py
    │   ├── extract_skills.py
    │   ├── label_jobs.py
    │   └── preprocess.py
    └── training
        └── train_baseline.py
```

# 디렉터리 및 파일 생성
mkdir jobskill-mlops
cd jobskill-mlops

mkdir -p data/raw data/processed models src/preprocessing src/training src/inference src/common notebooks dags
touch README.md

# 백엔드 실행
uvicorn main:app^C-host 0.0.0.0 --port 8000 --reload

# docker postgres
docker compose up -d
docker exec -it jobskill-postgres psql -U jobskill -d jobskill

# sql 실행
docker exec -i jobskill-postgres psql -U jobskill -d jobskill < sql/create_tables.sql

# sql 실행 확인
docker exec -it jobskill-postgres psql -U jobskill -d jobskill

# 실행 순서
python src/ingestion/load_raw_jobs.py
python src/preprocessing/preprocess_db.py
python src/training/train_baseline.py
