"""
backend/app/pipeline/simulation.py
Data querying logic for simulation (S2).
Reads backend/data/claims_sim.csv.
"""
from pathlib import Path
from datetime import date
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SIM_CSV_PATH = DATA_DIR / "claims_sim.csv"

def _load_claims_pool() -> pd.DataFrame:
    if SIM_CSV_PATH.exists():
        df = pd.read_csv(SIM_CSV_PATH)
    else:
        from .prepare_data import build
        df = build()
    
    df["filed_at"] = pd.to_datetime(df["filed_at"]).dt.date
    df["label_available_at"] = pd.to_datetime(df["label_available_at"]).dt.date
    return df

_df_pool = _load_claims_pool()

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
