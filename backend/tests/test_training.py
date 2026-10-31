"""
backend/tests/test_training.py
Unit tests for R4/R1 model training, XGBoost candidate, promotion rules, and scoring.
"""
import pytest
from datetime import date
import pandas as pd
import numpy as np

from app.pipeline.simulation import get_settled, get_pending
from app.pipeline.training import (
    train_and_log,
    score_claims,
    _create_model_pipeline,
    reset_model,
    get_model_version,
    get_current_model,
)


@pytest.fixture(autouse=True)
def clean_model_state():
    """Ensure clean model state before each test."""
    reset_model()
    yield
    reset_model()


def test_train_and_log_real_date_structure():
    """Test training on a real as_of date and verifying exact dictionary structure."""
    as_of = date(2015, 2, 15)
    res = train_and_log(as_of)

    assert isinstance(res, dict)
    expected_top_keys = {
        "run_id", "as_of", "n_train", "n_pending", "model_version",
        "metrics", "promoted", "champion_pr_auc", "candidate_pr_auc", "best_model", "retrained"
    }
    assert set(res.keys()) == expected_top_keys

    assert isinstance(res["run_id"], str)
    assert len(res["run_id"]) > 0
    assert res["as_of"] == "2015-02-15"
    assert res["n_train"] == len(get_settled(as_of))
    assert res["n_pending"] == len(get_pending(as_of))
    assert isinstance(res["model_version"], int)
    assert isinstance(res["promoted"], bool)
    assert isinstance(res["candidate_pr_auc"], float)
    assert isinstance(res["best_model"], str)
    assert res["best_model"] in {"XGBoost", "RandomForest", "LogisticRegression"}

    metrics = res["metrics"]
    expected_metric_keys = {"precision", "recall", "f1", "pr_auc"}
    assert set(metrics.keys()) == expected_metric_keys
    for k in expected_metric_keys:
        assert isinstance(metrics[k], float)
        assert 0.0 <= metrics[k] <= 1.0


def test_three_candidate_model_types_considered():
    """Test that RandomForest, LogisticRegression, and XGBoost pipelines can be created and fitted."""
    rf_pipe = _create_model_pipeline("rf")
    lr_pipe = _create_model_pipeline("lr")
    xgb_pipe = _create_model_pipeline("xgb")

    as_of = date(2015, 2, 15)
    settled = get_settled(as_of)
    assert len(settled) > 0

    from app.pipeline.training import FEATURES
    X = settled[FEATURES]
    y = settled["is_fraud"].astype(int)

    rf_pipe.fit(X, y)
    rf_probs = rf_pipe.predict_proba(X)[:, 1]
    assert len(rf_probs) == len(X)

    lr_pipe.fit(X, y)
    lr_probs = lr_pipe.predict_proba(X)[:, 1]
    assert len(lr_probs) == len(X)

    xgb_pipe.fit(X, y)
    xgb_probs = xgb_pipe.predict_proba(X)[:, 1]
    assert len(xgb_probs) == len(X)


def test_first_model_is_always_promoted():
    """First model retrain is always promoted to version 1 with champion_pr_auc as None."""
    as_of = date(2015, 1, 22)  # First date with >= 25 settled claims (61 settled)
    res = train_and_log(as_of)

    assert res["promoted"] is True
    assert res["model_version"] == 1
    assert res["champion_pr_auc"] is None
    assert res["candidate_pr_auc"] > 0.0
    assert get_model_version() == 1
    assert get_current_model() is not None


def test_candidate_worse_is_not_promoted_and_version_stays():
    """When a new candidate fails to beat the serving champion on holdout, it is not promoted and version stays."""
    # First retrain to promote v1 at 2015-01-22
    res1 = train_and_log(date(2015, 1, 22))
    assert res1["promoted"] is True
    assert res1["model_version"] == 1

    # Second retrain promotes v2 at 2015-01-29 (PR-AUC 0.6451 > 0.2095)
    res2 = train_and_log(date(2015, 1, 29))
    assert res2["promoted"] is True
    assert res2["model_version"] == 2

    # Third retrain at 2015-02-05: candidate (0.5518) fails to beat champion (0.6164)
    res3 = train_and_log(date(2015, 2, 5))
    assert res3["promoted"] is False
    assert res3["champion_pr_auc"] is not None
    assert res3["candidate_pr_auc"] < res3["champion_pr_auc"]
    assert res3["model_version"] == 2
    assert get_model_version() == 2


def test_better_candidate_is_promoted_and_version_increases():
    """When a new candidate beats the serving champion on holdout, it is promoted and model_version increments."""
    # Step 1: initial model v1 promoted at 2015-01-22
    res1 = train_and_log(date(2015, 1, 22))
    assert res1["promoted"] is True
    assert res1["model_version"] == 1

    # Step 2: at 2015-01-29, new candidate PR-AUC (~0.645) beats champion (~0.210) on 34 holdout claims
    res2 = train_and_log(date(2015, 1, 29))
    assert res2["promoted"] is True
    assert res2["model_version"] == 2
    assert res2["candidate_pr_auc"] > res2["champion_pr_auc"]
    assert get_model_version() == 2


def test_score_claims_output_and_bounds():
    """Test that score_claims returns probabilities between 0 and 1 with matching length."""
    as_of = date(2015, 2, 15)
    train_and_log(as_of)

    pending_df = get_pending(as_of)
    assert len(pending_df) > 0

    scores = score_claims(pending_df)
    assert len(scores) == len(pending_df)
    assert all(isinstance(s, float) for s in scores)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_pending_claims_not_used_in_training():
    """Test that pending claims are excluded from training set."""
    as_of = date(2015, 2, 15)
    res = train_and_log(as_of)

    settled_df = get_settled(as_of)
    pending_df = get_pending(as_of)

    assert res["n_train"] == len(settled_df)
    assert res["n_pending"] == len(pending_df)
    assert "is_fraud" not in pending_df.columns

