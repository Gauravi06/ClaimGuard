"""
backend/tests/test_tracking.py
Unit tests for MLflow tracking helper (R5).
"""
import pytest
from pathlib import Path
from app.pipeline.tracking import log_training_run, MLRUNS_DIR, EXPERIMENT_NAME
import mlflow


def test_log_training_run_creates_mlflow_run():
    metrics = {
        "precision": 0.85,
        "recall": 0.75,
        "f1": 0.80,
        "pr_auc": 0.82,
    }
    run_id = log_training_run(
        as_of="2015-02-15",
        n_train=100,
        n_pending=50,
        model_version=1,
        metrics=metrics,
        best_model_name="RandomForest",
    )

    assert isinstance(run_id, str)
    assert len(run_id) == 32

    # Verify run exists in MLflow
    run = mlflow.get_run(run_id)
    assert run is not None
    assert run.info.run_id == run_id

    # Verify logged params
    params = run.data.params
    assert params["as_of"] == "2015-02-15"
    assert params["n_train"] == "100"
    assert params["n_pending"] == "50"
    assert params["model_version"] == "1"
    assert params["best_model"] == "RandomForest"
    assert params["investigation_window_min"] == "10"
    assert params["investigation_window_max"] == "30"
    assert params["seed"] == "42"
    assert params["retrain_threshold"] == "25"

    # Verify logged metrics
    logged_metrics = run.data.metrics
    assert logged_metrics["precision"] == 0.85
    assert logged_metrics["recall"] == 0.75
    assert logged_metrics["f1"] == 0.80
    assert logged_metrics["pr_auc"] == 0.82
