"""
backend/app/pipeline/drift.py
Feature drift detection using Population Stability Index (PSI) (Task R3).

Compares feature distributions of the baseline settled claims (from the last model retrain)
against recent claims filed in the 14 days prior to as_of (pending or settled).
Never exposes or uses label columns.
"""
from datetime import date
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from app.pipeline import simulation
from app.pipeline.state import state

FEATURES: List[str] = [
    "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
    "incident_severity", "witnesses", "police_report_available",
    "bodily_injuries", "number_of_vehicles_involved", "policy_annual_premium",
    "months_as_customer", "age", "umbrella_limit",
]


def psi(expected: Any, actual: Any, bins: int = 10, epsilon: float = 1e-4) -> float:
    """
    Calculate Population Stability Index (PSI) between expected and actual distributions.
    Handles numeric arrays with binning, and categorical arrays with discrete frequency counts.
    Empty bins are smoothed with epsilon to avoid division by zero or log of zero.
    """
    exp_arr = np.asarray(expected)
    act_arr = np.asarray(actual)

    if len(exp_arr) == 0 or len(act_arr) == 0:
        return 0.0

    # Determine if values are numeric
    try:
        exp_num = np.asarray(expected, dtype=float)
        act_num = np.asarray(actual, dtype=float)
        is_numeric = True
    except (ValueError, TypeError):
        is_numeric = False

    if is_numeric:
        exp_num = exp_num[~np.isnan(exp_num)]
        act_num = act_num[~np.isnan(act_num)]
        if len(exp_num) == 0 or len(act_num) == 0:
            return 0.0

        min_val, max_val = float(np.min(exp_num)), float(np.max(exp_num))
        if min_val == max_val:
            prop_act = float(np.mean(act_num == min_val))
            if prop_act == 1.0:
                return 0.0
            exp_p = np.array([1.0, epsilon], dtype=float)
            act_p = np.array([max(prop_act, epsilon), max(1.0 - prop_act, epsilon)], dtype=float)
            exp_p /= np.sum(exp_p)
            act_p /= np.sum(act_p)
            return float(round(np.sum((act_p - exp_p) * np.log(act_p / exp_p)), 4))

        percentiles = np.linspace(0, 100, bins + 1)
        bin_edges = np.unique(np.percentile(exp_num, percentiles))
        if len(bin_edges) < 2:
            bin_edges = np.linspace(min_val, max_val, bins + 1)
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        exp_counts, _ = np.histogram(exp_num, bins=bin_edges)
        act_counts, _ = np.histogram(act_num, bins=bin_edges)
    else:
        exp_cat = np.asarray(expected, dtype=str)
        act_cat = np.asarray(actual, dtype=str)
        categories = np.unique(np.concatenate([exp_cat, act_cat]))
        if len(categories) == 0:
            return 0.0
        exp_counts = np.array([np.sum(exp_cat == c) for c in categories], dtype=float)
        act_counts = np.array([np.sum(act_cat == c) for c in categories], dtype=float)

    exp_pct = np.where(exp_counts == 0, epsilon, exp_counts / float(len(exp_arr)))
    act_pct = np.where(act_counts == 0, epsilon, act_counts / float(len(act_arr)))
    exp_pct /= np.sum(exp_pct)
    act_pct /= np.sum(act_pct)

    psi_val = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return float(round(psi_val, 4))


def compute_drift(as_of: Optional[date] = None) -> Dict[str, Any]:
    """
    Compare feature distribution of claims used in the last training (the settled claims
    at the last retrain) against recent claims (all claims filed in the 14 days before as_of).
    Uses ONLY the 13 contract feature columns, never label columns.
    Returns:
        as_of: ISO date string
        status: "no model yet" | "ok" (<0.10) | "warn" (0.10-0.25) | "alert" (>0.25)
        max_psi: float or None
        features: list of {"name": str, "psi": float}
    """
    if as_of is None:
        as_of = state.simulated_date

    # If no model trained yet, return status "no model yet"
    if state.model_version == 0 or state.latest_metrics is None:
        return {
            "as_of": as_of.isoformat(),
            "status": "no model yet",
            "max_psi": None,
            "features": []
        }

    # Reference data: settled claims used at last retrain
    last_train_as_of_str = state.latest_metrics.get("as_of")
    if last_train_as_of_str:
        last_train_date = date.fromisoformat(last_train_as_of_str)
    else:
        last_train_date = as_of

    expected_df = simulation.get_settled(last_train_date)
    recent_df = simulation.get_recent_claims(as_of, days=14)

    if expected_df.empty or recent_df.empty:
        return {
            "as_of": as_of.isoformat(),
            "status": "ok",
            "max_psi": 0.0,
            "features": [{"name": f, "psi": 0.0} for f in FEATURES]
        }

    feature_results = []
    psi_values = []

    for feat in FEATURES:
        if feat in expected_df.columns and feat in recent_df.columns:
            feat_psi = psi(expected_df[feat].values, recent_df[feat].values)
        else:
            feat_psi = 0.0
        feature_results.append({"name": feat, "psi": feat_psi})
        psi_values.append(feat_psi)

    max_psi = max(psi_values) if psi_values else 0.0

    if max_psi > 0.25:
        status = "alert"
    elif max_psi >= 0.10:
        status = "warn"
    else:
        status = "ok"

    return {
        "as_of": as_of.isoformat(),
        "status": status,
        "max_psi": round(max_psi, 4),
        "features": feature_results
    }
