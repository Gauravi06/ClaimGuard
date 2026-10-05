"""R1: build backend/data/claims_sim.csv from the Kaggle auto insurance claims CSV.

Run from the repo root:
    python backend/app/pipeline/prepare_data.py
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_PATH = DATA_DIR / "insurance_claims.csv"
OUT_PATH = DATA_DIR / "claims_sim.csv"

FEATURES = [
    "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
    "incident_severity", "witnesses", "police_report_available",
    "bodily_injuries", "number_of_vehicles_involved", "policy_annual_premium",
    "months_as_customer", "age", "umbrella_limit",
]
REQUIRED = ["incident_date", "fraud_reported"] + FEATURES

SEVERITY_MAP = {
    "trivial damage": 0,
    "minor damage": 1,
    "major damage": 2,
    "total loss": 3,
}
POLICE_MAP = {"yes": "1", "no": "0", "?": "unknown"}


def build() -> pd.DataFrame:
    if not RAW_PATH.exists():
        sys.exit(f"ERROR: raw file not found: {RAW_PATH}")

    raw = pd.read_csv(RAW_PATH)

    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        sys.exit(f"ERROR: missing columns in {RAW_PATH.name}: {missing}\n"
                 f"Found: {list(raw.columns)}")

    df = raw[REQUIRED].copy()

    # Metadata and label
    df["filed_at"] = pd.to_datetime(df["incident_date"], errors="coerce")
    bad_dates = df["filed_at"].isna().sum()
    if bad_dates:
        print(f"WARNING: dropping {bad_dates} rows with unparseable incident_date")
        df = df[df["filed_at"].notna()].copy()

    fraud = df["fraud_reported"].astype(str).str.strip().str.upper()
    unknown_labels = set(fraud) - {"Y", "N"}
    if unknown_labels:
        sys.exit(f"ERROR: unexpected fraud_reported values: {unknown_labels}")
    df["is_fraud"] = (fraud == "Y").astype(int)

    # Categorical encodings
    sev = df["incident_severity"].astype(str).str.strip().str.lower()
    df["incident_severity"] = sev.map(SEVERITY_MAP)
    if df["incident_severity"].isna().any():
        bad = sorted(set(sev[df["incident_severity"].isna()]))
        sys.exit(f"ERROR: unexpected incident_severity values: {bad}")

    police = df["police_report_available"].astype(str).str.strip().str.lower()
    df["police_report_available"] = police.map(POLICE_MAP).fillna("unknown")

    # Numeric columns: coerce, then fill any gaps with the median
    num_cols = [c for c in FEATURES
                if c not in ("incident_severity", "police_report_available")]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df[c].fillna(df[c].median())

    # Order by filing date, then assign ids so CLM-0001 is the earliest claim
    df = df.sort_values("filed_at", ascending=True).reset_index(drop=True)
    df["claim_id"] = [f"CLM-{i+1:04d}" for i in range(len(df))]

    # Investigation window 10-30 days, seed 42
    np.random.seed(42)
    df["investigation_days"] = np.random.randint(10, 31, size=len(df))
    df["label_available_at"] = (df["filed_at"] + pd.to_timedelta(df["investigation_days"], unit="D")).dt.strftime("%Y-%m-%d")
    df["filed_at"] = df["filed_at"].dt.strftime("%Y-%m-%d")

    out_cols = ["claim_id", "filed_at", "investigation_days", "label_available_at", "is_fraud"] + FEATURES
    df = df[out_cols]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Successfully generated {len(df)} simulation claims at {OUT_PATH}")
    return df


if __name__ == "__main__":
    build()
