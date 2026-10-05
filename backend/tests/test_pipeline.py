import pytest
from datetime import date
import pandas as pd
from app.pipeline import get_settled, get_pending, train_and_log, score_claims

def test_get_settled_columns_and_shapes():
    as_of = date(2015, 3, 1)
    df_settled = get_settled(as_of)
    
    assert isinstance(df_settled, pd.DataFrame)
    
    # Verify exact columns exist
    expected_cols = {
        "claim_id", "filed_at", "investigation_days", "label_available_at", "is_fraud",
        "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
        "incident_severity", "witnesses", "police_report_available",
        "bodily_injuries", "number_of_vehicles_involved", "policy_annual_premium",
        "months_as_customer", "age", "umbrella_limit"
    }
    assert set(df_settled.columns) == expected_cols
    
    # label_available_at <= as_of
    assert all(df_settled["label_available_at"] <= as_of)

def test_get_pending_columns_and_shapes():
    as_of = date(2015, 3, 1)
    df_pending = get_pending(as_of)
    
    assert isinstance(df_pending, pd.DataFrame)
    
    # Must NOT contain label columns
    assert "is_fraud" not in df_pending.columns
    assert "label_available_at" not in df_pending.columns
    assert "investigation_days" not in df_pending.columns
    
    # Should contain all feature columns
    expected_features = {
        "claim_id", "filed_at", 
        "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
        "incident_severity", "witnesses", "police_report_available",
        "bodily_injuries", "number_of_vehicles_involved", "policy_annual_premium",
        "months_as_customer", "age", "umbrella_limit"
    }
    assert set(df_pending.columns) == expected_features
    
    # filed_at <= as_of
    assert all(df_pending["filed_at"] <= as_of)

def test_score_claims():
    df = pd.DataFrame([{"claim_id": 1}, {"claim_id": 2}, {"claim_id": 3}])
    scores = score_claims(df)
    
    # One probability per row
    assert len(scores) == 3
    # Between 0 and 1
    assert all(0 <= s <= 1 for s in scores)
    
    # Deterministic check
    scores2 = score_claims(df)
    assert scores == scores2

def test_train_and_log():
    as_of = date(2015, 3, 1)
    res = train_and_log(as_of)
    
    # Check structure exactly
    assert res["run_id"] == "dummy_run_12345"
    assert res["as_of"] == "2015-03-01"
    assert isinstance(res["n_train"], int)
    assert isinstance(res["n_pending"], int)
    assert isinstance(res["model_version"], int)
    
    metrics = res["metrics"]
    assert isinstance(metrics["precision"], float)
    assert isinstance(metrics["recall"], float)
    assert isinstance(metrics["f1"], float)
    assert isinstance(metrics["pr_auc"], float)
