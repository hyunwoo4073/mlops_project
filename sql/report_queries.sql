-- =========================================================
-- JobSkill MLOps Report Queries
-- =========================================================

-- 1. Latest promoted model
SELECT
    id,
    model_name,
    run_id,
    ROUND(accuracy::numeric, 4) AS accuracy,
    ROUND(f1_weighted::numeric, 4) AS f1_weighted,
    status,
    promoted_model_path,
    created_at
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY created_at DESC, id DESC
LIMIT 1;


-- 2. Model registry history
SELECT
    id,
    model_name,
    LEFT(run_id, 12) AS run_id_short,
    ROUND(accuracy::numeric, 4) AS accuracy,
    ROUND(f1_weighted::numeric, 4) AS f1_weighted,
    status,
    message,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 20;


-- 3. Prediction lineage summary
SELECT
    mp.model_name,
    LEFT(mp.model_run_id, 12) AS model_run_id_short,
    mp.model_registry_id,
    mr.status AS registry_status,
    ROUND(mr.accuracy::numeric, 4) AS registry_accuracy,
    ROUND(mr.f1_weighted::numeric, 4) AS registry_f1_weighted,
    COUNT(*) AS prediction_count,
    ROUND(AVG(mp.confidence)::numeric, 4) AS avg_confidence,
    MIN(mp.predicted_at) AS first_predicted_at,
    MAX(mp.predicted_at) AS last_predicted_at
FROM model_predictions mp
LEFT JOIN model_registry mr
    ON mp.model_registry_id = mr.id
GROUP BY
    mp.model_name,
    mp.model_run_id,
    mp.model_registry_id,
    mr.status,
    mr.accuracy,
    mr.f1_weighted
ORDER BY prediction_count DESC;


-- 4. Latest predictions with model lineage
SELECT
    mp.id,
    mp.job_post_id,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
    mp.model_name,
    LEFT(mp.model_run_id, 12) AS model_run_id_short,
    mp.model_registry_id,
    mr.status AS registry_status,
    ROUND(mr.f1_weighted::numeric, 4) AS registry_f1_weighted,
    mp.model_path,
    mp.predicted_at
FROM model_predictions mp
LEFT JOIN model_registry mr
    ON mp.model_registry_id = mr.id
ORDER BY mp.id DESC
LIMIT 20;


-- 5. Prediction category distribution by model
SELECT
    mp.model_name,
    LEFT(mp.model_run_id, 12) AS model_run_id_short,
    mp.model_registry_id,
    mp.predicted_category,
    COUNT(*) AS prediction_count,
    ROUND(AVG(mp.confidence)::numeric, 4) AS avg_confidence
FROM model_predictions mp
GROUP BY
    mp.model_name,
    mp.model_run_id,
    mp.model_registry_id,
    mp.predicted_category
ORDER BY
    mp.model_registry_id DESC,
    prediction_count DESC;


-- 6. Recent check result summary
SELECT
    check_type,
    status,
    COUNT(*) AS check_count,
    MAX(checked_at) AS latest_checked_at
FROM pipeline_check_results
GROUP BY check_type, status
ORDER BY check_type, status;


-- 7. Latest check details
SELECT
    check_type,
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    dag_id,
    task_id,
    run_id,
    checked_at
FROM pipeline_check_results
ORDER BY id DESC
LIMIT 30;


-- 8. Failed checks
SELECT
    check_type,
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    dag_id,
    task_id,
    run_id,
    checked_at
FROM pipeline_check_results
WHERE status = 'FAIL'
ORDER BY id DESC
LIMIT 30;


-- 9. Model promotion result summary
SELECT
    status,
    COUNT(*) AS count,
    ROUND(AVG(accuracy)::numeric, 4) AS avg_accuracy,
    ROUND(AVG(f1_weighted)::numeric, 4) AS avg_f1_weighted,
    MAX(created_at) AS latest_created_at
FROM model_registry
GROUP BY status
ORDER BY status;
