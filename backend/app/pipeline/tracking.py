"""
backend/app/pipeline/tracking.py
MLflow tracking helper for ClaimGuard simulation and retrain pipeline (R5).
Logs runs locally to mlruns folder.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
import mlflow

REPO_ROOT = Path(__file__).resolve().parents[3]
MLRUNS_DIR = REPO_ROOT / "mlruns"
EXPERIMENT_NAME = "ClaimGuard_Simulation"


def init_tracking() -> None:
    """Initialize MLflow tracking URI and experiment."""
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(str(MLRUNS_DIR.as_uri()))
    mlflow.set_experiment(EXPERIMENT_NAME)


def log_training_run(
    as_of: str,
    n_train: int,
    n_pending: int,
    model_version: int,
    metrics: Dict[str, float],
    best_model_name: Optional[str] = "None",
    window_min: int = 10,
    window_max: int = 30,
    seed: int = 42,
    retrain_threshold: int = 25,
) -> str:
    """
    Log one retrain run to MLflow.
    Logs metrics, parameters, and tags, returning the MLflow run_id.
    """
    init_tracking()

    run_name = f"retrain_v{model_version}_{as_of}"
    with mlflow.start_run(run_name=run_name) as run:
        # Log parameters
        params = {
            "as_of": as_of,
            "n_train": n_train,
            "n_pending": n_pending,
            "model_version": model_version,
            "best_model": best_model_name or "None",
            "investigation_window_min": window_min,
            "investigation_window_max": window_max,
            "seed": seed,
            "retrain_threshold": retrain_threshold,
        }
        mlflow.log_params(params)

        # Log metrics
        for metric_name, metric_val in metrics.items():
            mlflow.log_metric(metric_name, float(metric_val))

        # Log tags
        mlflow.set_tags({
            "stage": "simulation",
            "source": "ClaimGuard_Pipeline"
        })

        return run.info.run_id
