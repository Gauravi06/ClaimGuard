import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db
from app.models import Claim
from uuid import uuid4
from datetime import datetime, timezone

client = TestClient(app)

def clear_db():
    db.claims.clear()
    db.claims_list.clear()

def test_model_performance_zero_claims():
    clear_db()
    response = client.get("/api/analytics/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert data["total_labeled"] == 0
    assert data["accuracy"] is None
    assert data["roc_auc"] is None
    assert data["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}

def test_model_performance_one_labeled_claim():
    clear_db()
    c = Claim(
        id=uuid4(),
        claimant_name="Test User",
        claim_amount=1000.0,
        claim_type="auto",
        incident_date="2026-01-01",
        days_to_report=2,
        description="Test",
        prior_claims_count=0,
        police_report_filed=True,
        witnesses=1,
        fraud_score=0.15,
        risk_level="low",
        explanations=[],
        status="pending",
        submission_date=datetime.now(timezone.utc),
        true_label=False,
        prediction=False
    )
    db.add(c)
    
    response = client.get("/api/analytics/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert data["total_labeled"] == 1
    assert data["roc_auc"] is None
    assert isinstance(data["accuracy"], float)
    assert data["accuracy"] == 1.0
    assert data["confusion_matrix"]["tn"] == 1

def test_model_performance_multiple_classes():
    clear_db()
    c1 = Claim(
        id=uuid4(),
        claimant_name="User 1",
        claim_amount=1000.0,
        claim_type="auto",
        incident_date="2026-01-01",
        days_to_report=2,
        description="Test",
        prior_claims_count=0,
        police_report_filed=True,
        witnesses=1,
        fraud_score=0.15,
        risk_level="low",
        explanations=[],
        status="pending",
        submission_date=datetime.now(timezone.utc),
        true_label=False,
        prediction=False
    )
    c2 = Claim(
        id=uuid4(),
        claimant_name="User 2",
        claim_amount=25000.0,
        claim_type="auto",
        incident_date="2026-01-01",
        days_to_report=30,
        description="Test Fraud",
        prior_claims_count=5,
        police_report_filed=False,
        witnesses=0,
        fraud_score=0.85,
        risk_level="high",
        explanations=[],
        status="pending",
        submission_date=datetime.now(timezone.utc),
        true_label=True,
        prediction=True
    )
    db.add(c1)
    db.add(c2)
    
    response = client.get("/api/analytics/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert data["total_labeled"] == 2
    assert data["roc_auc"] == 1.0
    assert data["accuracy"] == 1.0
    assert data["confusion_matrix"]["tp"] == 1
    assert data["confusion_matrix"]["tn"] == 1
