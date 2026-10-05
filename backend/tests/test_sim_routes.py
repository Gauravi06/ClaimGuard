import pytest
from fastapi.testclient import TestClient
from datetime import date

from app.main import app
from app.pipeline.state import reset_state, state
from app.routes.sim import get_risk_level, get_prediction

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_simulation_state():
    """Ensure clean simulation state for each route test."""
    reset_state()
    yield
    reset_state()

def test_get_sim_clock():
    """1. GET /api/sim/clock returns initial simulated date."""
    response = client.get("/api/sim/clock")
    assert response.status_code == 200
    data = response.json()
    assert "simulated_date" in data
    assert data["simulated_date"] == "2015-02-01"

def test_post_sim_advance_default():
    """2. POST /api/sim/advance with default 7 days advances date and triggers initial retrain."""
    # When no body is provided, defaults to 7 days
    response = client.post("/api/sim/advance")
    assert response.status_code == 200
    data = response.json()
    assert data["simulated_date"] == "2015-02-08"
    assert data["newly_settled"] == 0
    assert data["retrained"] is True
    assert data["model_version"] == 1

def test_post_sim_advance_custom_days():
    """3. POST /api/sim/advance with a custom number of days."""
    response = client.post("/api/sim/advance", json={"days": 14})
    assert response.status_code == 200
    data = response.json()
    assert data["simulated_date"] == "2015-02-15"
    assert data["retrained"] is True
    assert data["model_version"] == 1

def test_get_sim_pending():
    """4. GET /api/sim/pending returns claims with fraud_score and risk_level."""
    # Advance clock to ensure claims exist
    client.post("/api/sim/advance", json={"days": 28})  # 2015-03-01
    response = client.get("/api/sim/pending")
    assert response.status_code == 200
    data = response.json()
    assert "as_of" in data
    assert "count" in data
    assert "claims" in data
    assert data["as_of"] == "2015-03-01"
    assert data["count"] == len(data["claims"])
    assert data["count"] > 0

    first_claim = data["claims"][0]
    assert "fraud_score" in first_claim
    assert isinstance(first_claim["fraud_score"], float)
    assert "risk_level" in first_claim
    assert first_claim["risk_level"] in {"low", "medium", "high"}
    assert "prediction" in first_claim
    assert isinstance(first_claim["prediction"], bool)

def test_pending_never_exposes_label_columns():
    """7. Pending responses NEVER expose is_fraud, investigation_days, or label_available_at."""
    client.post("/api/sim/advance", json={"days": 28})
    response = client.get("/api/sim/pending")
    assert response.status_code == 200
    claims = response.json()["claims"]
    assert len(claims) > 0

    for claim in claims:
        assert "is_fraud" not in claim, "Pending claim leaked is_fraud!"
        assert "investigation_days" not in claim, "Pending claim leaked investigation_days!"
        assert "label_available_at" not in claim, "Pending claim leaked label_available_at!"

def test_get_sim_settled():
    """5. GET /api/sim/settled returns claims including true labels."""
    client.post("/api/sim/advance", json={"days": 28})  # 2015-03-01
    response = client.get("/api/sim/settled")
    assert response.status_code == 200
    data = response.json()
    assert "as_of" in data
    assert "count" in data
    assert "claims" in data
    assert data["count"] == len(data["claims"])
    assert data["count"] > 0

    first_claim = data["claims"][0]
    assert "fraud_score" in first_claim
    assert "risk_level" in first_claim
    assert "prediction" in first_claim
    assert "is_fraud" in first_claim
    assert "label_available_at" in first_claim

def test_get_sim_metrics():
    """6. GET /api/sim/metrics handles both pre-training and post-training states."""
    # Pre-training (before any advance)
    res_initial = client.get("/api/sim/metrics")
    assert res_initial.status_code == 200
    data_initial = res_initial.json()
    assert data_initial["model_version"] == 0
    assert data_initial["n_train"] == 0
    assert data_initial["precision"] == 0.0

    # Post-training (after first advance)
    client.post("/api/sim/advance", json={"days": 7})
    res_post = client.get("/api/sim/metrics")
    assert res_post.status_code == 200
    data_post = res_post.json()
    assert data_post["model_version"] == 1
    assert data_post["as_of"] == "2015-02-08"
    assert "n_train" in data_post
    assert isinstance(data_post["precision"], float)
    assert isinstance(data_post["recall"], float)
    assert isinstance(data_post["f1"], float)
    assert isinstance(data_post["pr_auc"], float)

def test_risk_level_boundaries():
    """8. Risk-level boundaries: <0.3 low, 0.3-0.7 medium, >=0.7 high."""
    assert get_risk_level(0.0) == "low"
    assert get_risk_level(0.299999) == "low"
    assert get_risk_level(0.3) == "medium"
    assert get_risk_level(0.5) == "medium"
    assert get_risk_level(0.699999) == "medium"
    assert get_risk_level(0.7) == "high"
    assert get_risk_level(0.95) == "high"

def test_prediction_boundary():
    """9. Prediction boundary: exactly 0.5 -> false, >0.5 -> true."""
    assert get_prediction(0.4999) is False
    assert get_prediction(0.5) is False
    assert get_prediction(0.50001) is True
    assert get_prediction(0.8) is True

def test_existing_claims_endpoints_still_work():
    """10. Existing /api/claims endpoints continue to work without conflict."""
    # Existing GET /api/claims
    res_get = client.get("/api/claims")
    assert res_get.status_code == 200
    assert isinstance(res_get.json(), list)

    # Existing POST /api/claims
    claim_payload = {
        "claimant_name": "Jane Doe",
        "claim_amount": 3500.0,
        "claim_type": "auto",
        "incident_date": "2026-02-01",
        "days_to_report": 3,
        "description": "Minor dent on parking lot",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 1
    }
    res_post = client.post("/api/claims", json=claim_payload)
    assert res_post.status_code == 200
    created = res_post.json()
    assert "id" in created
    assert created["claimant_name"] == "Jane Doe"
    assert "fraud_score" in created

    # Test that /api/sim is isolated and doesn't collide with /api/claims/{claim_id}
    res_clock = client.get("/api/sim/clock")
    assert res_clock.status_code == 200
