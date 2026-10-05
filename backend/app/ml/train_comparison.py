"""ClaimGuard Model Benchmark & Comparison.

Compares Logistic Regression, Random Forest, and XGBoost on real automobile
claims data using imbalanced-classification metrics (PR-AUC, ROC-AUC, F1, Recall, Precision).

Evaluates models strictly on an untouched test set (stratified 80/20 split)
without data leakage. Outputs comparative results to data/processed/model_comparison.csv.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

# File paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "carclaims_processed.csv"
DEFAULT_COMPARISON_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "model_comparison.csv"
DEFAULT_THRESHOLDS_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "model_thresholds.csv"
DEFAULT_MODEL_ARTIFACT_PATH = PROJECT_ROOT / "data" / "models" / "xgb_champion.joblib"

# Original baseline feature set
BASELINE_FEATURE_COLUMNS = [
    "claim_amount",
    "claim_type_encoded",
    "days_to_report",
    "prior_claims_count",
    "police_report_filed",
    "witnesses",
    "amount_to_avg_ratio",
]

# Newly added features
NEW_FEATURE_COLUMNS = [
    "fault",
    "deductible",
    "driver_rating",
    "age",
    "accident_area",
    "address_change_claim",
    "number_of_suppliments",
]

# Full 14-feature expanded set
EXPANDED_FEATURE_COLUMNS = BASELINE_FEATURE_COLUMNS + NEW_FEATURE_COLUMNS

TARGET_COLUMN = "is_fraud"

EVAL_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]


def load_benchmark_data(
    data_path: Path | str = DEFAULT_PROCESSED_DATA_PATH,
    feature_columns: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Load processed dataset and extract feature matrix and target vector."""
    path = Path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"Processed dataset not found at: {path}")

    features = feature_columns if feature_columns is not None else EXPANDED_FEATURE_COLUMNS

    df = pd.read_csv(path)

    missing_cols = [c for c in features if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required feature columns: {missing_cols}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' missing from dataset")

    X = df[features]
    y = df[TARGET_COLUMN]
    return X, y


def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.20,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Perform stratified train/test split to preserve class distribution."""
    return train_test_split(
        X,
        y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )


def initialize_candidate_models(
    y_train: pd.Series,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Initialize the 3 candidate model architectures.
    
    scale_pos_weight for XGBoost is dynamically computed from training data class ratio.
    Logistic Regression uses a Pipeline with StandardScaler fitted only on train data.
    """
    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos_weight = neg_count / max(1, pos_count)

    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(class_weight="balanced", random_state=random_state, max_iter=1000)),
        ]),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            class_weight="balanced",
            random_state=random_state,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=random_state,
        ),
    }
    return models


def evaluate_model_at_thresholds(
    y_test: pd.Series,
    y_prob: np.ndarray,
    thresholds: List[float] = EVAL_THRESHOLDS,
) -> List[Dict[str, Any]]:
    """Evaluate predictions across a range of decision probability thresholds."""
    results = []
    for threshold in thresholds:
        y_pred = (y_prob >= threshold).astype(int)
        precision = float(precision_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

        results.append({
            "threshold": threshold,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        })
    return results


def run_benchmark(
    data_path: Path | str = DEFAULT_PROCESSED_DATA_PATH,
    output_path: Path | str = DEFAULT_COMPARISON_OUTPUT_PATH,
    thresholds_output_path: Path | str = DEFAULT_THRESHOLDS_OUTPUT_PATH,
    feature_columns: Optional[List[str]] = None,
    random_state: int = 42,
    artifact_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Execute end-to-end model training, evaluation, and comparison."""
    X, y = load_benchmark_data(data_path, feature_columns=feature_columns)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=random_state)

    models = initialize_candidate_models(y_train, random_state=random_state)

    summary_rows = []
    threshold_rows = []
    detailed_metrics = {}

    for name, model in models.items():
        # Train candidate
        model.fit(X_train, y_train)

        # Predict probabilities on untouched test set
        y_prob = model.predict_proba(X_test)[:, 1]

        # Overall ranking metrics
        pr_auc = float(average_precision_score(y_test, y_prob))
        roc_auc = float(roc_auc_score(y_test, y_prob))

        # Threshold evaluations
        thresh_metrics = evaluate_model_at_thresholds(y_test, y_prob, EVAL_THRESHOLDS)

        # Identify best threshold by F1
        best_thresh_entry = max(thresh_metrics, key=lambda m: m["f1"])

        summary_rows.append({
            "Model": name,
            "PR-AUC": round(pr_auc, 4),
            "ROC-AUC": round(roc_auc, 4),
            "Best F1": best_thresh_entry["f1"],
            "Threshold": best_thresh_entry["threshold"],
            "Precision": best_thresh_entry["precision"],
            "Recall": best_thresh_entry["recall"],
        })

        for tm in thresh_metrics:
            threshold_rows.append({
                "Model": name,
                "Threshold": tm["threshold"],
                "Precision": tm["precision"],
                "Recall": tm["recall"],
                "F1": tm["f1"],
                "PR-AUC": round(pr_auc, 4),
                "ROC-AUC": round(roc_auc, 4),
                "TN": tm["tn"],
                "FP": tm["fp"],
                "FN": tm["fn"],
                "TP": tm["tp"],
            })

        detailed_metrics[name] = {
            "pr_auc": pr_auc,
            "roc_auc": roc_auc,
            "best_threshold": best_thresh_entry,
            "all_thresholds": thresh_metrics,
        }

    # Sort summary table by PR-AUC descending (primary benchmark criterion)
    df_summary = pd.DataFrame(summary_rows).sort_values("PR-AUC", ascending=False).reset_index(drop=True)
    df_thresholds = pd.DataFrame(threshold_rows)

    # Save outputs
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(output_path, index=False)

    thresholds_output_path = Path(thresholds_output_path)
    df_thresholds.to_csv(thresholds_output_path, index=False)

    champion = df_summary.iloc[0]["Model"]

    # Save champion model artifact for production serving
    artifact_file = Path(artifact_path or DEFAULT_MODEL_ARTIFACT_PATH)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    champion_model_obj = models[champion]
    joblib.dump({
        "model": champion_model_obj,
        "champion_name": champion,
        "feature_names": list(X.columns),
        "scale_pos_weight": getattr(champion_model_obj, "scale_pos_weight", None),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "metrics": detailed_metrics[champion]["best_threshold"],
        "pr_auc": detailed_metrics[champion]["pr_auc"],
        "roc_auc": detailed_metrics[champion]["roc_auc"],
    }, artifact_file)

    return {
        "features_used": list(X.columns),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "summary_table": df_summary,
        "champion_model": champion,
        "champion_artifact": str(artifact_file),
        "detailed_metrics": detailed_metrics,
        "comparison_file": str(output_path),
        "thresholds_file": str(thresholds_output_path),
    }


def train_and_save_champion(
    data_path: Path | str = DEFAULT_PROCESSED_DATA_PATH,
    artifact_path: Path | str = DEFAULT_MODEL_ARTIFACT_PATH,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Train only the XGBoost champion model and save artifact directly."""
    X, y = load_benchmark_data(data_path)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=random_state)

    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos_weight = neg_count / max(1, pos_count)

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    artifact_file = Path(artifact_path)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "champion_name": "XGBoost",
        "feature_names": list(X.columns),
        "scale_pos_weight": scale_pos_weight,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
    }, artifact_file)

    return {"model": model, "artifact_file": str(artifact_file)}


if __name__ == "__main__":
    print("Executing ClaimGuard Model Benchmark Comparison (14 Features)...")
    res = run_benchmark()
    print("\n--- BENCHMARK RESULTS (Ranked by PR-AUC) ---")
    print(res["summary_table"].to_string(index=False))
    print(f"\nChampion Candidate: {res['champion_model']}")
    print(f"Features ({len(res['features_used'])}): {res['features_used']}")
    print(f"Summary saved to: {res['comparison_file']}")
    print(f"Thresholds saved to: {res['thresholds_file']}")
    print(f"Champion artifact saved to: {res['champion_artifact']}")
