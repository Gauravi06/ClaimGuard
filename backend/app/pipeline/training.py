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

from app.pipeline import simulation
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
_last_training_fingerprint: Optional[str] = None
_last_training_result: Optional[Dict[str, Any]] = None


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
    elif classifier_type == "xgb":
        from xgboost import XGBClassifier
        clf = XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            eval_metric="logloss"
        )
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


def reset_model() -> None:
    """Reset in-memory model and version for test isolation."""
    global _current_model, _model_version, _last_training_fingerprint, _last_training_result
    _current_model = None
    _model_version = 0
    _last_training_fingerprint = None
    _last_training_result = None


def get_model_version() -> int:
    """Return the currently serving model version."""
    return _model_version


def get_current_model() -> Optional[Pipeline]:
    """Return the currently serving model pipeline."""
    return _current_model


def train_and_log(as_of: date) -> Dict[str, Any]:
    """
    Train RandomForest, LogisticRegression, and XGBoost on settled claims as of `as_of`.
    Evaluates candidates on a time-based holdout test set and applies the promotion rule:
    - Best candidate is selected based on PR-AUC on the holdout.
    - If no model is currently serving (first retrain), candidate is always promoted to v1.
    - If a model is currently serving, both candidate and champion are evaluated on that same holdout;
      candidate is promoted only if its PR-AUC is strictly higher.
    - If not promoted, the currently serving model is kept unchanged and model_version does not increment.
    - model_version reflects the version of the currently serving model.
    - Idempotency: calling twice with same as_of and settled count produces same metrics and does not bump version.
    - Safe error handling: single-class data or exceptions do not crash and preserve model state.
    """
    global _current_model, _model_version, _last_training_fingerprint, _last_training_result

    settled_df = simulation.get_settled(as_of)
    pending_df = simulation.get_pending(as_of)
    n_pending = len(pending_df)
    n_train = len(settled_df)

    # Idempotency guard: return identical metrics if called with identical as_of and settled count
    fingerprint = f"{as_of.isoformat()}_{n_train}"
    if fingerprint == _last_training_fingerprint and _last_training_result is not None:
        return dict(_last_training_result)

    # Single-class data or empty data guard
    unique_classes = np.unique(settled_df["is_fraud"]) if ("is_fraud" in settled_df.columns and not settled_df.empty) else []
    if n_train == 0 or len(unique_classes) < 2:
        reason = "No settled claims to train on" if n_train == 0 else "Settled data contains only one class"
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
            run_id = f"skip_{uuid.uuid4().hex[:8]}"

        result = {
            "run_id": run_id,
            "as_of": as_of.isoformat(),
            "n_train": n_train,
            "n_pending": n_pending,
            "model_version": _model_version,
            "metrics": dummy_metrics,
            "promoted": False,
            "champion_pr_auc": None,
            "candidate_pr_auc": 0.0,
            "best_model": "None",
            "retrained": False,
            "reason": reason,
        }
        _last_training_fingerprint = fingerprint
        _last_training_result = result
        return result

    try:
        X_train, X_val, y_train, y_val = _split_settled_data(settled_df)

        # Train and evaluate 3 candidates: RandomForest, LogisticRegression, XGBoost
        candidates = {}
        candidate_types = [("rf", "RandomForest"), ("lr", "LogisticRegression"), ("xgb", "XGBoost")]
        for ctype, cname in candidate_types:
            pipe = _create_model_pipeline(ctype)
            pipe.fit(X_train, y_train)
            probs = pipe.predict_proba(X_val)[:, 1]
            score = float(average_precision_score(y_val, probs)) if len(np.unique(y_val)) > 1 else 0.0
            candidates[cname] = (score, pipe, probs)

        # Select best candidate by PR-AUC
        best_model_name, (candidate_pr_auc, best_candidate_pipe, best_val_probs) = max(
            candidates.items(), key=lambda item: item[1][0]
        )

        # Promotion check against currently serving model on the same holdout
        if _current_model is None:
            # First model is always promoted to version 1
            promoted = True
            champion_pr_auc = None
            _model_version += 1
            # Fit on all settled claims for serving
            X_full = settled_df[FEATURES]
            y_full = settled_df["is_fraud"].astype(int)
            best_candidate_pipe.fit(X_full, y_full)
            _current_model = best_candidate_pipe
            serving_probs = best_val_probs
        else:
            # Evaluate current serving champion on the same holdout
            champ_probs = _current_model.predict_proba(X_val)[:, 1]
            champion_pr_auc = float(average_precision_score(y_val, champ_probs)) if len(np.unique(y_val)) > 1 else 0.0

            if candidate_pr_auc > champion_pr_auc:
                promoted = True
                _model_version += 1
                X_full = settled_df[FEATURES]
                y_full = settled_df["is_fraud"].astype(int)
                best_candidate_pipe.fit(X_full, y_full)
                _current_model = best_candidate_pipe
                serving_probs = best_val_probs
            else:
                promoted = False
                # Keep serving current model, model_version does not increment
                serving_probs = champ_probs

        # Compute validation metrics for the currently serving model on holdout
        val_preds = (serving_probs >= 0.5).astype(int)
        precision = float(precision_score(y_val, val_preds, zero_division=0))
        recall = float(recall_score(y_val, val_preds, zero_division=0))
        f1 = float(f1_score(y_val, val_preds, zero_division=0))
        pr_auc = float(average_precision_score(y_val, serving_probs)) if len(np.unique(y_val)) > 1 else 0.0

        metrics = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "pr_auc": round(pr_auc, 4),
        }

        # Log to MLflow
        mlflow_metrics = {
            **metrics,
            "candidate_pr_auc": round(float(candidate_pr_auc), 4),
            "promoted": 1.0 if promoted else 0.0,
        }
        if champion_pr_auc is not None:
            mlflow_metrics["champion_pr_auc"] = round(float(champion_pr_auc), 4)

        try:
            run_id = log_training_run(
                as_of=as_of.isoformat(),
                n_train=n_train,
                n_pending=n_pending,
                model_version=_model_version,
                metrics=mlflow_metrics,
                best_model_name=best_model_name,
            )
        except Exception:
            run_id = f"run_{uuid.uuid4().hex[:8]}"

        result = {
            "run_id": run_id,
            "as_of": as_of.isoformat(),
            "n_train": n_train,
            "n_pending": n_pending,
            "model_version": _model_version,
            "metrics": metrics,
            "promoted": promoted,
            "champion_pr_auc": round(champion_pr_auc, 4) if champion_pr_auc is not None else None,
            "candidate_pr_auc": round(float(candidate_pr_auc), 4),
            "best_model": best_model_name,
            "retrained": True,
        }
        _last_training_fingerprint = fingerprint
        _last_training_result = result
        return result

    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Training exception in train_and_log for as_of %s", as_of)
        return {
            "run_id": f"err_{uuid.uuid4().hex[:8]}",
            "as_of": as_of.isoformat(),
            "n_train": n_train,
            "n_pending": n_pending,
            "model_version": _model_version,
            "metrics": {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "pr_auc": 0.0,
            },
            "promoted": False,
            "champion_pr_auc": None,
            "candidate_pr_auc": 0.0,
            "best_model": "None",
            "retrained": False,
            "error": str(exc),
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

