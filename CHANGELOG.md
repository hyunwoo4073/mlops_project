# Changelog

## v0.1.0 - MVP Release

### Added

- Airflow 기반 JobSkill MLOps 파이프라인 구성
- PostgreSQL 기반 원천/정제/스킬/예측/검증/모델 메타데이터 저장 구조 구성
- RemoteOK 크롤러와 sample data generator 기반 데이터 수집 모드 구성
- `DATA_SOURCE_MODE` 지원
  - `sample_only`
  - `crawler_only`
  - `mixed`
- 크롤러 retry/fallback 로직 추가
- 학습 데이터 품질 검증 단계 추가
- scikit-learn 기반 TF-IDF + Logistic Regression baseline 모델 학습
- MLflow tracking 연동
- 모델 성능 검증 및 promotion 단계 추가
- batch inference 결과 저장
- API inference 결과 저장 및 API request log 저장
- prediction quality check 추가
- Markdown 기반 pipeline report 생성
- FastAPI 기반 inference API 추가
- Streamlit 기반 운영 대시보드 추가
- Makefile 기반 실행 명령어 표준화
- smoke check script 추가
- GitHub Actions 기반 Python CI 추가
- GitHub Actions 기반 Docker Compose smoke check workflow 추가

### Pipeline

Current DAG flow:

```text
prepare_raw_sources
→ generate_sample_jobs
→ load_raw_jobs
→ crawl_remoteok_jobs
→ preprocess_jobs
→ check_training_data
→ train_model
→ check_model_performance
→ promote_model
→ batch_inference
→ check_prediction_quality
→ generate_pipeline_report
