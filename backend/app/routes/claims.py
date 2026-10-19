from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID
from app.models import ClaimCreate, Claim, LabelUpdate, SimulationRequest
from app.database import db
from app.ml.pipeline import ml_pipeline
from datetime import datetime, timedelta, timezone
import random

claims_router = APIRouter(prefix="/api/claims", tags=["Claims"])
simulate_router = APIRouter(prefix="/api/simulate", tags=["Simulation"])

@claims_router.post("", response_model=Claim)
def create_claim(claim_in: ClaimCreate):
    claim_dict = claim_in.model_dump()
    
    score = ml_pipeline.predict(claim_dict)
    explanations = ml_pipeline.explain(claim_dict, score)
    
    risk_level = "low"
    if score > 0.7:
        risk_level = "high"
    elif score >= 0.3:
        risk_level = "medium"
        
    claim = Claim(
        **claim_dict,
        fraud_score=score,
        risk_level=risk_level,
        explanations=explanations,
        prediction=score > 0.5,
        status="pending",
        true_label=None,
    )
    
    db.add(claim)
    return claim

@claims_router.get("", response_model=List[Claim])
def get_claims():
    return db.get_all()

@claims_router.get("/{claim_id}", response_model=Claim)
def get_claim(claim_id: UUID):
    claim = db.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@claims_router.patch("/{claim_id}/label", response_model=Claim)
def update_label(claim_id: UUID, label_update: LabelUpdate):
    claim = db.update_label(claim_id, label_update.true_label)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@claims_router.post("/{claim_id}/settle", response_model=Claim)
def settle_claim(claim_id: UUID, outcome: LabelUpdate):
    """Demo of the delayed investigation outcome.

    Reveals the ground truth of a PENDING claim and marks it SETTLED. The original
    prediction, fraud score, risk level and explanations are never touched, so the
    stored prediction can be evaluated against the label that arrived later.
    """
    existing = db.get(claim_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Claim not found")
    if existing.true_label is not None:
        raise HTTPException(status_code=409, detail="Claim is already settled; ground truth is final")
    return db.update_label(claim_id, outcome.true_label)

@simulate_router.post("/delayed-labels", response_model=List[Claim])
def simulate_delayed_labels(req: SimulationRequest):
    new_claims = []
    claim_types = ['auto', 'health', 'property', 'life']
    
    for _ in range(req.count):
        claim_type = random.choice(claim_types)
        is_fraud_truth = random.random() < req.fraud_rate
        
        amount = random.uniform(500, 25000)
        if is_fraud_truth:
            amount += random.uniform(10000, 30000)
            
        claim_data = {
            "claimant_name": f"Simulated User {random.randint(1000,9999)}",
            "claim_amount": amount,
            "claim_type": claim_type,
            "incident_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(5, 60))).isoformat(),
            "days_to_report": random.randint(1, 40) if is_fraud_truth else random.randint(1, 10),
            "description": "Simulated claim data for testing",
            "prior_claims_count": random.randint(2, 5) if is_fraud_truth else random.randint(0, 1),
            "police_report_filed": not is_fraud_truth,
            "witnesses": 0 if is_fraud_truth else random.randint(0, 2),
            "fault": 1 if is_fraud_truth else random.choice([0, 1]),
            "deductible": 500.0 if (is_fraud_truth and random.random() < 0.3) else 400.0,
            "driver_rating": random.randint(2, 4) if is_fraud_truth else random.randint(1, 3),
            "age": float(random.randint(20, 60)),
            "accident_area": 1,
            "address_change_claim": random.choice([2, 3, 4]) if (is_fraud_truth and random.random() < 0.4) else 0,
            "number_of_suppliments": random.choice([4.0, 6.0]) if is_fraud_truth else 0.0,
        }
        
        score = ml_pipeline.predict(claim_data)
        explanations = ml_pipeline.explain(claim_data, score)
        
        risk_level = "low"
        if score > 0.7:
            risk_level = "high"
        elif score >= 0.3:
            risk_level = "medium"
            
        claim = Claim(
            **claim_data,
            fraud_score=score,
            risk_level=risk_level,
            explanations=explanations,
            prediction=score > 0.5,
            true_label=is_fraud_truth,
            status="settled",
            submission_date=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))
        )
        new_claims.append(claim)

    db.add_many(new_claims)
    return new_claims