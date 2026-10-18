"""
backend/app/pipeline/training.py
Training, evaluation, model selection, and scoring for ClaimGuard (R4).
"""
import uuid
from datetime import date
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score
from sklearn.model_selection import train_test_split

from app.pipeline.simulation import get_settled, get_pending
from app.pipeline.tracking import log_training_run

FEATURES = [
    "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim",
    "incident_severity", "witnesses", "police_report_available",
    "bodily_injuries", "number_of_vehicles_involved", "policy_annual_premium",
    "months_as_customer", "age", "umbrella_limit",
]

CATEGORICAL_FEATURES = ["police_report_available"]
NUMERICAL_FEATURES = [c for c in FEATURES if c not in CATEGORICAL_FEATURES]

# In-memory storage for current model state
_current_model: Optional[Pipeline] = None
_model_version: int = 0


def _build_preprocessing_pipeline() -> ColumnTransformer:
    """Construct ColumnTransformer for numerical and categorical features."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop"
    )


def _create_model_pipeline(classifier_type: str) -> Pipeline:
    """Create full sklearn Pipeline with preprocessor and specified classifier."""
    preprocessor = _build_preprocessing_pipeline()
    if classifier_type == "rf":
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
    elif classifier_type == "lr":
        clf = LogisticRegression(max_iter=1000, random_state=42)
    else:
        raise ValueError(f"Unknown classifier_type: {classifier_type}")

    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", clf)
    ])


def _split_settled_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split settled data into train and validation sets.
    Prefers chronological split (first 80% train, last 20% validation).
    Falls back to stratified random split if chronological split has insufficient class diversity.
    """
    df_sorted = df.sort_values("filed_at", ascending=True).reset_index(drop=True)
    X = df_sorted[FEATURES]
    y = df_sorted["is_fraud"].astype(int)

    n_samples = len(df)
    if n_samples >= 10:
        split_idx = int(n_samples * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        if len(np.unique(y_train)) > 1 and len(np.unique(y_val)) > 1:
            return X_train, X_val, y_train, y_val

    if len(np.unique(y)) > 1 and n_samples >= 5:
        try:
            return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        except Exception:
            pass

    return X, X, y, y


def train_and_log(as_of: date) -> Dict[str, Any]:
    """
    Train Random Forest and Logistic Regression models on settled claims as of `as_of`.
    Selects the better model based on PR-AUC, updates in-memory model, logs run to MLflow,
    and returns metric summary.
    """
    global _current_model, _model_version

    settled_df = get_settled(as_of)
    pending_df = get_pending(as_of)
    n_pending = len(pending_df)
    n_train = len(settled_df)

    _model_version += 1

    if n_train == 0 or "is_fraud" not in settled_df.columns or len(np.unique(settled_df["is_fraud"])) < 2:
        dummy_metrics = {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "pr_auc": 0.0
        }
        try:
            run_id = log_training_run(
                as_of=as_of.isoformat(),
                n_train=n_train,
                n_pending=n_pending,
                model_version=_model_version,
                metrics=dummy_metrics,
                best_model_name="None",
            )
        except Exception:
            run_id = f"run_{uuid.uuid4().hex[:8]}"

        return {
            "run_id": run_id,
            "as_of": as_of.isoformat(),
            "n_train": n_train,
            "n_pending": n_pending,
            "model_version": _model_version,
            "metrics": dummy_metrics
        }

    X_train, X_val, y_train, y_val = _split_settled_data(settled_df)

    # Train and evaluate Random Forest
    rf_pipe = _create_model_pipeline("rf")
    rf_pipe.fit(X_train, y_train)
    rf_val_probs = rf_pipe.predict_proba(X_val)[:, 1]
    rf_pr_auc = float(average_precision_score(y_val, rf_val_probs)) if len(np.unique(y_val)) > 1 else 0.0

    # Train and evaluate Logistic Regression
    lr_pipe = _create_model_pipeline("lr")
    lr_pipe.fit(X_train, y_train)
    lr_val_probs = lr_pipe.predict_proba(X_val)[:, 1]
    lr_pr_auc = float(average_precision_score(y_val, lr_val_probs)) if len(np.unique(y_val)) > 1 else 0.0

    # Select better model by PR-AUC
    if rf_pr_auc >= lr_pr_auc:
        best_pipe = rf_pipe
        best_val_probs = rf_val_probs
        best_model_name = "RandomForest"
    else:
        best_pipe = lr_pipe
        best_val_probs = lr_val_probs
        best_model_name = "LogisticRegression"

    # Retrain best pipeline structure on ALL settled claims for production scoring
    X_full = settled_df[FEATURES]
    y_full = settled_df["is_fraud"].astype(int)
    best_pipe.fit(X_full, y_full)
    _current_model = best_pipe

    # Compute validation metrics for report
    val_preds = (best_val_probs >= 0.5).astype(int)
    precision = float(precision_score(y_val, val_preds, zero_division=0))
    recall = float(recall_score(y_val, val_preds, zero_division=0))
    f1 = float(f1_score(y_val, val_preds, zero_division=0))
    pr_auc = float(average_precision_score(y_val, best_val_probs)) if len(np.unique(y_val)) > 1 else 0.0

    metrics = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc, 4)
    }

    try:
        run_id = log_training_run(
            as_of=as_of.isoformat(),
            n_train=n_train,
            n_pending=n_pending,
            model_version=_model_version,
            metrics=metrics,
            best_model_name=best_model_name,
        )
    except Exception:
        run_id = f"run_{uuid.uuid4().hex[:8]}"

    return {
        "run_id": run_id,
        "as_of": as_of.isoformat(),
        "n_train": n_train,
        "n_pending": n_pending,
        "model_version": _model_version,
        "metrics": metrics
    }


def score_claims(df: pd.DataFrame) -> list[float]:
    """
    Score claims dataframe using the currently trained in-memory model.
    Returns list of fraud probabilities (class 1).
    """
    global _current_model
    if df.empty:
        return []

    if _current_model is None:
        latest_date = pd.to_datetime(df["filed_at"]).dt.date.max() if "filed_at" in df.columns else date(2015, 3, 1)
        train_and_log(latest_date)

    if _current_model is None:
        return [0.0] * len(df)

    # Ensure required features exist, defaulting missing columns
    df_features = df.copy()
    for col in FEATURES:
        if col not in df_features.columns:
            df_features[col] = "unknown" if col in CATEGORICAL_FEATURES else 0

    probs = _current_model.predict_proba(df_features[FEATURES])[:, 1]
    return [float(p) for p in probs]

