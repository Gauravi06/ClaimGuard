"""Persistence tests (run on SQLite via conftest.py).

Real process-restart and Neon checks are manual: see backend/neon_smoke_test.py.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.database import SessionLocal, db
from app.main import app
from app.ml.pipeline import ml_pipeline
from app.models import Claim
from app.orm import ClaimRow

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    if not ml_pipeline.is_trained:  # these tests bypass the app lifespan
        ml_pipeline.train()
    db.clear()
    yield
    db.clear()


def payload(name="Persist Test", **kw):
    data = dict(
        claimant_name=name, claim_amount=30000.0, claim_type="auto", incident_date="2026-09-01",
        days_to_report=40, description="persistence test", prior_claims_count=4,
        police_report_filed=False, witnesses=0,
    )
    data.update(kw)
    return data


def perf():
    return client.get("/api/analytics/model-performance").json()


def metrics_only(p):
    return {k: v for k, v in p.items() if k != "total_predictions"}


def test_created_claim_is_stored_unlabeled_and_reads_back_identically():
    created = client.post("/api/claims", json=payload()).json()
    assert created["true_label"] is None
    assert client.get(f"/api/claims/{created['id']}").json() == created
    stored = db.get(uuid_of(created))
    assert stored.true_label is None
    assert stored.fraud_score == created["fraud_score"]
    assert stored.prediction == created["prediction"]
    assert stored.risk_level == created["risk_level"]
    assert [e.model_dump() for e in stored.explanations] == created["explanations"]


def test_stored_prediction_is_read_not_recomputed():
    created = client.post("/api/claims", json=payload()).json()
    with SessionLocal() as session:
        session.execute(update(ClaimRow).where(ClaimRow.id == uuid_of(created)).values(
            fraud_score=0.9876, risk_level="high", prediction=True,
            explanations=[{"feature": "SENTINEL", "importance": 1.0, "value": 1.0, "direction": "up"}],
        ))
        session.commit()
    got = client.get(f"/api/claims/{created['id']}").json()
    assert got["fraud_score"] == 0.9876
    assert got["risk_level"] == "high"
    assert got["explanations"][0]["feature"] == "SENTINEL"


def test_labeling_persists_and_keeps_original_prediction():
    created = client.post("/api/claims", json=payload()).json()
    labeled = client.patch(f"/api/claims/{created['id']}/label", json={"true_label": True}).json()
    assert labeled["true_label"] is True
    for key in ("fraud_score", "prediction", "risk_level", "explanations"):
        assert labeled[key] == created[key]
    assert db.get(uuid_of(created)).true_label is True


def test_label_unknown_claim_returns_404():
    r = client.patch(f"/api/claims/{uuid4()}/label", json={"true_label": True})
    assert r.status_code == 404


def test_model_performance_excludes_unlabeled_claims():
    a = client.post("/api/claims", json=payload("Labeled A")).json()
    before = perf()
    assert before["total_labeled"] == 0 and before["total_predictions"] == 1

    client.post("/api/claims", json=payload("Unlabeled B"))
    after_unlabeled = perf()
    assert after_unlabeled["total_predictions"] == 2
    assert metrics_only(after_unlabeled) == metrics_only(before)  # unlabeled claim changes nothing

    client.patch(f"/api/claims/{a['id']}/label", json={"true_label": True})
    after_label = perf()
    assert after_label["total_labeled"] == 1 and after_label["total_predictions"] == 2
    cm = after_label["confusion_matrix"]
    assert sum(cm.values()) == 1
    assert (cm["tp"] if a["prediction"] else cm["fn"]) == 1


def test_get_labeled_returns_only_labeled_claims():
    now = datetime.now(timezone.utc)
    for label in (True, False, None):
        db.add(Claim(**payload(f"L-{label}"), fraud_score=0.5, risk_level="medium", explanations=[],
                     prediction=True, submission_date=now, true_label=label))
    assert db.count() == 3
    labeled = db.get_labeled()
    assert len(labeled) == 2 and all(c.true_label is not None for c in labeled)


def test_simulator_claims_are_persisted_with_labels():
    r = client.post("/api/simulate/delayed-labels", json={"count": 10, "fraud_rate": 0.5})
    returned = r.json()
    assert r.status_code == 200 and len(returned) == 10
    assert db.count() == 10 and len(db.get_labeled()) == 10
    stored = {str(c.id): c for c in db.get_all()}
    for c in returned:
        assert stored[c["id"]].fraud_score == c["fraud_score"]
        assert stored[c["id"]].true_label == c["true_label"]


def test_seed_persists_20_claims_and_replaces_existing_data():
    db.add(Claim(**payload("Pre-existing"), fraud_score=0.1, risk_level="low", explanations=[],
                 prediction=False, submission_date=datetime.now(timezone.utc)))
    r = client.post("/api/dev/seed")
    assert r.status_code == 200
    stored = db.get_all()
    assert len(stored) == 20
    assert [sum(c.true_label is v for c in stored) for v in (True, False, None)] == [7, 7, 6]
    assert "Pre-existing" not in {c.claimant_name for c in stored}  # documented wipe behavior


def uuid_of(created):
    return UUID(created["id"])
