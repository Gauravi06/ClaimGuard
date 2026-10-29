import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.pipeline import ml_pipeline

client = TestClient(app)

SAMPLE_CLAIM_14 = {
    "claimant_name": "Test Claimant",
    "claim_amount": 42000.0,
    "claim_type": "sedan",
    "incident_date": "2026-03-15",
    "days_to_report": 18,
    "description": "Collision at intersection",
    "prior_claims_count": 2,
    "police_report_filed": False,
    "witnesses": 0,
    "fault": 1,
    "deductible": 500.0,
    "driver_rating": 3,
    "age": 42.0,
    "accident_area": 1,
    "address_change_claim": 2,
    "number_of_suppliments": 1.0,
}


def test_shap_explanation_keys_and_sorting():
    """Verify explanation contains expected keys including shap_value, and is sorted by abs(shap_value)."""
    score = ml_pipeline.predict(SAMPLE_CLAIM_14)
    explanations = ml_pipeline.explain(SAMPLE_CLAIM_14, score)

    assert isinstance(explanations, list)
    assert 0 < len(explanations) <= 5

    prev_abs_shap = float("inf")
    for exp in explanations:
        assert "feature" in exp
        assert "importance" in exp
        assert "value" in exp
        assert "direction" in exp
        assert "shap_value" in exp
        assert isinstance(exp["shap_value"], float)
        assert exp["feature"] in ml_pipeline.feature_names

        current_abs_shap = abs(exp["shap_value"])
        assert current_abs_shap <= prev_abs_shap + 1e-6
        prev_abs_shap = current_abs_shap


def test_shap_direction_signs_consistency():
    """Verify that a positive shap_value always maps to 'increases risk' and negative/zero to 'decreases risk'."""
    score = ml_pipeline.predict(SAMPLE_CLAIM_14)
    explanations = ml_pipeline.explain(SAMPLE_CLAIM_14, score)

    for exp in explanations:
        if exp["shap_value"] > 0:
            assert exp["direction"] == "increases risk"
        else:
            assert exp["direction"] == "decreases risk"


def test_shap_explainer_cached():
    """Verify that TreeExplainer is built once and cached on the pipeline instance."""
    ml_pipeline.explainer = None  # Force clean state
    assert ml_pipeline.explainer is None

    score = ml_pipeline.predict(SAMPLE_CLAIM_14)
    ml_pipeline.explain(SAMPLE_CLAIM_14, score)
    cached_explainer = ml_pipeline.explainer
    assert cached_explainer is not None

    # Second call should reuse the same explainer instance
    ml_pipeline.explain(SAMPLE_CLAIM_14, score)
    assert ml_pipeline.explainer is cached_explainer


def test_shap_fallback_when_explainer_raises(monkeypatch, caplog):
    """Verify fallback to feature importance when shap computation raises an error."""
    class FailingExplainer:
        def shap_values(self, X):
            raise RuntimeError("Forced SHAP failure for fallback testing")

    monkeypatch.setattr(ml_pipeline, "_get_explainer", lambda: FailingExplainer())

    with caplog.at_level(logging.WARNING):
        score = ml_pipeline.predict(SAMPLE_CLAIM_14)
        explanations = ml_pipeline.explain(SAMPLE_CLAIM_14, score)

    assert isinstance(explanations, list)
    assert len(explanations) > 0
    # Fallback explanation uses classic directions 'up'/'down'
    for exp in explanations:
        assert "feature" in exp
        assert "importance" in exp
        assert "value" in exp
        assert exp["direction"] in ("up", "down")

    assert any("SHAP explanation failed" in record.message for record in caplog.records)


def test_post_claims_returns_200_with_explanation():
    """Verify POST /api/claims still returns 200 with explanations populated."""
    response = client.post("/api/claims", json=SAMPLE_CLAIM_14)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "fraud_score" in data
    assert "risk_level" in data
    assert "explanations" in data
    assert isinstance(data["explanations"], list)
    assert len(data["explanations"]) > 0
    first_exp = data["explanations"][0]
    assert "feature" in first_exp
    assert "importance" in first_exp
    assert "direction" in first_exp
