"""ClaimGuard Production ML Serving Pipeline.

Serves predictions using the benchmark champion: XGBoost trained on 14 real-world
automobile claims features from data/processed/carclaims_processed.csv.

Architectural highlights:
- Loads pre-trained serialized model artifact (data/models/xgb_champion.joblib) in <10ms.
- Avoids expensive retraining on server startup while providing immediate inference.
- Requires the artifact at serving time; a missing artifact fails clearly instead of
  silently launching a training job. Use train() for deliberate/offline training.
- Requires all production model features per prediction request; no silent defaults.
- Generates Gini/Gain-based tree feature importance explanations (not SHAP).
- Inference always uses the feature order stored inside the serialized artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from xgboost import XGBClassifier

from app.ml.train_comparison import (
    DEFAULT_PROCESSED_DATA_PATH,
    EXPANDED_FEATURE_COLUMNS,
    train_and_save_champion,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT = PROJECT_ROOT / "data" / "models" / "xgb_champion.joblib"

# The 14 features the production model requires. The artifact must contain exactly
# this set; the ORDER used at inference comes from the artifact itself.
REQUIRED_MODEL_FEATURES = tuple(EXPANDED_FEATURE_COLUMNS)

# Claim type mapping (auto body categories + backward-compatible aliases).
# Unknown claim types are rejected, never defaulted.
CLAIM_TYPE_MAP = {
    "sedan": 0,
    "auto": 0,
    "passenger": 0,
    "sport": 1,
    "sports": 1,
    "utility": 2,
    "suv": 2,
    "truck": 2,
    # Legacy demo types, explicitly mapped to sedan (0)
    "property": 0,
    "health": 0,
    "life": 0,
}


class MLPipeline:
    def __init__(self, artifact_path: Optional[Path | str] = None):
        self.artifact_path = Path(artifact_path or DEFAULT_ARTIFACT)
        self.model: Optional[XGBClassifier] = None
        # Populated from the artifact on load; never assumed.
        self.feature_names: List[str] = []
        self.is_trained = False

        self.claim_type_map = CLAIM_TYPE_MAP

        # Empirical category average vehicle valuations from real dataset
        self.avg_amounts = {0: 31123.05, 1: 36984.04, 2: 71211.00}

    @staticmethod
    def _validate_artifact(artifact: Any, source: Path) -> Tuple[Any, List[str]]:
        """Validate a loaded artifact and return ``(model, feature_names)``.

        Nothing is guessed: the artifact must carry its own ``feature_names``,
        they must be exactly the 14 required model features, and they must match
        the order the model was trained with.
        """
        if not isinstance(artifact, dict) or "model" not in artifact:
            raise ValueError(
                f"Invalid model artifact at {source}: expected a dict with 'model' and "
                "'feature_names'. Regenerate it with the offline training pipeline."
            )
        names = artifact.get("feature_names")
        if not isinstance(names, (list, tuple)) or not all(isinstance(n, str) for n in names):
            raise ValueError(
                f"Invalid model artifact at {source}: 'feature_names' is missing or malformed. "
                "Regenerate it with the offline training pipeline."
            )
        names = list(names)
        if len(set(names)) != len(names) or set(names) != set(REQUIRED_MODEL_FEATURES):
            missing = sorted(set(REQUIRED_MODEL_FEATURES) - set(names))
            unexpected = sorted(set(names) - set(REQUIRED_MODEL_FEATURES))
            raise ValueError(
                f"Model artifact at {source} does not match the 14 required features "
                f"(missing={missing}, unexpected={unexpected}, duplicates={len(names) != len(set(names))}). "
                "Regenerate it with the offline training pipeline."
            )

        model = artifact["model"]
        n_in = getattr(model, "n_features_in_", None)
        if n_in is not None and n_in != len(names):
            raise ValueError(
                f"Model artifact at {source}: model expects {n_in} features but "
                f"feature_names lists {len(names)}."
            )
        booster_names = None
        if hasattr(model, "get_booster"):
            booster_names = model.get_booster().feature_names
        if booster_names is not None and list(booster_names) != names:
            raise ValueError(
                f"Model artifact at {source}: feature_names order does not match the "
                "order the model was trained with. Regenerate it with the offline "
                "training pipeline."
            )
        return model, names

    def load_model(self, artifact_path: Optional[Path | str] = None) -> None:
        """Load and validate the serialized production model artifact.

        Raises ``FileNotFoundError`` if the artifact is absent and ``ValueError``
        if it is unreadable or invalid. Never trains a model.
        """
        target_path = Path(artifact_path or self.artifact_path)
        if not target_path.is_file():
            raise FileNotFoundError(
                f"Model artifact not found at {target_path}. The production model must be "
                "generated first with the explicit offline training pipeline "
                "(MLPipeline.train() or app.ml.train_comparison.train_and_save_champion()), "
                "then restart the service. Serving does not trigger training."
            )
        try:
            artifact = joblib.load(target_path)
        except Exception as exc:
            raise ValueError(
                f"Model artifact at {target_path} could not be loaded ({exc}). "
                "Regenerate it with the offline training pipeline."
            ) from exc

        model, names = self._validate_artifact(artifact, target_path)
        self.model = model
        self.feature_names = names
        self.is_trained = True

    def train(self, data_path: Optional[Path | str] = None):
        """Explicit offline training: train the champion, save it, then load it
        through the same validation used for serving."""
        target_data = Path(data_path or DEFAULT_PROCESSED_DATA_PATH)
        train_and_save_champion(
            data_path=target_data,
            artifact_path=self.artifact_path,
        )
        self.load_model()

    def load_or_train(self):
        """Serving entrypoint (legacy name): load the artifact, NEVER train.

        If the artifact is missing or invalid this raises an actionable error;
        training must be run explicitly offline.
        """
        self.load_model()

    # Raw claim fields that feed the 14 production model features. Every one of
    # them must be supplied explicitly by the caller; no value is invented.
    REQUIRED_CLAIM_FIELDS = (
        "claim_amount",
        "claim_type",
        "days_to_report",
        "prior_claims_count",
        "police_report_filed",
        "witnesses",
        "fault",
        "deductible",
        "driver_rating",
        "age",
        "accident_area",
        "address_change_claim",
        "number_of_suppliments",
    )

    def _extract_features(self, claim_data: Dict[str, Any]) -> Tuple[pd.DataFrame, List[float]]:
        """Extract and format 14 features for model inference.

        All required model inputs must be present in ``claim_data``; missing or
        null values raise ``ValueError`` instead of being silently defaulted.
        """
        missing = [
            name
            for name in self.REQUIRED_CLAIM_FIELDS
            if name not in claim_data or claim_data[name] is None
        ]
        if missing:
            raise ValueError(
                "Missing required model input(s) for real prediction: "
                + ", ".join(missing)
                + ". Supply explicit values; ClaimGuard does not fabricate defaults."
            )

        raw_claim_type = str(claim_data["claim_type"]).lower()
        if raw_claim_type not in self.claim_type_map:
            raise ValueError(
                f"Unsupported claim_type {claim_data['claim_type']!r}. "
                f"Supported values: {sorted(self.claim_type_map)}."
            )
        claim_type_encoded = self.claim_type_map[raw_claim_type]

        claim_amount = float(claim_data["claim_amount"])
        cat_avg = self.avg_amounts[claim_type_encoded]
        amount_to_avg_ratio = round(claim_amount / max(1.0, cat_avg), 4)

        feature_dict = {
            "claim_amount": claim_amount,
            "claim_type_encoded": claim_type_encoded,
            "days_to_report": int(claim_data["days_to_report"]),
            "prior_claims_count": int(claim_data["prior_claims_count"]),
            "police_report_filed": int(bool(claim_data["police_report_filed"])),
            "witnesses": int(claim_data["witnesses"]),
            "amount_to_avg_ratio": amount_to_avg_ratio,
            "fault": int(claim_data["fault"]),
            "deductible": float(claim_data["deductible"]),
            "driver_rating": int(claim_data["driver_rating"]),
            "age": float(claim_data["age"]),
            "accident_area": int(claim_data["accident_area"]),
            "address_change_claim": int(claim_data["address_change_claim"]),
            "number_of_suppliments": float(claim_data["number_of_suppliments"]),
        }

        # Build DataFrame with strictly ordered columns taken from the artifact
        if not self.feature_names:
            raise RuntimeError("Model artifact is not loaded; feature order is unknown.")
        missing_features = [name for name in self.feature_names if name not in feature_dict]
        if missing_features:
            raise ValueError(
                f"Model artifact expects unsupported feature(s): {missing_features}. "
                "The serving pipeline is out of sync with the artifact; retrain/redeploy."
            )
        df = pd.DataFrame([[feature_dict[name] for name in self.feature_names]], columns=self.feature_names)
        feature_values = [feature_dict[name] for name in self.feature_names]
        return df, feature_values

    def predict(self, claim_data: Dict[str, Any]) -> float:
        """Generate fraud risk probability (0.0 - 1.0)."""
        if not self.is_trained:
            self.load_or_train()
        X, _ = self._extract_features(claim_data)
        return float(self.model.predict_proba(X)[0][1])

    def explain(self, claim_data: Dict[str, Any], score: float) -> List[Dict[str, Any]]:
        """Tree Feature Importance Explanations (Gain/Gini-based, not SHAP).
        
        Evaluates top contributing features based on model feature importances
        and domain thresholds.
        """
        if not self.is_trained:
            self.load_or_train()

        _, feature_values = self._extract_features(claim_data)
        importances = self.model.feature_importances_

        explanations = []
        for name, imp, val in zip(self.feature_names, importances, feature_values):
            if imp > 0.03:
                direction = "up"
                if name == "witnesses" and val > 0:
                    direction = "down"
                elif name == "police_report_filed" and val == 1:
                    direction = "down"
                elif name == "fault" and val == 0:
                    direction = "down"  # Third party fault has much lower fraud rate
                elif name == "days_to_report" and val > 15:
                    direction = "up"
                elif name == "claim_amount" and val > 35000:
                    direction = "up"
                elif name == "prior_claims_count" and val > 1:
                    direction = "up"
                elif name == "address_change_claim" and val > 1:
                    direction = "up"
                elif name == "deductible" and val == 500:
                    direction = "up"
                elif name == "accident_area" and val == 1:
                    direction = "up"

                explanations.append({
                    "feature": name,
                    "importance": round(float(imp), 4),
                    "value": float(val),
                    "direction": direction,
                })

        explanations.sort(key=lambda x: x["importance"], reverse=True)
        return explanations


ml_pipeline = MLPipeline()