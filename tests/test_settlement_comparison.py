"""tests/test_settlement_comparison.py
Unit tests for the settlement-aware vs naive experiment module.
"""

import pandas as pd
import pytest

from experiments.settlement_comparison import (
    load_claims_data,
    run_experiment,
    split_holdout,
)


def test_split_holdout_temporal_ordering():
    """Verify holdout split isolates the most recently filed claims."""
    df = load_claims_data().iloc[:100].copy()
    train_pool, holdout = split_holdout(df, holdout_ratio=0.20)

    assert len(holdout) == 20
    assert len(train_pool) == 80
    assert holdout["filed_at"].min() >= train_pool["filed_at"].min()
    assert set(train_pool["claim_id"]).isdisjoint(set(holdout["claim_id"]))


def test_settlement_comparison_sample_run():
    """Verify run_experiment executes on a 100-row sample and produces expected columns."""
    df = load_claims_data().iloc[:100].copy()

    # Run on the 100-row slice with a lower min_settled threshold for fast test execution
    results = run_experiment(pool_df=df, min_settled=5, holdout_ratio=0.20)

    assert isinstance(results, pd.DataFrame)
    assert not results.empty

    expected_columns = {
        "date",
        "naive_pr_auc",
        "settled_pr_auc",
        "naive_precision",
        "settled_precision",
        "naive_recall",
        "settled_recall",
        "n_settled_train",
        "n_naive_train",
    }
    assert expected_columns.issubset(set(results.columns))

    for _, row in results.iterrows():
        assert 0.0 <= row["naive_pr_auc"] <= 1.0
        assert 0.0 <= row["settled_pr_auc"] <= 1.0
        assert 0.0 <= row["naive_recall"] <= 1.0
        assert 0.0 <= row["settled_recall"] <= 1.0
        assert row["n_settled_train"] > 0
        assert row["n_naive_train"] >= row["n_settled_train"]
