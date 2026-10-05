"""Tests for production integration of real-data XGBoost model and delayed-label lifecycle."""

from datetime import datetime, timezone
from uuid import UUID

import joblib
import pytest
from fastapi.testclient import TestClient

from app.database import db
from app.main import app
from app.ml.pipeline import MLPipeline, ml_pipeline
from app.models import Claim
from xgboost import XGBClassifier

client = TestClient(app)

VALID_CLAIM = {
    "claimant_name": "Valid Claimant",
    "claim_amount": 25000.0,
    "claim_type": "sedan",
    "incident_date": "2026-09-10",
    "days_to_report": 5,
    "description": "Valid 14-feature claim",
    "prior_claims_count": 1,
    "police_report_filed": True,
    "witnesses": 1,
    "fault": 0,
    "deductible": 400.0,
    "driver_rating": 2,
    "age": 38.0,
    "accident_area": 1,
    "address_change_claim": 0,
    "number_of_suppliments": 0.0,
}


@pytest.fixture(autouse=True)
def ensure_model_and_clean_db():
    """Ensure ML pipeline is loaded with champion model and clean DB per test."""
    ml_pipeline.load_or_train()
    db.clear()
    yield
    db.clear()


def test_real_xgboost_model_loads_from_artifact():
    """Verify that MLPipeline loads the pre-trained XGBClassifier with all 14 features."""
    assert ml_pipeline.is_trained is True
    assert isinstance(ml_pipeline.model, XGBClassifier)
    assert len(ml_pipeline.feature_names) == 14
    assert "fault" in ml_pipeline.feature_names
    assert "claim_amount" in ml_pipeline.feature_names


def test_14_feature_prediction_and_explanations():
    """Verify that a full 14-feature dictionary yields valid score and explanations."""
    payload_14 = {
        "claimant_name": "Eleanor Rigby",
        "claim_amount": 35000.0,
        "claim_type": "sedan",
        "incident_date": "2026-09-10",
        "days_to_report": 12,
        "description": "Rear-end collision on highway",
        "prior_claims_count": 2,
        "police_report_filed": False,
        "witnesses": 0,
        "fault": 1,
        "deductible": 400.0,
        "driver_rating": 3,
        "age": 42.0,
        "accident_area": 1,
        "address_change_claim": 2,
        "number_of_suppliments": 1.5,
    }

    score = ml_pipeline.predict(payload_14)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

    explanations = ml_pipeline.explain(payload_14, score)
    assert isinstance(explanations, list)
    assert len(explanations) > 0
    for exp in explanations:
        assert "feature" in exp
        assert "importance" in exp
        assert "direction" in exp
        assert exp["feature"] in ml_pipeline.feature_names


def test_post_claims_with_full_14_features():
    """Test POST /api/claims accepts all 14 features and stores prediction immediately."""
    payload = {
        "claimant_name": "Marcus Vance",
        "claim_amount": 45000.0,
        "claim_type": "sport",
        "incident_date": "2026-09-15",
        "days_to_report": 18,
        "description": "Sport vehicle damage at intersection",
        "prior_claims_count": 3,
        "police_report_filed": False,
        "witnesses": 0,
        "fault": 1,
        "deductible": 500.0,
        "driver_rating": 4,
        "age": 28.0,
        "accident_area": 1,
        "address_change_claim": 3,
        "number_of_suppliments": 4.0,
    }

    res = client.post("/api/claims", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Verify response structure
    assert data["claimant_name"] == "Marcus Vance"
    assert data["fault"] == 1
    assert data["deductible"] == 500.0
    assert data["driver_rating"] == 4
    assert data["age"] == 28.0
    assert data["accident_area"] == 1
    assert data["address_change_claim"] == 3
    assert data["number_of_suppliments"] == 4.0

    # Prediction fields
    assert "fraud_score" in data
    assert 0.0 <= data["fraud_score"] <= 1.0
    assert data["risk_level"] in ("low", "medium", "high")
    assert data["prediction"] == (data["fraud_score"] > 0.5)
    assert data["true_label"] is None

    # Read back from GET /api/claims/{id}
    claim_id = data["id"]
    get_res = client.get(f"/api/claims/{claim_id}")
    assert get_res.status_code == 200
    assert get_res.json() == data


def test_post_claims_missing_model_inputs_rejected_clearly():
    """Legacy 9-field payload (missing the 7 extended model features) is rejected."""
    legacy_payload = {
        "claimant_name": "Legacy Claimant",
        "claim_amount": 18000.0,
        "claim_type": "auto",
        "incident_date": "2026-08-20",
        "days_to_report": 5,
        "description": "Fender bender",
        "prior_claims_count": 0,
        "police_report_filed": True,
        "witnesses": 1,
    }

    res = client.post("/api/claims", json=legacy_payload)
    assert res.status_code == 422
    detail = res.json()["detail"]
    missing_locs = {tuple(err["loc"]) for err in detail}
    for field in ("fault", "deductible", "driver_rating", "age", "accident_area",
                  "address_change_claim", "number_of_suppliments"):
        assert ("body", field) in missing_locs


def test_predict_missing_model_inputs_raises_value_error():
    """Direct pipeline use with missing required inputs raises a clear error."""
    from app.ml.pipeline import ml_pipeline as pipeline

    with pytest.raises(ValueError, match="Missing required model input"):
        pipeline.predict({"claim_amount": 1000.0, "claim_type": "auto"})


def test_missing_artifact_fails_clearly_without_training():
    """Serving must not silently train when the artifact is absent."""
    from app.ml.pipeline import MLPipeline

    fresh = MLPipeline(artifact_path="data/models/__definitely_missing__.joblib")
    with pytest.raises(FileNotFoundError, match="Model artifact not found") as exc:
        fresh.load_or_train()
    assert "offline training pipeline" in str(exc.value)
    assert fresh.is_trained is False


def test_missing_artifact_does_not_trigger_training(monkeypatch, tmp_path):
    """Neither load nor predict may call any training routine when the artifact is absent."""
    import app.ml.pipeline as pipeline_module

    def _boom(*args, **kwargs):
        raise AssertionError("training must never run during serving")

    monkeypatch.setattr(pipeline_module, "train_and_save_champion", _boom)
    monkeypatch.setattr(pipeline_module.MLPipeline, "train", _boom)

    missing = tmp_path / "nope.joblib"
    fresh = MLPipeline(artifact_path=missing)
    with pytest.raises(FileNotFoundError):
        fresh.load_or_train()
    with pytest.raises(FileNotFoundError):
        fresh.predict(VALID_CLAIM)
    assert not missing.exists()  # nothing was trained/saved
    assert fresh.is_trained is False


def _real_artifact():
    from app.ml.pipeline import DEFAULT_ARTIFACT

    return joblib.load(DEFAULT_ARTIFACT)


def test_artifact_without_feature_names_rejected(tmp_path):
    art = _real_artifact()
    path = tmp_path / "no_names.joblib"
    joblib.dump({"model": art["model"]}, path)
    with pytest.raises(ValueError, match="feature_names"):
        MLPipeline(artifact_path=path).load_or_train()


def test_bare_model_artifact_rejected(tmp_path):
    path = tmp_path / "bare.joblib"
    joblib.dump(_real_artifact()["model"], path)
    with pytest.raises(ValueError, match="Invalid model artifact"):
        MLPipeline(artifact_path=path).load_or_train()


def test_artifact_with_wrong_feature_set_rejected(tmp_path):
    art = _real_artifact()
    names = list(art["feature_names"])
    names[0] = "not_a_real_feature"
    path = tmp_path / "wrong_set.joblib"
    joblib.dump({**art, "feature_names": names}, path)
    with pytest.raises(ValueError, match="14 required features"):
        MLPipeline(artifact_path=path).load_or_train()


def test_artifact_with_reordered_feature_names_rejected(tmp_path):
    art = _real_artifact()
    path = tmp_path / "reordered.joblib"
    joblib.dump({**art, "feature_names": list(reversed(art["feature_names"]))}, path)
    with pytest.raises(ValueError, match="order"):
        MLPipeline(artifact_path=path).load_or_train()


def test_valid_artifact_copy_loads_with_artifact_order(tmp_path):
    art = _real_artifact()
    path = tmp_path / "copy.joblib"
    joblib.dump(art, path)
    fresh = MLPipeline(artifact_path=path)
    fresh.load_or_train()
    assert fresh.is_trained is True
    assert fresh.feature_names == list(art["feature_names"])
    assert fresh.predict(VALID_CLAIM) == ml_pipeline.predict(VALID_CLAIM)


MODEL_INPUT_FIELDS = (
    "claim_amount", "claim_type", "days_to_report", "prior_claims_count",
    "police_report_filed", "witnesses", "fault", "deductible", "driver_rating",
    "age", "accident_area", "address_change_claim", "number_of_suppliments",
)


@pytest.mark.parametrize("field", MODEL_INPUT_FIELDS)
def test_post_claims_rejects_each_missing_required_model_input(field):
    body = {k: v for k, v in VALID_CLAIM.items() if k != field}
    res = client.post("/api/claims", json=body)
    assert res.status_code == 422
    assert ("body", field) in {tuple(e["loc"]) for e in res.json()["detail"]}
    assert db.count() == 0


def test_post_claims_rejects_null_model_input():
    res = client.post("/api/claims", json={**VALID_CLAIM, "age": None})
    assert res.status_code == 422
    assert db.count() == 0


def test_post_claims_rejects_unsupported_claim_type():
    res = client.post("/api/claims", json={**VALID_CLAIM, "claim_type": "spaceship"})
    assert res.status_code == 422
    assert db.count() == 0


def test_inference_uses_artifact_feature_order():
    """The pipeline's feature order must match the artifact's stored order."""
    import joblib
    from app.ml.pipeline import DEFAULT_ARTIFACT

    artifact = joblib.load(DEFAULT_ARTIFACT)
    stored = artifact["feature_names"] if isinstance(artifact, dict) else None
    assert stored is not None
    assert list(ml_pipeline.feature_names) == list(stored)


def test_delayed_label_lifecycle_preserves_original_prediction():
    """Verify delayed-label workflow: true_label updates without re-computing prediction."""
    create_payload = {
        "claimant_name": "Lifecycle Test",
        "claim_amount": 32000.0,
        "claim_type": "auto",
        "incident_date": "2026-09-01",
        "days_to_report": 25,
        "description": "Suspicious late night single vehicle accident",
        "prior_claims_count": 3,
        "police_report_filed": False,
        "witnesses": 0,
        "fault": 1,
        "deductible": 500.0,
        "driver_rating": 3,
        "age": 30.0,
        "accident_area": 1,
        "address_change_claim": 2,
        "number_of_suppliments": 1.5,
    }

    # Step 1: Submit claim -> prediction generated and stored immediately
    created = client.post("/api/claims", json=create_payload).json()
    claim_id = created["id"]
    initial_score = created["fraud_score"]
    initial_prediction = created["prediction"]
    initial_risk = created["risk_level"]
    initial_explanations = created["explanations"]

    assert created["true_label"] is None
    assert initial_score > 0.0

    # Step 2: Investigation completes later -> PATCH delayed label
    patch_res = client.patch(f"/api/claims/{claim_id}/label", json={"true_label": True})
    assert patch_res.status_code == 200
    updated = patch_res.json()

    # Step 3: Verify true_label is set while prediction remains strictly unchanged
    assert updated["true_label"] is True
    assert updated["fraud_score"] == initial_score
    assert updated["prediction"] == initial_prediction
    assert updated["risk_level"] == initial_risk
    assert updated["explanations"] == initial_explanations

    # Step 4: Verify analytics picks up the newly labeled claim
    perf_res = client.get("/api/analytics/model-performance").json()
    assert perf_res["total_labeled"] == 1
    assert perf_res["confusion_matrix"]["tp"] + perf_res["confusion_matrix"]["fn"] == 1