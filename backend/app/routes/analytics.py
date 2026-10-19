import math
from fastapi import APIRouter
from app.database import db
from collections import defaultdict
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

router = APIRouter()

def _sanitize_metric(val):
    if val is None:
        return None
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return f_val
    except (ValueError, TypeError):
        return None

@router.get("/stats")
def get_stats():
    claims = db.get_all()
    total_claims = len(claims)
    
    if total_claims == 0:
        return {
            "total_claims": 0, "flagged_claims": 0, "avg_fraud_score": 0, 
            "labeled_claims": 0, "pending_claims": 0, "settled_claims": 0, "fraud_rate": 0, "claims_by_type": {}, 
            "claims_by_risk": {"low": 0, "medium": 0, "high": 0}, 
            "recent_claims": []
        }
        
    flagged_claims = sum(1 for c in claims if c.risk_level == "high")
    avg_fraud_score = sum(c.fraud_score for c in claims) / total_claims
    
    labeled_claims = [c for c in claims if c.true_label is not None]
    num_labeled = len(labeled_claims)
    fraud_rate = sum(1 for c in labeled_claims if c.true_label) / num_labeled if num_labeled > 0 else 0
    
    claims_by_type = defaultdict(int)
    claims_by_risk = {"low": 0, "medium": 0, "high": 0}
    
    for c in claims:
        claims_by_type[c.claim_type] += 1
        claims_by_risk[c.risk_level] += 1
        
    return {
        "total_claims": total_claims,
        "flagged_claims": flagged_claims,
        "avg_fraud_score": avg_fraud_score,
        "labeled_claims": num_labeled,
        "settled_claims": num_labeled,
        "pending_claims": total_claims - num_labeled,
        "fraud_rate": fraud_rate,
        "claims_by_type": dict(claims_by_type),
        "claims_by_risk": claims_by_risk,
        "recent_claims": [c.model_dump(mode="json") for c in claims[:5]]
    }

@router.get("/model-performance")
def get_model_performance():
    claims = db.get_labeled()
    
    if not claims:
        return {
            "accuracy": None, "precision": None, "recall": None, "f1_score": None, 
            "roc_auc": None, "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "total_labeled": 0, "total_predictions": db.count(),
            "correct_predictions": 0, "incorrect_predictions": 0
        }
        
    y_true = [1 if c.true_label else 0 for c in claims]
    y_pred = [1 if c.prediction else 0 for c in claims]
    y_score = [c.fraud_score for c in claims]
    
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    auc = None
    if len(set(y_true)) >= 2:
        try:
            auc_val = roc_auc_score(y_true, y_score)
            auc = _sanitize_metric(auc_val)
        except Exception:
            auc = None
        
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    
    tn, fp, fn, tp = 0, 0, 0, 0
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    
    return {
        "accuracy": _sanitize_metric(acc),
        "precision": _sanitize_metric(prec),
        "recall": _sanitize_metric(rec),
        "f1_score": _sanitize_metric(f1),
        "roc_auc": _sanitize_metric(auc),
        "confusion_matrix": {
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)
        },
        "total_labeled": len(claims),
        "total_predictions": db.count(),
        # Settled claims only: the ORIGINAL stored prediction vs the later ground truth.
        "correct_predictions": sum(1 for t, p in zip(y_true, y_pred) if t == p),
        "incorrect_predictions": sum(1 for t, p in zip(y_true, y_pred) if t != p),
    }