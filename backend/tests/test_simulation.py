"""
backend/tests/test_simulation.py
Unit and data leakage tests for simulation layer (R3).
"""
import pytest
from datetime import date, timedelta
import pandas as pd
import numpy as np

from app.pipeline.simulation import get_settled, get_pending, _df_pool


def test_claim_pending_before_label_available_at():
    """
    R3 Req 2: Test that a claim is pending before its label_available_at date.
    """
    first_claim = _df_pool.iloc[0]
    claim_id = first_claim["claim_id"]
    filed_at = first_claim["filed_at"]
    label_available_at = first_claim["label_available_at"]

    as_of = filed_at + timedelta(days=1)
    assert as_of < label_available_at

    df_pending = get_pending(as_of)
    df_settled = get_settled(as_of)

    assert claim_id in df_pending["claim_id"].values
    assert claim_id not in df_settled["claim_id"].values


def test_claim_settled_on_and_after_label_available_at():
    """
    R3 Req 3: Test that the same claim becomes settled on label_available_at and remains settled after it.
    """
    first_claim = _df_pool.iloc[0]
    claim_id = first_claim["claim_id"]
    label_available_at = first_claim["label_available_at"]

    # On label_available_at
    df_settled_on = get_settled(label_available_at)
    df_pending_on = get_pending(label_available_at)

    assert claim_id in df_settled_on["claim_id"].values
    assert claim_id not in df_pending_on["claim_id"].values

    # After label_available_at
    after_date = label_available_at + timedelta(days=10)
    df_settled_after = get_settled(after_date)
    df_pending_after = get_pending(after_date)

    assert claim_id in df_settled_after["claim_id"].values
    assert claim_id not in df_pending_after["claim_id"].values


def test_pending_claims_do_not_contain_leakage_columns():
    """
    R3 Req 4: Test that pending claims do NOT contain is_fraud, investigation_days, or label_available_at.
    """
    forbidden_columns = {"is_fraud", "investigation_days", "label_available_at"}

    test_dates = [date(2015, 1, 5), date(2015, 1, 20), date(2015, 2, 1), date(2015, 2, 15)]
    for as_of in test_dates:
        df_pending = get_pending(as_of)
        assert isinstance(df_pending, pd.DataFrame)
        present_forbidden = forbidden_columns.intersection(df_pending.columns)
        assert len(present_forbidden) == 0, f"Pending claims contained leakage columns: {present_forbidden}"


def test_no_claim_in_both_settled_and_pending():
    """
    R3 Req 5: Test that no claim appears in both settled and pending for the same as_of date.
    """
    test_dates = [
        date(2015, 1, 1),
        date(2015, 1, 10),
        date(2015, 1, 20),
        date(2015, 2, 1),
        date(2015, 2, 15),
        date(2015, 3, 1),
    ]
    for as_of in test_dates:
        settled_ids = set(get_settled(as_of)["claim_id"])
        pending_ids = set(get_pending(as_of)["claim_id"])
        intersection = settled_ids.intersection(pending_ids)
        assert len(intersection) == 0, f"Claims {intersection} present in both settled and pending on {as_of}"


def test_reproducible_investigation_delays_with_seed():
    """
    R3 Req 6: Test that using the same seed (42) produces the exact same investigation delays.
    """
    np.random.seed(42)
    expected_delays = np.random.randint(10, 31, size=len(_df_pool))
    
    actual_delays = _df_pool["investigation_days"].values
    np.testing.assert_array_equal(expected_delays, actual_delays)
