"""
backend/tests/test_drift.py
Unit tests for Task R3: Feature drift detection using Population Stability Index (PSI).

Tests:
1. psi of identical arrays is ~ 0.
2. psi of clearly shifted arrays is > 0.25.
3. psi handles categorical arrays and edge cases cleanly.
4. compute_drift and GET /api/sim/drift before first retrain return status "no model yet".
5. compute_drift and GET /api/sim/drift after retrain return valid status, max_psi, and 13 features.
6. No label fields anywhere in the drift response.
7. DRIFT_TRIGGERS_RETRAIN environment variable triggers retrain on 'alert' status.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
import numpy as np

from app.main import app
from app.pipeline.drift import psi, compute_drift, FEATURES
from app.pipeline.state import state, reset_state, advance

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_simulation():
    """Ensure clean simulation state for each drift test."""
    from app.database import init_db
    init_db()
    reset_state()
    yield
    reset_state()


def test_psi_identical_arrays_is_zero():
    """psi of identical arrays is ~ 0 (<= 0.001)."""
    np.random.seed(42)
    arr = np.random.normal(50, 10, 500)
    score = psi(arr, arr)
    assert score == pytest.approx(0.0, abs=1e-3)

    # Identical categorical
    cat_arr = np.array(["yes", "no", "unknown"] * 100)
    cat_score = psi(cat_arr, cat_arr)
    assert cat_score == pytest.approx(0.0, abs=1e-3)


def test_psi_shifted_arrays_is_above_threshold():
    """psi of clearly shifted arrays is well above 0.25 alert threshold."""
    np.random.seed(42)
    expected = np.random.normal(50, 5, 500)
    actual = np.random.normal(80, 5, 500)
    score = psi(expected, actual)
    assert score > 0.25

    # Categorical shift
    exp_cat = np.array(["yes"] * 200 + ["no"] * 10)
    act_cat = np.array(["yes"] * 10 + ["no"] * 200)
    assert psi(exp_cat, act_cat) > 0.25


def test_psi_edge_cases():
    """psi handles empty arrays and constant arrays gracefully."""
    assert psi([], []) == 0.0
    assert psi([1, 2, 3], []) == 0.0
    assert psi([], [1, 2, 3]) == 0.0

    # Constant array compared to same constant array
    const = np.array([5.0, 5.0, 5.0])
    assert psi(const, const) == 0.0

    # Constant array compared to shifted value
    assert psi(const, np.array([10.0, 10.0, 10.0])) > 0.25


def test_drift_endpoint_before_first_retrain():
    """Before the first retrain, /api/sim/drift returns status 'no model yet' with max_psi None."""
    assert state.model_version == 0

    response = client.get("/api/sim/drift")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "no model yet"
    assert data["max_psi"] is None
    assert data["features"] == []
    assert "as_of" in data

    # Verify no label fields leaked
    for forbidden in ["is_fraud", "investigation_days", "label_available_at"]:
        assert forbidden not in data


def test_drift_endpoint_after_retrain():
    """After first retrain, /api/sim/drift returns valid status, max_psi, and all 13 features."""
    # Advance clock to first retrain at 2015-01-22
    adv_res = advance(days=21)
    assert adv_res["retrained"] is True
    assert adv_res["model_version"] == 1

    response = client.get("/api/sim/drift")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in {"ok", "warn", "alert"}
    assert isinstance(data["max_psi"], float)
    assert data["max_psi"] >= 0.0
    assert len(data["features"]) == 13

    feature_names = {f["name"] for f in data["features"]}
    assert feature_names == set(FEATURES)

    for item in data["features"]:
        assert "name" in item
        assert "psi" in item
        assert isinstance(item["psi"], float)
        assert item["psi"] >= 0.0

    # Verify no label fields leaked
    for forbidden in ["is_fraud", "investigation_days", "label_available_at"]:
        assert forbidden not in data


def test_drift_triggers_retrain_flag(monkeypatch):
    """When DRIFT_TRIGGERS_RETRAIN=true and drift is 'alert', retrain is triggered."""
    # First retrain to promote v1 at 2015-01-22
    adv1 = advance(days=21)
    assert adv1["retrained"] is True
    assert adv1["model_version"] == 1

    # By default (DRIFT_TRIGGERS_RETRAIN not set or false), alert drift does not trigger retrain if newly_settled < 25
    monkeypatch.delenv("DRIFT_TRIGGERS_RETRAIN", raising=False)

    # Force compute_drift to return alert
    from app.pipeline import drift
    monkeypatch.setattr(
        drift,
        "compute_drift",
        lambda d: {"as_of": d.isoformat(), "status": "alert", "max_psi": 0.35, "features": []}
    )

    # Advance 1 day (small increment, newly_settled < 25)
    adv_default = advance(days=1)
    if adv_default["newly_settled"] < 25:
        assert adv_default["retrained"] is False

    # Now enable DRIFT_TRIGGERS_RETRAIN=true
    monkeypatch.setenv("DRIFT_TRIGGERS_RETRAIN", "true")

    # Advance another day with newly_settled > 0 and drift alert
    adv_drift = advance(days=2)
    if adv_drift["newly_settled"] > 0:
        assert adv_drift["retrained"] is True
