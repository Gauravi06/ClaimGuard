import pandas as pd
from datetime import date, timedelta
import random

# Generate a static pool of claims to act as our database for the stub
_claims = []
_start_date = date(2015, 1, 1)
random.seed(42)

for i in range(1, 101):  # 100 claims total
    filed_at = _start_date + timedelta(days=random.randint(0, 100))
    inv_days = random.randint(10, 30)
    label_available_at = filed_at + timedelta(days=inv_days)
    
    _claims.append({
        "claim_id": f"claim_{i}",
        "filed_at": filed_at,
        "investigation_days": inv_days,
        "label_available_at": label_available_at,
        "is_fraud": random.choice([0, 1]),
        "total_claim_amount": float(random.randint(1000, 100000)),
        "injury_claim": float(random.randint(0, 50000)),
        "property_claim": float(random.randint(0, 50000)),
        "vehicle_claim": float(random.randint(0, 50000)),
        "incident_severity": random.choice(["Minor", "Major", "Total Loss"]),
        "witnesses": random.randint(0, 3),
        "police_report_available": random.choice(["1", "0", "unknown"]),
        "bodily_injuries": random.randint(0, 2),
        "number_of_vehicles_involved": random.randint(1, 4),
        "policy_annual_premium": float(random.uniform(500, 2000)),
        "months_as_customer": random.randint(1, 120),
        "age": random.randint(18, 80),
        "umbrella_limit": float(random.choice([0, 1000000, 5000000]))
    })

_df_pool = pd.DataFrame(_claims)

def get_settled(as_of: date) -> pd.DataFrame:
    """
    Return settled claims where label_available_at <= as_of.
    These claims have labels and all features.
    """
    df = _df_pool[_df_pool["label_available_at"] <= as_of].copy()
    return df.reset_index(drop=True)

def get_pending(as_of: date) -> pd.DataFrame:
    """
    Return pending claims where filed_at <= as_of and label_available_at > as_of.
    These claims MUST NOT contain is_fraud, investigation_days, or label_available_at.
    """
    mask = (_df_pool["filed_at"] <= as_of) & (_df_pool["label_available_at"] > as_of)
    df = _df_pool[mask].copy()
    
    # Remove label/investigation columns for pending claims
    cols_to_drop = ["is_fraud", "investigation_days", "label_available_at"]
    df = df.drop(columns=cols_to_drop, errors="ignore")
    
    return df.reset_index(drop=True)
