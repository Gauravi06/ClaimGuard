"""
backend/tests/test_training.py
Unit tests for R4 model training, selection, metrics, and scoring.
"""
import pytest
from datetime import date
import pandas as pd
import numpy as np

from app.pipeline.simulation import get_settled, get_pending
from app.pipeline.training import train_and_log, score_claims, _create_model_pipeline


def test_train_and_log_real_date_structure():
    """Test training on a real as_of date and verifying exact dictionary structure."""
    as_of = date(2015, 2, 15)
    res = train_and_log(as_of)

    assert isinstance(res, dict)
    expected_top_keys = {"run_id", "as_of", "n_train", "n_pending", "model_version", "metrics"}
    assert set(res.keys()) == expected_top_keys

    assert isinstance(res["run_id"], str)
    assert len(res["run_id"]) > 0
    assert res["as_of"] == "2015-02-15"
    assert res["n_train"] == len(get_settled(as_of))
    assert res["n_pending"] == len(get_pending(as_of))
    assert isinstance(res["model_version"], int)

    metrics = res["metrics"]
    expected_metric_keys = {"precision", "recall", "f1", "pr_auc"}
    assert set(metrics.keys()) == expected_metric_keys
    for k in expected_metric_keys:
        assert isinstance(metrics[k], float)
        assert 0.0 <= metrics[k] <= 1.0


def test_both_model_types_considered():
    """Test that both RandomForest and LogisticRegression pipelines can be created and fitted."""
    rf_pipe = _create_model_pipeline("rf")
    lr_pipe = _create_model_pipeline("lr")

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


def test_model_version_increments():
    """Test that model_version increases across consecutive training calls."""
    as_of = date(2015, 2, 1)
    res1 = train_and_log(as_of)
    v1 = res1["model_version"]

    res2 = train_and_log(as_of)
    v2 = res2["model_version"]

    assert v2 == v1 + 1


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
