# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow, MLflow, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 연결해 데이터 수집부터 운영 검증, 모니터링, 알림, 증빙 산출물까지 구성한 경량 MLOps 프로젝트입니다.

## 문서 구성

```text
README.md
- 프로젝트 메인 소개와 빠른 실행 흐름

docs/README_SUMMARY.md
- 포트폴리오 검토자용 요약

docs/README_FULL.md
- 전체 구현 상세, 운영 기능, 트러블슈팅, 검증 절차

docs/QUICKSTART.md
- 로컬 실행 명령어 중심 Quick Start
```

## 핵심 흐름

```text
데이터 생성/수집
→ PostgreSQL raw 적재
→ 전처리/기술스택 추출
→ Data Contract / Training Data Quality 검증
→ TF-IDF + Logistic Regression 학습
→ MLflow experiment / dataset / evaluation artifact 기록
→ 모델 성능 검증 / class-level gate
→ best model promotion / archive / rollback
→ batch inference / FastAPI serving
→ production feedback 수집
→ retraining candidate 판단
→ retraining strategy check
→ training cost benchmark
→ metrics / alert / runbook / evidence bundle
```

## 최근 주요 개선

```text
2026-08-04 ~ 2026-08-05
- Retraining Strategy and Cost Benchmark 추가
- RETRAINING_STRATEGY / TRAINING_COST 결과를 pipeline_check_results에 저장
- retraining strategy report와 training cost report 생성
- training cost metric을 FastAPI /metrics, Prometheus alert, runbook으로 연결
- Training Data Selection Policy 추가
- full / lookback / recent / recent_plus_history_sample 학습 데이터 선택 모드 추가
- ops evidence bundle에 retraining strategy report와 training cost report 포함

2026-08-03
- ops evidence bundle validation 추가
- CI ops evidence artifact 업로드 추가
- CI failure diagnostics artifact 추가
- README / SUMMARY / FULL / QUICKSTART 문서 구조 정리
```

## 주요 명령어

```bash
make up
make smoke
make ops-static-check
make ops-check

make production-feedback-check
make retraining-candidate-check

make retraining-strategy-check
make retraining-strategy-report
make training-cost-report

make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## 재학습 전략/비용 검증

```bash
make retraining-strategy-check
make retraining-strategy-report
make training-cost-report
```

결과 파일:

```text
reports/latest_retraining_strategy_report.md
reports/latest_training_cost_report.md
```

DB 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    checked_at
FROM pipeline_check_results
WHERE check_type IN ('RETRAINING_STRATEGY', 'TRAINING_COST')
ORDER BY checked_at DESC, check_type, check_name
LIMIT 50;
"
```

## 학습 데이터 선택 모드

기본값은 full입니다.

```env
TRAINING_DATA_MODE=full
```

실험 실행 예시:

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&
TRAINING_DATA_MODE=recent_plus_history_sample TRAINING_RECENT_DAYS=90 TRAINING_HISTORY_SAMPLE_ROWS_PER_CLASS=50 python src/training/train_baseline.py
"
```

## 운영 증빙 생성

```bash
make ops-check
make ops-report
make retraining-strategy-report
make training-cost-report
make ops-evidence-bundle
make ops-evidence-check
```

생성 위치:

```text
reports/ops_evidence/jobskill_ops_evidence_YYYYMMDD_HHMMSS.zip
```

상세 내용은 `docs/README_FULL.md`, 빠른 검토는 `docs/README_SUMMARY.md`, 실행 절차는 `docs/QUICKSTART.md`를 참고합니다.
