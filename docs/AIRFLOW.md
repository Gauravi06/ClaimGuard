# Airflow DAG Deployment Guide

This DAG is designed and syntax-checked but was NOT run in Airflow.

## How it would run in Docker

1. **Airflow Service**: Use the official Apache Airflow container image (e.g. `apache/airflow:2.9.2`) inside `docker-compose.yml`.
2. **Mount Volume**: Mount `dags/` into `/opt/airflow/dags` inside the Airflow webserver and scheduler containers.
3. **Mount Backend**: Mount `backend/` into `/opt/airflow/backend` so pipeline code is available to Airflow workers.
4. **Environment Configuration**: Set `PYTHONPATH=/opt/airflow/backend` and `BACKEND_URL=http://backend:8000` in the Airflow environment.
5. **Database Connection**: Set `DATABASE_URL` matching the application database configuration (PostgreSQL or mounted SQLite).
6. **Airflow Scheduler**: The Airflow scheduler discovers `dags/claimguard_retrain.py` and schedules daily execution (`@daily`).
7. **Task Execution Flow**:
   - `check_settled_count`: Queries settled claims and raises `AirflowSkipException` if fewer than 25 claims are settled.
   - `train_and_log`: Trains RF, LR, and XGBoost candidates, evaluates on validation holdout, and logs metrics to MLflow.
   - `promote_check`: Checks candidate PR-AUC against active champion PR-AUC and flags promotion.
   - `notify_api`: Sends a GET request to `${BACKEND_URL}/api/sim/metrics` to inform the serving backend.
