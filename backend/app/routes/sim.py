from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from app.pipeline.state import state, advance
from app.pipeline.simulation import get_pending, get_settled
from app.pipeline.training import score_claims

router = APIRouter(prefix="/api/sim", tags=["Simulation"])
sim_router = router  # Alias for flexible importing

class AdvanceRequest(BaseModel):
    days: int = Field(default=7, description="Number of days to advance the simulation clock")

def get_risk_level(score: float) -> str:
    """
    Risk rules:
    - low < 0.3
    - medium 0.3 to < 0.7
    - high >= 0.7
    """
    if score >= 0.7:
        return "high"
    elif score >= 0.3:
        return "medium"
    return "low"

def get_prediction(score: float) -> bool:
    """Prediction rule: true only when fraud_score > 0.5."""
    return score > 0.5

@router.get("/clock")
def get_clock() -> Dict[str, str]:
    """Return the current simulated clock date."""
    return {
        "simulated_date": state.simulated_date.isoformat()
    }

@router.post("/advance")
def advance_simulation(req: Optional[AdvanceRequest] = None) -> Dict[str, Any]:
    """
    Advance the simulation clock by the specified days (default 7).
    Executes O3 retrain logic and returns simulation state summary.
    """
    days = req.days if req and req.days is not None else 7
    return advance(days=days)

@router.get("/pending")
def get_pending_endpoint() -> Dict[str, Any]:
    """
    Return all pending claims as of the simulated date.
    Pending claims NEVER include is_fraud, investigation_days, or label_available_at.
    """
    as_of = state.simulated_date
    df = get_pending(as_of)

    if df.empty:
        return {
            "as_of": as_of.isoformat(),
            "count": 0,
            "claims": []
        }

    scores = score_claims(df)
    claims_list: List[Dict[str, Any]] = []

    for i, row in enumerate(df.to_dict(orient="records")):
        score = float(scores[i])
        row["fraud_score"] = score
        row["risk_level"] = get_risk_level(score)
        row["prediction"] = get_prediction(score)

        # Enforce contract: pending claims NEVER expose true labels or investigation window
        row.pop("is_fraud", None)
        row.pop("investigation_days", None)
        row.pop("label_available_at", None)

        # Ensure all date/datetime objects are ISO strings
        for k, v in row.items():
            if isinstance(v, (date, datetime)):
                row[k] = v.isoformat()

        claims_list.append(row)

    return {
        "as_of": as_of.isoformat(),
        "count": len(claims_list),
        "claims": claims_list
    }

@router.get("/settled")
def get_settled_endpoint() -> Dict[str, Any]:
    """
    Return all settled claims as of the simulated date.
    Settled claims include true label (is_fraud) and label_available_at.
    """
    as_of = state.simulated_date
    df = get_settled(as_of)

    if df.empty:
        return {
            "as_of": as_of.isoformat(),
            "count": 0,
            "claims": []
        }

    scores = score_claims(df)
    claims_list: List[Dict[str, Any]] = []

    for i, row in enumerate(df.to_dict(orient="records")):
        score = float(scores[i])
        row["fraud_score"] = score
        row["risk_level"] = get_risk_level(score)
        row["prediction"] = get_prediction(score)

        # Ensure all date/datetime objects are ISO strings
        for k, v in row.items():
            if isinstance(v, (date, datetime)):
                row[k] = v.isoformat()

        claims_list.append(row)

    return {
        "as_of": as_of.isoformat(),
        "count": len(claims_list),
        "claims": claims_list
    }

@router.get("/metrics")
def get_metrics_endpoint() -> Dict[str, Any]:
    """
    Return the latest simulation training metrics.
    Handles None gracefully if queried before first model training.
    """
    if state.latest_metrics is None:
        return {
            "model_version": 0,
            "as_of": state.simulated_date.isoformat(),
            "n_train": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "pr_auc": 0.0
        }

    metrics = state.latest_metrics.get("metrics", {})
    return {
        "model_version": state.model_version,
        "as_of": state.latest_metrics.get("as_of", state.simulated_date.isoformat()),
        "n_train": state.latest_metrics.get("n_train", 0),
        "precision": float(metrics.get("precision", 0.0)),
        "recall": float(metrics.get("recall", 0.0)),
        "f1": float(metrics.get("f1", 0.0)),
        "pr_auc": float(metrics.get("pr_auc", 0.0))
    }
