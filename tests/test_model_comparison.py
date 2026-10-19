"""Focused tests for ClaimGuard model benchmark comparison pipeline (expanded features)."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.train_comparison import (
    BASELINE_FEATURE_COLUMNS,
    DEFAULT_COMPARISON_OUTPUT_PATH,
    DEFAULT_PROCESSED_DATA_PATH,
    EXPANDED_FEATURE_COLUMNS,
    NEW_FEATURE_COLUMNS,
    TARGET_COLUMN,
    initialize_candidate_models,
    load_benchmark_data,
    run_benchmark,
    split_data,
)


@pytest.fixture(scope="module")
def benchmark_data():
    """Load benchmark data once for test module."""
    assert DEFAULT_PROCESSED_DATA_PATH.is_file(), f"Missing processed data at {DEFAULT_PROCESSED_DATA_PATH}"
    X, y = load_benchmark_data(DEFAULT_PROCESSED_DATA_PATH)
    return X, y


def test_dataset_loads_and_expected_columns_exist(benchmark_data):
    """Verify that processed dataset loads with all 14 expanded features and target."""
    X, y = benchmark_data
    assert list(X.columns) == EXPANDED_FEATURE_COLUMNS
    assert len(X.columns) == 14
    assert len(X) == 15419
    assert len(y) == 15419
    assert X.isnull().sum().sum() == 0


def test_can_load_baseline_features_subset():
    """Verify that the loader can also load just the original 7 baseline features."""
    X_base, y = load_benchmark_data(DEFAULT_PROCESSED_DATA_PATH, feature_columns=BASELINE_FEATURE_COLUMNS)
    assert list(X_base.columns) == BASELINE_FEATURE_COLUMNS
    assert len(X_base.columns) == 7


def test_stratified_split_preserves_classes(benchmark_data):
    """Verify stratified split maintains consistent class ratio in train and test."""
    X, y = benchmark_data
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=42)

    total_fraud_rate = (y == 1).mean()
    train_fraud_rate = (y_train == 1).mean()
    test_fraud_rate = (y_test == 1).mean()

    # Ratios should be equal to within 0.1% due to stratification
    assert abs(train_fraud_rate - total_fraud_rate) < 0.002
    assert abs(test_fraud_rate - total_fraud_rate) < 0.002
    assert len(X_train) == 12335
    assert len(X_test) == 3084


def test_all_candidate_models_initialize_and_train(benchmark_data):
    """Verify all 3 candidate models train cleanly on the expanded 14-feature training split."""
    X, y = benchmark_data
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=42)

    models = initialize_candidate_models(y_train, random_state=42)
    expected_models = {"Logistic Regression", "Random Forest", "XGBoost"}
    assert set(models.keys()) == expected_models

    for name, model in models.items():
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]
        assert len(probs) == len(X_test)
        assert not np.isnan(probs).any(), f"NaN probabilities in {name}"
        assert (probs >= 0.0).all() and (probs <= 1.0).all(), f"Probabilities out of range in {name}"


def test_benchmark_metrics_are_finite(tmp_path, benchmark_data):
    """Ensure run_benchmark produces finite numeric metrics for all models on 14 features."""
    out_summary = tmp_path / "model_comparison.csv"
    out_thresh = tmp_path / "model_thresholds.csv"

    results = run_benchmark(
        data_path=DEFAULT_PROCESSED_DATA_PATH,
        output_path=out_summary,
        thresholds_output_path=out_thresh,
        random_state=42,
    )

    df_summary = results["summary_table"]
    assert len(df_summary) == 3
    assert len(results["features_used"]) == 14

    for col in ["PR-AUC", "ROC-AUC", "Best F1", "Precision", "Recall"]:
        for val in df_summary[col]:
            assert not math.isnan(val), f"Metric {col} has NaN"
            assert not math.isinf(val), f"Metric {col} has Inf"
            assert 0.0 <= val <= 1.0, f"Metric {col} out of range [0, 1]: {val}"

    # Verify that PR-AUC is notably higher than the previous 7-feature baseline (~0.12)
    assert df_summary.loc[df_summary["Model"] == "XGBoost", "PR-AUC"].iloc[0] > 0.15


def test_comparison_output_contains_all_three_models(tmp_path):
    """Verify that comparison CSV file contains Logistic Regression, Random Forest, and XGBoost."""
    out_summary = tmp_path / "model_comparison.csv"
    out_thresh = tmp_path / "model_thresholds.csv"

    results = run_benchmark(
        data_path=DEFAULT_PROCESSED_DATA_PATH,
        output_path=out_summary,
        thresholds_output_path=out_thresh,
        random_state=42,
    )

    assert out_summary.is_file()
    df_saved = pd.read_csv(out_summary)

    saved_models = set(df_saved["Model"])
    assert saved_models == {"Logistic Regression", "Random Forest", "XGBoost"}

    # Top model should match champion_model
    assert df_saved.iloc[0]["Model"] == results["champion_model"]
    # Table should be sorted descending by PR-AUC
    assert df_saved["PR-AUC"].is_monotonic_decreasing
