"""Tests for ClaimGuard real-data loader pipeline (expanded feature set)."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.real_data_loader import (
    BASELINE_FEATURE_COLUMNS,
    CONTRACT_COLUMNS,
    DEFAULT_PROCESSED_PATH,
    DEFAULT_RAW_PATH,
    MODEL_FEATURE_COLUMNS,
    NEW_FEATURE_COLUMNS,
    compute_file_hash,
    ingest_real_data,
    load_raw_dataset,
    process_dataset,
    validate_processed_dataframe,
)


@pytest.fixture(scope="module")
def raw_data_path():
    assert DEFAULT_RAW_PATH.is_file(), f"Raw data file missing at: {DEFAULT_RAW_PATH}"
    return DEFAULT_RAW_PATH


@pytest.fixture(scope="module")
def raw_data_hash(raw_data_path):
    return compute_file_hash(raw_data_path)


@pytest.fixture(scope="module")
def processed_result(raw_data_path):
    df_raw = load_raw_dataset(raw_data_path)
    return process_dataset(df_raw)


def test_raw_csv_immutability(raw_data_path, raw_data_hash):
    """Ensure raw CSV has not been modified or corrupted."""
    current_hash = compute_file_hash(raw_data_path)
    assert current_hash == raw_data_hash, "Raw carclaims.csv was modified!"


def test_processed_row_count(processed_result):
    """Ensure exactly 1 invalid row (sentinel 0) is dropped from 15,420 rows."""
    assert len(processed_result) == 15419


def test_contract_columns_exist(processed_result):
    """Verify that all required ClaimGuard contract columns are present."""
    assert list(processed_result.columns) == CONTRACT_COLUMNS
    assert len(MODEL_FEATURE_COLUMNS) == 14
    assert len(BASELINE_FEATURE_COLUMNS) == 7
    assert len(NEW_FEATURE_COLUMNS) == 7


def test_no_nans_in_model_features(processed_result):
    """Verify zero NaN values across all 14 model features."""
    for col in MODEL_FEATURE_COLUMNS:
        assert processed_result[col].isnull().sum() == 0, f"NaN values found in feature: {col}"


def test_expanded_features_values_and_bounds(processed_result):
    """Verify newly added features are correctly mapped and within expected bounds."""
    # fault: binary 0/1
    assert set(processed_result["fault"].unique()).issubset({0, 1})

    # accident_area: binary 0/1
    assert set(processed_result["accident_area"].unique()).issubset({0, 1})

    # deductible: positive numeric values
    assert set(processed_result["deductible"].unique()).issubset({300.0, 400.0, 500.0, 700.0})

    # driver_rating: 1 to 4
    assert set(processed_result["driver_rating"].unique()).issubset({1, 2, 3, 4})

    # age: positive, Age==0 was imputed to 16.5
    assert (processed_result["age"] > 0).all()
    assert (processed_result["age"] >= 16.0).all()
    assert 16.5 in processed_result["age"].values

    # address_change_claim: ordinal 0 to 4
    assert set(processed_result["address_change_claim"].unique()).issubset({0, 1, 2, 3, 4})

    # number_of_suppliments: non-negative numeric
    assert (processed_result["number_of_suppliments"] >= 0.0).all()


def test_target_is_binary(processed_result):
    """Ensure is_fraud contains strictly 0 and 1, with expected fraud distribution."""
    unique_vals = set(processed_result["is_fraud"].unique())
    assert unique_vals == {0, 1}
    fraud_count = (processed_result["is_fraud"] == 1).sum()
    legit_count = (processed_result["is_fraud"] == 0).sum()
    assert fraud_count == 923
    assert legit_count == 14496


def test_investigation_fields_are_null(processed_result):
    """Ensure investigation timestamps remain null as dataset contains no investigation logs."""
    assert processed_result["investigation_days"].isnull().all()
    assert processed_result["label_available_at"].isnull().all()


def test_filed_at_format(processed_result):
    """Verify that filed_at is populated with valid YYYY-MM-DD date strings."""
    assert processed_result["filed_at"].isnull().sum() == 0
    # Spot check format
    sample_dates = processed_result["filed_at"].head(100)
    for d in sample_dates:
        assert len(d) == 10
        assert d[4] == "-" and d[7] == "-"


def test_amount_to_avg_ratio_positive(processed_result):
    """Verify amount_to_avg_ratio is positive and correctly computed."""
    assert (processed_result["amount_to_avg_ratio"] > 0).all()


def test_full_pipeline_ingest_reproducible(tmp_path, raw_data_path, raw_data_hash):
    """Test the complete end-to-end ingest function writing to a temp location."""
    out_file = tmp_path / "test_carclaims_processed.csv"
    df_clean, metrics = ingest_real_data(raw_path=raw_data_path, processed_path=out_file)

    assert out_file.exists()
    assert metrics["total_rows"] == 15419
    assert metrics["fraud_count"] == 923
    assert metrics["raw_hash_verified"] is True
    # Verify raw file remains identical
    assert compute_file_hash(raw_data_path) == raw_data_hash
