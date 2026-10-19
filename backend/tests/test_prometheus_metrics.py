"""
backend/tests/test_prometheus_metrics.py
Tests for Prometheus metrics exported at GET /metrics.
Verifies gauges, counter, day 0 behavior, advance steps, and retrain updates.
"""
import re
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.state import reset_state, advance, state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_simulation_state():
    """Ensure clean simulation state for each metrics test."""
    reset_state()
    yield
    reset_state()


def parse_prometheus_text(text: str) -> dict:
    """Parse Prometheus text exposition format into a name -> float dictionary."""
    metrics = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            # Strip any labels e.g. metric_name{label="val"}
            name = parts[0].split("{")[0]
            try:
                metrics[name] = float(parts[1])
            except ValueError:
                pass
    return metrics


def test_metrics_endpoint_headers_and_status():
    """1. GET /metrics returns HTTP 200 with text/plain content type."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_metrics_day_zero_values():
    """2. At Day 0 before first model exists: model_version=0, pr_auc=0.0, never crashes."""
    response = client.get("/metrics")
    assert response.status_code == 200

    parsed = parse_prometheus_text(response.text)
    assert parsed["claimguard_model_version"] == 0.0
    assert parsed["claimguard_last_retrain_pr_auc"] == 0.0
    assert parsed["claimguard_retrains_total"] == 0.0
    assert parsed["claimguard_settled_claims"] == 0.0
    assert parsed["claimguard_pending_backlog"] == 19.0
    assert parsed["claimguard_newly_settled_since_retrain"] == 0.0

    expected_epoch = datetime(2015, 1, 1, tzinfo=timezone.utc).timestamp()
    assert parsed["claimguard_simulated_date_epoch"] == pytest.approx(expected_epoch, rel=1e-3)


def test_metrics_advances_before_first_retrain():
    """3. Advances with fewer than 25 settled claims update counts but do not trigger retrain."""
    # Advance 7 days -> 2015-01-08: 0 settled
    client.post("/api/sim/advance", json={"days": 7})
    res1 = client.get("/metrics")
    assert res1.status_code == 200
    p1 = parse_prometheus_text(res1.text)
    assert p1["claimguard_model_version"] == 0.0
    assert p1["claimguard_settled_claims"] == 0.0
    assert p1["claimguard_retrains_total"] == 0.0

    # Advance another 7 days -> 2015-01-15: 8 settled (< 25)
    client.post("/api/sim/advance", json={"days": 7})
    res2 = client.get("/metrics")
    assert res2.status_code == 200
    p2 = parse_prometheus_text(res2.text)
    assert p2["claimguard_model_version"] == 0.0
    assert p2["claimguard_last_retrain_pr_auc"] == 0.0
    assert p2["claimguard_settled_claims"] == 8.0
    assert p2["claimguard_newly_settled_since_retrain"] == 8.0
    assert p2["claimguard_retrains_total"] == 0.0

    expected_epoch = datetime(2015, 1, 15, tzinfo=timezone.utc).timestamp()
    assert p2["claimguard_simulated_date_epoch"] == pytest.approx(expected_epoch, rel=1e-3)


def test_metrics_at_first_retrain():
    """4. When settled claims cross 25, model_version rises to 1, retrains_total increments, PR-AUC > 0."""
    # Day 0 -> +7 -> +7 -> +7 (total 21 days: 2015-01-22)
    # At 2015-01-22, 69 claims are settled (>= 25)
    adv_res = client.post("/api/sim/advance", json={"days": 21})
    assert adv_res.status_code == 200
    data = adv_res.json()
    assert data["retrained"] is True
    assert data["model_version"] == 1

    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    parsed = parse_prometheus_text(metrics_res.text)

    assert parsed["claimguard_model_version"] == 1.0
    assert parsed["claimguard_retrains_total"] == 1.0
    assert parsed["claimguard_settled_claims"] == 61.0
    assert parsed["claimguard_newly_settled_since_retrain"] == 0.0
    assert parsed["claimguard_last_retrain_pr_auc"] > 0.0

    expected_epoch = datetime(2015, 1, 22, tzinfo=timezone.utc).timestamp()
    assert parsed["claimguard_simulated_date_epoch"] == pytest.approx(expected_epoch, rel=1e-3)


def test_metrics_across_multiple_retrains():
    """5. Multiple retrain cycles increment model_version and counter while tracking settled/backlog."""
    # First retrain (21 days -> 2015-01-22: 61 settled)
    client.post("/api/sim/advance", json={"days": 21})

    # Second retrain (another 7 days -> 28 days total, 2015-01-29: 167 settled, newly settled = 106 >= 25)
    adv2 = client.post("/api/sim/advance", json={"days": 7})
    assert adv2.json()["retrained"] is True
    assert adv2.json()["model_version"] == 2

    metrics_res = client.get("/metrics")
    parsed = parse_prometheus_text(metrics_res.text)

    assert parsed["claimguard_model_version"] == 2.0
    assert parsed["claimguard_retrains_total"] == 2.0
    assert parsed["claimguard_settled_claims"] == 167.0
    assert parsed["claimguard_newly_settled_since_retrain"] == 0.0
    assert parsed["claimguard_last_retrain_pr_auc"] > 0.0


def test_metrics_isolation_from_sim_router():
    """6. GET /metrics is at root, not under /api/sim, and /api/sim/metrics remains JSON."""
    prom_res = client.get("/metrics")
    assert prom_res.status_code == 200
    assert "# TYPE claimguard_model_version" in prom_res.text

    sim_res = client.get("/api/sim/metrics")
    assert sim_res.status_code == 200
    assert isinstance(sim_res.json(), dict)
    assert "model_version" in sim_res.json()
