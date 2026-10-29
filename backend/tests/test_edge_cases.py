"""
backend/tests/test_edge_cases.py
Comprehensive unit tests for Task R2: Edge cases and idempotency in ClaimGuard.

Covers:
1. newly_settled <= 0: Advancing clock must NOT retrain; returns retrained: false.
2. Settled data with only 1 class: Do not crash; keep current model; return retrained: false with reason.
3. Training exception: Catch it, preserve previous model and version, return HTTP 200 with retrained: false and error.
4. Idempotency: Calling train_and_log twice with the same as_of and settled count produces identical metrics,
   without bumping model_version or retrains_total twice.
5. Empty pending set at dataset end: /api/sim/pending returns count: 0 and claims: [].
6. Clock past last filed date: No crash; clean JSON returned across all endpoints.
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

from app.main import app
from app.pipeline.state import state, reset_state, advance
from app.pipeline import simulation, training
from app.pipeline.training import train_and_log, reset_model, get_model_version, get_current_model

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean DB and simulation state for every test."""
    from app.database import init_db
    init_db()
    reset_state()
    reset_model()
    yield
    reset_state()
    reset_model()


def test_no_new_settled_claims_does_not_retrain():
    """Requirement 1: If newly_settled <= 0, advance must NOT retrain and return retrained: false."""
    # Fast forward to first retrain at 2015-01-22 (61 settled claims, promotes v1)
    res1 = advance(days=21)
    assert res1["retrained"] is True
    assert res1["model_version"] == 1
    assert state.model_version == 1
    retrains_before = state.retrains_total

    # Advance 0 days -> newly_settled is 0
    res_zero = advance(days=0)
    assert res_zero["retrained"] is False
    assert res_zero["newly_settled"] == 0
    assert res_zero["model_version"] == 1
    assert state.retrains_total == retrains_before


def test_settled_data_single_class_does_not_crash(monkeypatch):
    """Requirement 2: Settled data with only 1 class must not crash, keeps model, returns retrained: false with reason."""
    as_of = date(2015, 2, 1)
    real_settled = simulation.get_settled(as_of)
    assert len(real_settled) > 25

    # Modify all claims so they have only one class (is_fraud = 0)
    single_class_df = real_settled.copy()
    single_class_df["is_fraud"] = 0

    monkeypatch.setattr(simulation, "get_settled", lambda d: single_class_df)

    res = train_and_log(as_of)
    assert res["retrained"] is False
    assert "reason" in res
    assert "one class" in res["reason"].lower()
    assert res["model_version"] == 0
    assert get_model_version() == 0

    # Also test via state.advance()
    adv_res = advance(days=7)
    assert adv_res["retrained"] is False
    assert "reason" in adv_res
    assert "one class" in adv_res["reason"].lower()
    assert adv_res["model_version"] == 0


def test_training_exception_handled_gracefully_and_returns_http_200(monkeypatch):
    """Requirement 3: Training exception caught, preserves model/version, HTTP 200 with retrained: false and error."""
    # First promote v1
    res1 = advance(days=21)
    assert res1["retrained"] is True
    assert res1["model_version"] == 1
    initial_model = get_current_model()
    assert initial_model is not None

    # Inject an unexpected exception during candidate creation/fitting
    def failing_create_model(classifier_type: str):
        raise RuntimeError("Simulated failure in ML candidate pipeline")

    monkeypatch.setattr(training, "_create_model_pipeline", failing_create_model)

    # Calling train_and_log directly
    res_err = train_and_log(date(2015, 1, 29))
    assert res_err["retrained"] is False
    assert "error" in res_err
    assert "Simulated failure" in res_err["error"]
    assert res_err["model_version"] == 1
    assert get_model_version() == 1

    # Calling via HTTP POST /api/sim/advance
    response = client.post("/api/sim/advance", json={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert data["retrained"] is False
    assert "error" in data
    assert "Simulated failure" in data["error"]
    assert data["model_version"] == 1
    assert state.model_version == 1
    # Serving model must still be preserved
    assert get_current_model() is initial_model


def test_idempotency_train_and_log_and_advance():
    """Requirement 4: Calling train_and_log twice with same as_of & settled count produces identical metrics,
    without bumping model_version or retrains_total twice."""
    as_of = date(2015, 1, 22)

    # First call
    res_a = train_and_log(as_of)
    assert res_a["promoted"] is True
    assert res_a["model_version"] == 1

    # Second call with identical as_of and settled count
    res_b = train_and_log(as_of)
    assert res_a == res_b
    assert res_b["model_version"] == 1
    assert get_model_version() == 1

    # Check via state.advance()
    reset_state()
    adv_1 = advance(days=21)
    assert adv_1["retrained"] is True
    retrains_after_1 = state.retrains_total

    # Advance 0 days (same date, same settled count)
    adv_repeat = advance(days=0)
    assert adv_repeat["retrained"] is False
    assert state.retrains_total == retrains_after_1


def test_empty_pending_set_at_dataset_end():
    """Requirement 5: At dataset end when all claims settled, /api/sim/pending returns count: 0 and claims: []."""
    # Advance clock far beyond dataset end (e.g. 2017-01-01)
    state.simulated_date = date(2017, 1, 1)

    response = client.get("/api/sim/pending")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["claims"] == []
    assert data["as_of"] == "2017-01-01"


def test_clock_past_last_filed_date_no_crash():
    """Requirement 6: Advancing clock past last filed date must not crash and return valid state."""
    # Advance clock by 400 days past all data
    res = advance(days=400)
    assert isinstance(res, dict)
    assert "simulated_date" in res
    assert res["retrained"] is True or res["retrained"] is False

    # Check all sim endpoints past dataset end
    clock_res = client.get("/api/sim/clock")
    assert clock_res.status_code == 200

    pending_res = client.get("/api/sim/pending")
    assert pending_res.status_code == 200
    assert pending_res.json()["count"] == 0

    settled_res = client.get("/api/sim/settled")
    assert settled_res.status_code == 200
    assert settled_res.json()["count"] > 0

    metrics_res = client.get("/api/sim/metrics")
    assert metrics_res.status_code == 200
