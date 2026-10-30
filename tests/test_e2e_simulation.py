"""End-to-end simulation loop test (Task L6).

Tests the full simulation lifecycle via FastAPI TestClient against app.main:app:
- Resetting simulation state for clean isolation.
- Clock initialization at day 0 (2015-01-01, model_version == 0).
- Advancing clock in 7-day increments.
- Retrain trigger firing after 3rd advance (settled >= 25 -> model_version 1, retrained True).
- Strict contract enforcement: pending claims never leak ground truth or investigation window.
- Settled claims invariant: label_available_at <= simulated_date.
- Prometheus /metrics exposition consistency with settled claim count.
"""
from datetime import date
from typing import Dict

import mlflow
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.state import reset_state, state
import app.pipeline.tracking as tracking
import app.pipeline.training as training

FORBIDDEN_PENDING_FIELDS = ("is_fraud", "investigation_days", "label_available_at")


def parse_prometheus_text(text: str) -> Dict[str, float]:
    """Parse Prometheus exposition text into a metric_name -> float value map."""
    metrics: Dict[str, float] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            metric_name = parts[0].split("{")[0]
            try:
                metrics[metric_name] = float(parts[1])
            except ValueError:
                continue
    return metrics


@pytest.fixture(autouse=True)
def isolate_simulation_environment(monkeypatch, tmp_path):
    """Ensure simulation state and MLflow runs are isolated per test execution."""
    # Redirect MLflow logging to tmp_path to prevent polluting repo mlruns/
    test_mlruns_dir = tmp_path / "mlruns"
    test_mlruns_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tracking, "MLRUNS_DIR", test_mlruns_dir)

    original_tracking_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(str(test_mlruns_dir.as_uri()))

    # Reset state and training pipeline before test
    reset_state(date(2015, 1, 1))
    training._current_model = None
    training._model_version = 0

    try:
        yield
    finally:
        # Reset state and training pipeline after test
        reset_state(date(2015, 1, 1))
        training._current_model = None
        training._model_version = 0
        try:
            mlflow.set_tracking_uri(original_tracking_uri)
        except Exception:
            pass


def _assert_step_invariants(client: TestClient, current_date_iso: str):
    """Assert invariants across pending, settled, and /metrics endpoints at any step."""
    # 1. Pending claims check
    pending_resp = client.get("/api/sim/pending")
    assert pending_resp.status_code == 200
    pending_data = pending_resp.json()
    assert pending_data["as_of"] == current_date_iso
    assert pending_data["count"] == len(pending_data["claims"])

    for claim in pending_data["claims"]:
        for field in FORBIDDEN_PENDING_FIELDS:
            assert field not in claim, f"Pending claim {claim.get('claim_id')} exposed forbidden field '{field}'"

    # 2. Settled claims check
    settled_resp = client.get("/api/sim/settled")
    assert settled_resp.status_code == 200
    settled_data = settled_resp.json()
    assert settled_data["as_of"] == current_date_iso
    assert settled_data["count"] == len(settled_data["claims"])

    for claim in settled_data["claims"]:
        assert "label_available_at" in claim
        assert claim["label_available_at"] <= current_date_iso, (
            f"Settled claim {claim.get('claim_id')} label_available_at ({claim['label_available_at']}) "
            f"exceeds simulated date ({current_date_iso})"
        )

    # 3. Prometheus /metrics check
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    metrics_text = metrics_resp.text
    assert "claimguard_model_version" in metrics_text
    assert "claimguard_settled_claims" in metrics_text

    parsed = parse_prometheus_text(metrics_text)
    assert "claimguard_model_version" in parsed
    assert "claimguard_settled_claims" in parsed
    assert parsed["claimguard_settled_claims"] == float(settled_data["count"])

    return pending_data, settled_data, parsed


def test_simulation_e2e_loop():
    """Execute full simulation lifecycle walk through 3 weekly advances."""
    client = TestClient(app)

    # Step 0: Day 0 check (simulated date 2015-01-01, no model yet)
    clock_resp = client.get("/api/sim/clock")
    assert clock_resp.status_code == 200
    clock_data = clock_resp.json()
    assert clock_data["simulated_date"] == "2015-01-01"

    _, settled_step0, metrics_step0 = _assert_step_invariants(client, "2015-01-01")
    assert metrics_step0["claimguard_model_version"] == 0.0

    # Advance 1: +7 days -> 2015-01-08
    adv1_resp = client.post("/api/sim/advance", json={"days": 7})
    assert adv1_resp.status_code == 200
    adv1_data = adv1_resp.json()
    assert adv1_data["simulated_date"] == "2015-01-08"
    assert adv1_data["retrained"] is False
    assert adv1_data["model_version"] == 0
    _assert_step_invariants(client, "2015-01-08")

    # Advance 2: +7 days -> 2015-01-15
    adv2_resp = client.post("/api/sim/advance", json={"days": 7})
    assert adv2_resp.status_code == 200
    adv2_data = adv2_resp.json()
    assert adv2_data["simulated_date"] == "2015-01-15"
    assert adv2_data["retrained"] is False
    assert adv2_data["model_version"] == 0
    _assert_step_invariants(client, "2015-01-15")

    # Advance 3: +7 days -> 2015-01-22 (triggers initial retrain)
    adv3_resp = client.post("/api/sim/advance", json={"days": 7})
    assert adv3_resp.status_code == 200
    adv3_data = adv3_resp.json()
    assert adv3_data["simulated_date"] == "2015-01-22"
    assert adv3_data["retrained"] is True
    assert adv3_data["model_version"] == 1
    assert adv3_data["newly_settled"] >= 25

    _, settled_step3, metrics_step3 = _assert_step_invariants(client, "2015-01-22")
    assert metrics_step3["claimguard_model_version"] == 1.0
    assert metrics_step3["claimguard_settled_claims"] >= 25.0
    assert metrics_step3["claimguard_settled_claims"] == float(settled_step3["count"])
