"""Demo lifecycle: score now (PENDING) -> ground truth later (SETTLED).

The original prediction must never change when the label arrives, and only
settled claims may feed the performance metrics.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import db
from app.main import app
from app.ml.pipeline import ml_pipeline

client = TestClient(app)

CLAIM = {
    "claimant_name": "Demo Claimant",
    "claim_amount": 42000.0,
    "claim_type": "sport",
    "incident_date": "2026-09-20",
    "days_to_report": 20,
    "description": "Demo claim",
    "prior_claims_count": 3,
    "police_report_filed": False,
    "witnesses": 0,
    "fault": 1,
    "deductible": 500.0,
    "driver_rating": 4,
    "age": 29.0,
    "accident_area": 1,
    "address_change_claim": 3,
    "number_of_suppliments": 6.0,
}


@pytest.fixture(autouse=True)
def clean():
    ml_pipeline.load_or_train()  # loads the artifact; never trains
    db.clear()
    yield
    db.clear()


def submit(name="Demo Claimant", **kw):
    r = client.post("/api/claims", json={**CLAIM, "claimant_name": name, **kw})
    assert r.status_code == 200
    return r.json()


def perf():
    return client.get("/api/analytics/model-performance").json()


def test_new_claim_is_scored_and_pending_without_label():
    c = submit()
    assert c["status"] == "pending"
    assert c["true_label"] is None
    assert 0.0 <= c["fraud_score"] <= 1.0
    assert c["risk_level"] in ("low", "medium", "high")
    assert c["prediction"] == (c["fraud_score"] > 0.5)
    assert len(c["explanations"]) > 0
    listed = {x["id"]: x for x in client.get("/api/claims").json()}
    assert listed[c["id"]]["status"] == "pending"
    assert listed[c["id"]]["true_label"] is None


@pytest.mark.parametrize("truth", [True, False])
def test_settling_reveals_label_and_keeps_original_prediction(truth):
    c = submit()
    r = client.post(f"/api/claims/{c['id']}/settle", json={"true_label": truth})
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "settled"
    assert s["true_label"] is truth
    for key in ("fraud_score", "risk_level", "prediction", "explanations"):
        assert s[key] == c[key]
    stored = client.get(f"/api/claims/{c['id']}").json()
    assert stored == s


def test_settled_claim_counts_in_metrics_with_correct_evaluation():
    c = submit()
    truth = bool(c["prediction"])  # label agrees with the original prediction
    client.post(f"/api/claims/{c['id']}/settle", json={"true_label": truth})
    p = perf()
    assert p["total_labeled"] == 1
    assert p["correct_predictions"] == 1 and p["incorrect_predictions"] == 0
    assert p["accuracy"] == 1.0


def test_incorrect_prediction_is_counted_as_incorrect():
    c = submit()
    client.post(f"/api/claims/{c['id']}/settle", json={"true_label": not c["prediction"]})
    p = perf()
    assert p["correct_predictions"] == 0 and p["incorrect_predictions"] == 1
    assert p["accuracy"] == 0.0


def test_pending_claims_are_excluded_from_metrics():
    settled = submit("Settled One")
    submit("Pending One")
    submit("Pending Two")
    before = perf()
    assert before["total_labeled"] == 0 and before["total_predictions"] == 3
    assert before["correct_predictions"] == 0 and before["incorrect_predictions"] == 0

    client.post(f"/api/claims/{settled['id']}/settle", json={"true_label": True})
    after = perf()
    assert after["total_labeled"] == 1 and after["total_predictions"] == 3
    assert after["correct_predictions"] + after["incorrect_predictions"] == 1

    stats = client.get("/api/analytics/stats").json()
    assert stats["settled_claims"] == 1 and stats["pending_claims"] == 2


def test_settled_claim_cannot_be_settled_again():
    c = submit()
    assert client.post(f"/api/claims/{c['id']}/settle", json={"true_label": True}).status_code == 200
    again = client.post(f"/api/claims/{c['id']}/settle", json={"true_label": False})
    assert again.status_code == 409
    assert client.get(f"/api/claims/{c['id']}").json()["true_label"] is True


def test_settle_unknown_claim_returns_404():
    assert client.post(f"/api/claims/{uuid4()}/settle", json={"true_label": True}).status_code == 404


def test_legacy_label_patch_also_settles_without_touching_prediction():
    c = submit()
    r = client.patch(f"/api/claims/{c['id']}/label", json={"true_label": False}).json()
    assert r["status"] == "settled" and r["true_label"] is False
    assert r["fraud_score"] == c["fraud_score"] and r["prediction"] == c["prediction"]


def test_seed_marks_labeled_claims_settled_and_unlabeled_pending():
    claims = client.post("/api/dev/seed").json()
    assert len(claims) == 20
    for c in claims:
        assert c["status"] == ("settled" if c["true_label"] is not None else "pending")
    stats = client.get("/api/analytics/stats").json()
    assert stats["settled_claims"] == 14 and stats["pending_claims"] == 6
    p = perf()
    assert p["total_labeled"] == 14
    assert p["correct_predictions"] + p["incorrect_predictions"] == 14