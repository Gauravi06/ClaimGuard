from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.models import Claim
from app.database import db
from app.ml.pipeline import ml_pipeline

SEED_CLAIMS_DATA = [
    # Labeled Fraud (7 claims)
    {
        "claimant_name": "Robert Vance",
        "claim_amount": 18500.0,
        "claim_type": "auto",
        "incident_date": "2026-08-10",
        "days_to_report": 35,
        "description": "Single vehicle collision late night on rural road, no third-party involvement.",
        "prior_claims_count": 4,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 25,
    },
    {
        "claimant_name": "Amanda Sterling",
        "claim_amount": 42000.0,
        "claim_type": "property",
        "incident_date": "2026-08-01",
        "days_to_report": 42,
        "description": "Claimed high-value jewelry and electronics stolen during weekend trip.",
        "prior_claims_count": 3,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 22,
    },
    {
        "claimant_name": "Marcus Brody",
        "claim_amount": 28900.0,
        "claim_type": "health",
        "incident_date": "2026-08-15",
        "days_to_report": 25,
        "description": "Elective procedure at out-of-network clinic with handwritten receipts.",
        "prior_claims_count": 5,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 20,
    },
    {
        "claimant_name": "Victoria Hayes",
        "claim_amount": 120000.0,
        "claim_type": "life",
        "incident_date": "2026-07-20",
        "days_to_report": 50,
        "description": "Claim filed shortly after policy inception with unverified offshore death certificate.",
        "prior_claims_count": 2,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 18,
    },
    {
        "claimant_name": "Derek Hollis",
        "claim_amount": 14200.0,
        "claim_type": "auto",
        "incident_date": "2026-08-20",
        "days_to_report": 28,
        "description": "Rear-end collision claimed, damage inconsistent with reported impact angle.",
        "prior_claims_count": 3,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 15,
    },
    {
        "claimant_name": "Samantha Reed",
        "claim_amount": 31500.0,
        "claim_type": "property",
        "incident_date": "2026-08-05",
        "days_to_report": 38,
        "description": "Water damage claimed from burst pipe while out of country for 3 months.",
        "prior_claims_count": 4,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 12,
    },
    {
        "claimant_name": "Jason Thorne",
        "claim_amount": 19800.0,
        "claim_type": "health",
        "incident_date": "2026-08-12",
        "days_to_report": 31,
        "description": "Multiple overlapping chiropractic claims submitted across three clinics.",
        "prior_claims_count": 3,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": True,
        "submission_days_ago": 10,
    },

    # Labeled Legitimate (7 claims)
    {
        "claimant_name": "Sarah Jenkins",
        "claim_amount": 3200.0,
        "claim_type": "auto",
        "incident_date": "2026-09-01",
        "days_to_report": 1,
        "description": "Minor fender bender at intersection. Police report filed at scene.",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 2,
        "true_label": False,
        "submission_days_ago": 24,
    },
    {
        "claimant_name": "Michael Chang",
        "claim_amount": 4500.0,
        "claim_type": "health",
        "incident_date": "2026-09-03",
        "days_to_report": 3,
        "description": "Emergency room visit for fractured wrist after sports injury.",
        "prior_claims_count": 1,
        "police_report_filed": False,
        "witnesses": 1,
        "true_label": False,
        "submission_days_ago": 21,
    },
    {
        "claimant_name": "Emily Rodriguez",
        "claim_amount": 6800.0,
        "claim_type": "property",
        "incident_date": "2026-09-05",
        "days_to_report": 2,
        "description": "Storm damage to roof shingles verified by local weather report.",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 1,
        "true_label": False,
        "submission_days_ago": 19,
    },
    {
        "claimant_name": "David Miller",
        "claim_amount": 5100.0,
        "claim_type": "auto",
        "incident_date": "2026-09-08",
        "days_to_report": 2,
        "description": "Side collision in parking garage, eyewitness statement provided.",
        "prior_claims_count": 1,
        "police_report_filed": True,
        "witnesses": 2,
        "true_label": False,
        "submission_days_ago": 16,
    },
    {
        "claimant_name": "Rachel Adams",
        "claim_amount": 2400.0,
        "claim_type": "health",
        "incident_date": "2026-09-10",
        "days_to_report": 1,
        "description": "Standard outpatient diagnostic imaging and lab tests.",
        "prior_claims_count": 0,
        "police_report_filed": False,
        "witnesses": 1,
        "true_label": False,
        "submission_days_ago": 14,
    },
    {
        "claimant_name": "James Wilson",
        "claim_amount": 8900.0,
        "claim_type": "property",
        "incident_date": "2026-09-12",
        "days_to_report": 4,
        "description": "Kitchen fire caused by appliance malfunction, fire department report attached.",
        "prior_claims_count": 1,
        "police_report_filed": True,
        "witnesses": 1,
        "true_label": False,
        "submission_days_ago": 11,
    },
    {
        "claimant_name": "Laura Martinez",
        "claim_amount": 50000.0,
        "claim_type": "life",
        "incident_date": "2026-09-02",
        "days_to_report": 5,
        "description": "Hospital certified natural cause claim with complete medical record.",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 2,
        "true_label": False,
        "submission_days_ago": 9,
    },

    # Unlabeled Claims (6 claims - delayed label workflow)
    {
        "claimant_name": "Brian Gallagher",
        "claim_amount": 9400.0,
        "claim_type": "auto",
        "incident_date": "2026-09-15",
        "days_to_report": 12,
        "description": "Multi-vehicle pileup on highway, liability currently under investigation.",
        "prior_claims_count": 2,
        "police_report_filed": True,
        "witnesses": 1,
        "true_label": None,
        "submission_days_ago": 7,
    },
    {
        "claimant_name": "Elena Rostova",
        "claim_amount": 16200.0,
        "claim_type": "property",
        "incident_date": "2026-09-16",
        "days_to_report": 18,
        "description": "Basement flooding after heavy rain, inspector assessment pending.",
        "prior_claims_count": 1,
        "police_report_filed": False,
        "witnesses": 0,
        "true_label": None,
        "submission_days_ago": 6,
    },
    {
        "claimant_name": "Kevin Patel",
        "claim_amount": 11500.0,
        "claim_type": "health",
        "incident_date": "2026-09-18",
        "days_to_report": 8,
        "description": "Surgical consultation and follow-up MRI awaiting hospital billing confirmation.",
        "prior_claims_count": 2,
        "police_report_filed": False,
        "witnesses": 1,
        "true_label": None,
        "submission_days_ago": 5,
    },
    {
        "claimant_name": "Olivia Taylor",
        "claim_amount": 7800.0,
        "claim_type": "auto",
        "incident_date": "2026-09-20",
        "days_to_report": 5,
        "description": "Hit-and-run while vehicle was parked overnight.",
        "prior_claims_count": 1,
        "police_report_filed": True,
        "witnesses": 0,
        "true_label": None,
        "submission_days_ago": 4,
    },
    {
        "claimant_name": "Carlos Mendez",
        "claim_amount": 22400.0,
        "claim_type": "property",
        "incident_date": "2026-09-22",
        "days_to_report": 14,
        "description": "Vandalism and property loss at commercial storefront.",
        "prior_claims_count": 2,
        "police_report_filed": True,
        "witnesses": 1,
        "true_label": None,
        "submission_days_ago": 2,
    },
    {
        "claimant_name": "Hannah White",
        "claim_amount": 75000.0,
        "claim_type": "life",
        "incident_date": "2026-09-24",
        "days_to_report": 10,
        "description": "Accidental death claim, awaiting coroner final report.",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 1,
        "true_label": None,
        "submission_days_ago": 1,
    },
]

def _model_fields_for(item: dict) -> dict:
    """Explicit, label-consistent values for the 7 real-data model features.

    Seed claims are demo data: they must still carry the full required model
    input set explicitly (never fabricated at the prediction boundary).
    """
    if item["true_label"] is True:
        return {
            "fault": 1,
            "deductible": 500.0,
            "driver_rating": 3,
            "age": 35.0,
            "accident_area": 1,
            "address_change_claim": 2,
            "number_of_suppliments": 4.0,
        }
    if item["true_label"] is False:
        return {
            "fault": 0,
            "deductible": 400.0,
            "driver_rating": 1,
            "age": 45.0,
            "accident_area": 1,
            "address_change_claim": 0,
            "number_of_suppliments": 0.0,
        }
    return {
        "fault": 1,
        "deductible": 400.0,
        "driver_rating": 2,
        "age": 40.0,
        "accident_area": 1,
        "address_change_claim": 0,
        "number_of_suppliments": 0.0,
    }


def seed_database(clear_existing: bool = True):
    if not ml_pipeline.is_trained:
        ml_pipeline.load_or_train()

    if clear_existing:
        db.clear()

    now = datetime.now(timezone.utc)
    created_claims = []

    for item in SEED_CLAIMS_DATA:
        claim_data = {
            "claimant_name": item["claimant_name"],
            "claim_amount": item["claim_amount"],
            "claim_type": item["claim_type"],
            "incident_date": item["incident_date"],
            "days_to_report": item["days_to_report"],
            "description": item["description"],
            "prior_claims_count": item["prior_claims_count"],
            "police_report_filed": item["police_report_filed"],
            "witnesses": item["witnesses"],
            **_model_fields_for(item),
        }

        # Predict score & explanations using the model
        score = ml_pipeline.predict(claim_data)
        explanations = ml_pipeline.explain(claim_data, score)

        risk_level = "low"
        if score > 0.7:
            risk_level = "high"
        elif score >= 0.3:
            risk_level = "medium"

        submission_date = now - timedelta(days=item["submission_days_ago"])

        claim = Claim(
            id=uuid4(),
            **claim_data,
            fraud_score=score,
            risk_level=risk_level,
            explanations=explanations,
            prediction=score > 0.5,
            status="pending",
            submission_date=submission_date,
            true_label=item["true_label"],
        )
        db.add(claim)
        created_claims.append(claim)

    return created_claims
