"""ClaimGuard Real-Data Ingestion Pipeline.

Loads, cleans, and transforms raw insurance claim data from data/raw/carclaims.csv
into a standardized, reproducible dataset for ClaimGuard model training and evaluation.

Adheres strictly to ClaimGuard data contracts:
- Raw CSV is treated as read-only and never modified.
- Outputs cleaned dataset to data/processed/carclaims_processed.csv.
- Extracts both the original 7 baseline features and 7 expanded features.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

# Standard paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "carclaims.csv"
DEFAULT_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "carclaims_processed.csv"

# -------------------------------------------------------------------------
# Feature Mapping Dictionaries
# -------------------------------------------------------------------------

BINARY_MAP = {
    "No": 0,
    "Yes": 1,
}

# Ordinal mapping for PastNumberOfClaims (string bin -> representative integer count)
PAST_CLAIMS_MAP = {
    "none": 0,
    "1": 1,
    "2 to 4": 3,
    "more than 4": 5,
}

# Ordinal mapping for VehiclePrice (bracket string -> bracket dollar midpoint)
VEHICLE_PRICE_MAP = {
    "less than 20,000": 15000.0,
    "20,000 to 29,000": 24500.0,
    "30,000 to 39,000": 34500.0,
    "40,000 to 59,000": 49500.0,
    "60,000 to 69,000": 64500.0,
    "more than 69,000": 75000.0,
}

# Ordinal mapping for Days:Policy-Claim (bracket string -> representative elapsed days)
DAYS_POLICY_CLAIM_MAP = {
    "none": 0,
    "8 to 15": 11,
    "15 to 30": 22,
    "more than 30": 45,
}

# Vehicle category to ClaimGuard claim_type_encoded (auto line)
VEHICLE_CATEGORY_MAP = {
    "Sedan": 0,
    "Sport": 1,
    "Utility": 2,
}

# Binary mapping for Fault (Third Party = 0, Policy Holder = 1)
FAULT_MAP = {
    "Third Party": 0,
    "Policy Holder": 1,
}

# Binary mapping for AccidentArea (Rural = 0, Urban = 1)
ACCIDENT_AREA_MAP = {
    "Rural": 0,
    "Urban": 1,
}

# Ordinal mapping for AddressChange-Claim ordered by recency / fraud risk
ADDRESS_CHANGE_MAP = {
    "no change": 0,
    "4 to 8 years": 1,
    "2 to 3 years": 2,
    "1 year": 3,
    "under 6 months": 4,
}

# Numeric midpoint mapping for NumberOfSuppliments
SUPPLIMENTS_MAP = {
    "none": 0.0,
    "1 to 2": 1.5,
    "3 to 5": 4.0,
    "more than 5": 6.0,
}

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

DAY_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}

# -------------------------------------------------------------------------
# Feature Sets & Contract Columns
# -------------------------------------------------------------------------

BASELINE_FEATURE_COLUMNS = [
    "claim_amount",
    "claim_type_encoded",
    "days_to_report",
    "prior_claims_count",
    "police_report_filed",
    "witnesses",
    "amount_to_avg_ratio",
]

NEW_FEATURE_COLUMNS = [
    "fault",
    "deductible",
    "driver_rating",
    "age",
    "accident_area",
    "address_change_claim",
    "number_of_suppliments",
]

MODEL_FEATURE_COLUMNS = BASELINE_FEATURE_COLUMNS + NEW_FEATURE_COLUMNS

CONTRACT_COLUMNS = [
    "claim_id",
    "filed_at",
    "investigation_days",
    "label_available_at",
    "is_fraud",
] + MODEL_FEATURE_COLUMNS


def compute_file_hash(path: Path | str) -> str:
    """Compute MD5 hash of a file for integrity verification."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def construct_filed_at(row: pd.Series) -> Optional[str]:
    """Construct an approximate ISO date for filed_at.
    
    Synthesizes a calendar date from Year, MonthClaimed, WeekOfMonthClaimed,
    and DayOfWeekClaimed. Handles December-to-January calendar rollover.
    Returns 'YYYY-MM-DD' or None if unparseable.
    """
    month_claimed_str = str(row.get("MonthClaimed", "")).strip()
    day_claimed_str = str(row.get("DayOfWeekClaimed", "")).strip()

    if month_claimed_str not in MONTH_MAP or day_claimed_str not in DAY_MAP:
        return None

    try:
        yr = int(row["Year"])
        mo = MONTH_MAP[month_claimed_str]

        # Year rollover check: incident in Dec, claim filed in Jan
        acc_month_str = str(row.get("Month", "")).strip()
        acc_mo = MONTH_MAP.get(acc_month_str, mo)
        if acc_mo == 12 and mo == 1:
            yr += 1

        target_weekday = DAY_MAP[day_claimed_str]
        week_num = max(1, min(5, int(row.get("WeekOfMonthClaimed", 1))))

        first_day = datetime(yr, mo, 1)
        first_weekday = first_day.weekday()
        days_to_target = (target_weekday - first_weekday) % 7
        target_date = first_day + timedelta(days=days_to_target + (week_num - 1) * 7)
        return target_date.strftime("%Y-%m-%d")
    except Exception:
        return None


def load_raw_dataset(raw_path: Path | str = DEFAULT_RAW_PATH) -> pd.DataFrame:
    """Read the raw CSV into a DataFrame in read-only mode."""
    path = Path(raw_path)
    if not path.is_file():
        raise FileNotFoundError(f"Raw dataset not found at: {path}")
    return pd.read_csv(path)


def process_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the raw car claims DataFrame into the ClaimGuard format.
    
    Guarantees:
    1. Removes sentinel '0' invalid date row(s).
    2. Imputes Age == 0 sensibly (assigned to 16.5 for minor category '16 to 17').
    3. Maps binary and ordinal columns to standard numeric representations.
    4. Computes amount_to_avg_ratio based on category empirical means.
    5. Retains NULL/None for investigation timestamps.
    """
    df = df_raw.copy()

    # 1. Clean invalid claim-date rows (sentinel '0' values)
    valid_mask = (df["MonthClaimed"] != "0") & (df["DayOfWeekClaimed"] != "0")
    df = df[valid_mask].copy()

    # 2. Target mapping
    df["is_fraud"] = df["FraudFound"].map(BINARY_MAP).astype(int)

    # 3. Baseline 7 feature mappings
    df["police_report_filed"] = df["PoliceReportFiled"].map(BINARY_MAP).astype(int)
    df["witnesses"] = df["WitnessPresent"].map(BINARY_MAP).astype(int)
    df["prior_claims_count"] = df["PastNumberOfClaims"].map(PAST_CLAIMS_MAP).astype(int)
    df["claim_amount"] = df["VehiclePrice"].map(VEHICLE_PRICE_MAP).astype(float)
    df["days_to_report"] = df["Days:Policy-Claim"].map(DAYS_POLICY_CLAIM_MAP).astype(int)
    df["claim_type_encoded"] = df["VehicleCategory"].map(VEHICLE_CATEGORY_MAP).astype(int)

    # Amount to category average ratio
    category_means = df.groupby("claim_type_encoded")["claim_amount"].transform("mean")
    df["amount_to_avg_ratio"] = (df["claim_amount"] / category_means).round(4)

    # 4. Expanded 7 feature mappings
    df["fault"] = df["Fault"].map(FAULT_MAP).astype(int)
    df["deductible"] = df["Deductible"].astype(float)
    df["driver_rating"] = df["DriverRating"].astype(int)
    df["age"] = df["Age"].apply(lambda a: 16.5 if a == 0 else float(a))
    df["accident_area"] = df["AccidentArea"].map(ACCIDENT_AREA_MAP).astype(int)
    df["address_change_claim"] = df["AddressChange-Claim"].map(ADDRESS_CHANGE_MAP).astype(int)
    df["number_of_suppliments"] = df["NumberOfSuppliments"].map(SUPPLIMENTS_MAP).astype(float)

    # 5. Temporal and lifecycle fields
    df["claim_id"] = df["PolicyNumber"].astype(int)
    df["filed_at"] = df.apply(construct_filed_at, axis=1)

    # Explicitly set investigation fields to None (dataset lacks investigation logs)
    df["investigation_days"] = None
    df["label_available_at"] = None

    # Return standardized contract columns
    return df[CONTRACT_COLUMNS].copy()


def validate_processed_dataframe(
    df_processed: pd.DataFrame,
    raw_path: Path | str,
    expected_raw_hash: str,
) -> Dict[str, Any]:
    """Validate processed dataset against integrity constraints."""
    current_raw_hash = compute_file_hash(raw_path)
    if current_raw_hash != expected_raw_hash:
        raise ValueError("CRITICAL: Raw dataset was modified during processing!")

    # Check for NaNs in model features
    feature_nans = df_processed[MODEL_FEATURE_COLUMNS].isnull().sum().to_dict()
    has_feature_nans = any(count > 0 for count in feature_nans.values())
    if has_feature_nans:
        raise ValueError(f"Processed features contain unexpected NaNs: {feature_nans}")

    # Check target values
    unique_targets = set(df_processed["is_fraud"].unique())
    if not unique_targets.issubset({0, 1}):
        raise ValueError(f"Target contains invalid values: {unique_targets}")

    fraud_count = int((df_processed["is_fraud"] == 1).sum())
    legit_count = int((df_processed["is_fraud"] == 0).sum())
    total_rows = len(df_processed)

    return {
        "raw_hash_verified": True,
        "total_rows": total_rows,
        "fraud_count": fraud_count,
        "legit_count": legit_count,
        "fraud_ratio": round(fraud_count / total_rows, 4),
        "feature_nans": feature_nans,
    }


def ingest_real_data(
    raw_path: Path | str = DEFAULT_RAW_PATH,
    processed_path: Path | str = DEFAULT_PROCESSED_PATH,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Complete ingestion pipeline: loads raw, transforms, validates, and saves.
    
    Returns:
        (processed_dataframe, validation_summary)
    """
    raw_path = Path(raw_path)
    processed_path = Path(processed_path)

    # 1. Capture initial raw file hash to guarantee immutability
    raw_hash_before = compute_file_hash(raw_path)

    # 2. Load and process
    df_raw = load_raw_dataset(raw_path)
    df_processed = process_dataset(df_raw)

    # 3. Validate
    summary = validate_processed_dataframe(df_processed, raw_path, raw_hash_before)

    # 4. Save to processed CSV
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df_processed.to_csv(processed_path, index=False)

    return df_processed, summary


if __name__ == "__main__":
    print("Executing ClaimGuard Real-Data Ingestion Pipeline (Expanded Features)...")
    df_clean, metrics = ingest_real_data()
    print("--- INGESTION COMPLETE ---")
    print(f"Processed Rows: {metrics['total_rows']}")
    print(f"Legitimate Claims: {metrics['legit_count']}")
    print(f"Fraud Claims: {metrics['fraud_count']} ({metrics['fraud_ratio']*100:.2f}%)")
    print(f"Total Model Features: {len(MODEL_FEATURE_COLUMNS)}")
    print(f"Features: {MODEL_FEATURE_COLUMNS}")
    print(f"Raw File Intact: {metrics['raw_hash_verified']}")
    print(f"Feature NaNs: {metrics['feature_nans']}")
    print(f"Saved to: {DEFAULT_PROCESSED_PATH}")
