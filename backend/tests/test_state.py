import pytest
from datetime import date, timedelta
import pandas as pd

from app.pipeline.state import state, advance, advance_date, reset_state, SimulationState

@pytest.fixture(autouse=True)
def clean_simulation_state():
    """Ensure every test runs with an isolated, clean simulation state."""
    reset_state()
    yield
    reset_state()

def test_initial_state():
    """1. Initial state is correct."""
    assert state.simulated_date == state.start_date
    assert state.last_retrain_settled_count == 0
    assert state.model_version == 0
    assert state.latest_metrics is None

def test_advance_seven_days():
    """2. advance(7) moves the date exactly 7 days."""
    result = advance(7)
    expected_date = state.start_date + timedelta(days=7)
    assert state.simulated_date == expected_date
    assert result["simulated_date"] == expected_date.isoformat()

def test_multiple_advances_accumulate():
    """3. Multiple advances accumulate correctly."""
    d1 = state.start_date + timedelta(days=7)
    d2 = state.start_date + timedelta(days=14)
    d3 = state.start_date + timedelta(days=21)

    r1 = advance(7)
    assert r1["simulated_date"] == d1.isoformat()
    assert state.simulated_date == d1

    r2 = advance(7)
    assert r2["simulated_date"] == d2.isoformat()
    assert state.simulated_date == d2

    r3 = advance(7)
    assert r3["simulated_date"] == d3.isoformat()
    assert state.simulated_date == d3

def test_no_retrain_at_zero_settled():
    """At 0 settled claims, advancing does NOT trigger retrain and model_version remains 0."""
    result = advance(7)
    assert result["retrained"] is False
    assert result["model_version"] == 0
    assert result["newly_settled"] == 0
    assert state.model_version == 0
    assert state.latest_metrics is None
    assert state.last_retrain_settled_count == 0

def test_no_retrain_at_24_settled(monkeypatch):
    """At 24 settled claims, advancing does NOT trigger retrain and model_version remains 0."""
    def mock_df_of_length(n):
        return pd.DataFrame([{"claim_id": f"c_{i}"} for i in range(n)])

    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(24))
    res = advance(7)
    assert res["retrained"] is False
    assert res["newly_settled"] == 24
    assert res["model_version"] == 0
    assert state.model_version == 0
    assert state.latest_metrics is None
    assert state.last_retrain_settled_count == 0

def test_first_retrain_at_25_settled(monkeypatch):
    """At 25 settled claims, first retrain is triggered and model_version becomes 1."""
    def mock_df_of_length(n):
        return pd.DataFrame([{"claim_id": f"c_{i}"} for i in range(n)])

    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(25))
    res = advance(7)
    assert res["retrained"] is True
    assert res["newly_settled"] == 25
    assert res["model_version"] == 1
    assert state.model_version == 1
    assert state.latest_metrics is not None
    assert state.latest_metrics["model_version"] == 1
    assert state.last_retrain_settled_count == 25

def test_retrain_when_newly_settled_at_least_25():
    """Retrain occurs when claims reach at least 25 (real dataset progression)."""
    # Step 1 (week 1): 0 settled -> no retrain, version remains 0
    r1 = advance(7)
    assert r1["retrained"] is False
    assert state.model_version == 0

    # Step 2 (week 2): 8 settled (< 25) -> no retrain, version remains 0
    r2 = advance(7)
    assert not r2["retrained"]
    assert state.model_version == 0

    # Step 3 (week 3): 61 settled (>= 25) -> first retrain to v1!
    r3 = advance(7)
    assert r3["retrained"] is True
    assert r3["newly_settled"] >= 25
    assert r3["model_version"] == 1
    assert state.model_version == 1
    assert state.last_retrain_settled_count >= 25

def test_model_version_increases_only_on_retrain(monkeypatch):
    """model_version increases ONLY when retraining occurs."""
    # Start: version is 0
    assert state.model_version == 0

    def mock_df_of_length(n):
        return pd.DataFrame([{"claim_id": f"c_{i}"} for i in range(n)])

    # 1. 0 settled claims -> no retrain -> version stays 0
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(0))
    r0 = advance(7)
    assert r0["retrained"] is False
    assert state.model_version == 0

    # 2. 24 settled claims -> no retrain -> version stays 0
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(24))
    r24 = advance(7)
    assert r24["retrained"] is False
    assert state.model_version == 0

    # 3. 25 settled claims -> first retrain -> version becomes 1
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(25))
    r25 = advance(7)
    assert r25["retrained"] is True
    assert state.model_version == 1

    # 4. 35 settled claims (10 newly settled < 25) -> no retrain -> version stays 1
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(35))
    r35 = advance(7)
    assert r35["retrained"] is False
    assert state.model_version == 1

    # 5. 50 settled claims (25 newly settled >= 25) -> retrain -> version becomes 2
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(50))
    r50 = advance(7)
    assert r50["retrained"] is True
    assert state.model_version == 2

def test_last_retrain_settled_count_updates_only_on_retrain():
    """last_retrain_settled_count updates only after retraining."""
    # Step 1: settled_count is 0, no retrain -> last_retrain_settled_count = 0
    advance(7)
    assert state.last_retrain_settled_count == 0

    # Step 2: settled_count is 8 (< 25), no retrain -> last_retrain_settled_count = 0
    advance(7)
    assert state.last_retrain_settled_count == 0

    # Step 3: settled_count is 61 (>= 25), retrain occurs -> last_retrain_settled_count = 61
    advance(7)
    assert state.last_retrain_settled_count == 61

def test_result_structure_keys_and_types():
    """9. The returned result contains exactly the required fields."""
    res = advance(7)
    expected_keys = {"simulated_date", "newly_settled", "retrained", "model_version"}
    assert set(res.keys()) == expected_keys
    assert isinstance(res["simulated_date"], str)
    assert isinstance(res["newly_settled"], int)
    assert isinstance(res["retrained"], bool)
    assert isinstance(res["model_version"], int)

def test_state_isolation_and_reset():
    """10. Reset/isolation between tests must be handled properly."""
    advance(14)
    assert state.simulated_date == state.start_date + timedelta(days=14)

    # Reset
    reset_state()
    assert state.simulated_date == state.start_date
    assert state.model_version == 0
    assert state.last_retrain_settled_count == 0
    assert state.latest_metrics is None

def test_independent_simulation_state_instance():
    """Test that creating custom SimulationState instances works independently."""
    custom_state = SimulationState(start_date=date(2020, 1, 1))
    assert custom_state.simulated_date == date(2020, 1, 1)
    res = custom_state.advance(10)
    assert res["simulated_date"] == "2020-01-11"
    assert res["retrained"] is True  # No model yet
    assert custom_state.model_version == 1
