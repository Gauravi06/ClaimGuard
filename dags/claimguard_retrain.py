"""
dags/claimguard_retrain.py
Airflow DAG for ClaimGuard periodic retraining pipeline.
Designed and syntax-checked; not executed locally.
"""
import os
from datetime import datetime
import requests

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowSkipException

# Reuse pipeline components (assumes backend is on PYTHONPATH)
from app.pipeline.state import state, MIN_SETTLED
from app.pipeline.simulation import get_settled
from app.pipeline.training import train_and_log


def check_settled_count(**context) -> int:
    """Check number of settled claims; skip retraining if < 25."""
    as_of = state.simulated_date
    settled = get_settled(as_of)
    settled_count = len(settled)
    if settled_count < MIN_SETTLED:
        raise AirflowSkipException(
            f"Fewer than {MIN_SETTLED} claims settled ({settled_count} < {MIN_SETTLED}). Skipping retraining."
        )
    return settled_count


def task_train_and_log(**context) -> dict:
    """Run model training and candidate evaluation on settled claims."""
    as_of = state.simulated_date
    result = train_and_log(as_of)
    return result


def task_promote_check(**context) -> bool:
    """Verify if the trained candidate model was promoted to champion."""
    ti = context["ti"]
    train_res = ti.xcom_pull(task_ids="train_and_log")
    promoted = train_res.get("promoted", False) if isinstance(train_res, dict) else False
    return bool(promoted)


def task_notify_api(**context) -> str:
    """Notify backend API simulation metrics endpoint."""
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    try:
        resp = requests.get(f"{backend_url}/api/sim/metrics", timeout=5)
        resp.raise_for_status()
    except Exception as exc:
        print(f"API notification skipped or failed: {exc}")
    return "ok"


default_args = {
    "owner": "claimguard",
    "retries": 0,
}

with DAG(
    dag_id="claimguard_retrain",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    default_args=default_args,
    tags=["claimguard", "retrain", "mlops"],
) as dag:
    check_task = PythonOperator(
        task_id="check_settled_count",
        python_callable=check_settled_count,
    )

    train_task = PythonOperator(
        task_id="train_and_log",
        python_callable=task_train_and_log,
    )

    promote_task = PythonOperator(
        task_id="promote_check",
        python_callable=task_promote_check,
    )

    notify_task = PythonOperator(
        task_id="notify_api",
        python_callable=task_notify_api,
    )

    check_task >> train_task >> promote_task >> notify_task
