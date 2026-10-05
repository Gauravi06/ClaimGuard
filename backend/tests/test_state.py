import pytest
from datetime import date
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
    assert state.simulated_date == date(2015, 2, 1)
    assert state.last_retrain_settled_count == 0
    assert state.model_version == 0
    assert state.latest_metrics is None

def test_advance_seven_days():
    """2. advance(7) moves the date exactly 7 days."""
    result = advance(7)
    assert state.simulated_date == date(2015, 2, 8)
    assert result["simulated_date"] == "2015-02-08"

def test_multiple_advances_accumulate():
    """3. Multiple advances accumulate correctly."""
    r1 = advance(7)
    assert r1["simulated_date"] == "2015-02-08"
    assert state.simulated_date == date(2015, 2, 8)

    r2 = advance(7)
    assert r2["simulated_date"] == "2015-02-15"
    assert state.simulated_date == date(2015, 2, 15)

    r3 = advance(7)
    assert r3["simulated_date"] == "2015-02-22"
    assert state.simulated_date == date(2015, 2, 22)

def test_first_model_created_without_25_settled():
    """6. A first model is created even if fewer than 25 claims have settled (no model yet)."""
    # At 2015-02-08, settled count is 0 (< 25)
    result = advance(7)
    assert result["retrained"] is True
    assert result["model_version"] == 1
    assert state.model_version == 1
    assert state.latest_metrics is not None
    assert state.latest_metrics["model_version"] == 1

def test_no_retrain_when_newly_settled_under_25_after_model_exists():
    """4. No retrain occurs when newly_settled < 25 after an existing model exists."""
    # First advance creates model v1
    advance(7)
    assert state.model_version == 1

    # Second advance at 2015-02-15 has settled_count = 0, newly_settled = 0 (< 25)
    result = advance(7)
    assert result["retrained"] is False
    assert result["newly_settled"] == 0
    assert result["model_version"] == 1
    assert state.model_version == 1

def test_retrain_when_newly_settled_at_least_25():
    """5. Retrain occurs when newly_settled >= 25."""
    # Step through stub dataset until settled reaches >= 25 after initial retrain
    # Step 1 (2015-02-08): retrained to v1, last_retrain_settled_count = 0
    r1 = advance(7)
    assert r1["retrained"] is True
    assert state.model_version == 1

    # Steps 2 to 6: newly_settled stays below 25
    r2 = advance(7) # 2015-02-15: newly_settled=0 -> no retrain
    assert not r2["retrained"]
    r3 = advance(7) # 2015-02-22: newly_settled=4 -> no retrain
    assert not r3["retrained"]
    r4 = advance(7) # 2015-03-01: newly_settled=11 -> no retrain
    assert not r4["retrained"]
    r5 = advance(7) # 2015-03-08: newly_settled=15 -> no retrain
    assert not r5["retrained"]
    r6 = advance(7) # 2015-03-15: newly_settled=21 -> no retrain
    assert not r6["retrained"]
    assert state.model_version == 1

    # Step 7 (2015-03-22): settled count reaches 33 (33 - 0 = 33 >= 25) -> retrain to v2!
    r7 = advance(7)
    assert r7["retrained"] is True
    assert r7["newly_settled"] == 33
    assert r7["model_version"] == 2
    assert state.model_version == 2
    assert state.last_retrain_settled_count == 33

def test_model_version_increases_only_on_retrain():
    """7. model_version increases ONLY when retraining occurs."""
    # Start: version is 0
    assert state.model_version == 0

    # Advance 1 -> retrain occurs -> version 1
    r1 = advance(7)
    assert r1["retrained"] is True
    assert state.model_version == 1

    # Advance 2 -> no retrain -> version remains 1
    r2 = advance(7)
    assert r2["retrained"] is False
    assert r2["model_version"] == 1
    assert state.model_version == 1

    # Advance 3 -> no retrain -> version remains 1
    r3 = advance(7)
    assert r3["retrained"] is False
    assert r3["model_version"] == 1
    assert state.model_version == 1

def test_last_retrain_settled_count_updates_only_on_retrain():
    """8. last_retrain_settled_count updates only after retraining."""
    # First advance: settled_count is 0, retrain occurs -> last_retrain_settled_count = 0
    advance(7)
    assert state.last_retrain_settled_count == 0

    # Next advances with newly_settled < 25 do NOT change last_retrain_settled_count
    advance(7)  # 2015-02-15
    advance(7)  # 2015-02-22 (settled = 4, but no retrain)
    assert state.last_retrain_settled_count == 0

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
    assert state.simulated_date == date(2015, 2, 15)
    assert state.model_version > 0

    # Reset
    reset_state()
    assert state.simulated_date == date(2015, 2, 1)
    assert state.model_version == 0
    assert state.last_retrain_settled_count == 0
    assert state.latest_metrics is None

def test_boundary_24_vs_25_newly_settled(monkeypatch):
    """
    Explicit boundary testing:
    - 24 newly settled claims -> NO retrain
    - 25 newly settled claims -> RETRAIN
    Uses monkeypatching on get_settled to test exact boundary deterministically.
    """
    # 1. Establish initial model v1
    advance(7)
    assert state.model_version == 1
    assert state.last_retrain_settled_count == 0

    # Create dummy DataFrame generator of length n
    def mock_df_of_length(n):
        return pd.DataFrame([{"claim_id": f"c_{i}"} for i in range(n)])

    # Test boundary: 24 newly settled claims
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(24))
    res_24 = advance(7)
    assert res_24["retrained"] is False
    assert res_24["newly_settled"] == 24
    assert res_24["model_version"] == 1
    assert state.model_version == 1
    assert state.last_retrain_settled_count == 0  # Still 0, not updated

    # Test boundary: 25 newly settled claims
    monkeypatch.setattr("app.pipeline.simulation.get_settled", lambda as_of: mock_df_of_length(25))
    res_25 = advance(7)
    assert res_25["retrained"] is True
    assert res_25["newly_settled"] == 25
    assert res_25["model_version"] == 2
    assert state.model_version == 2
    assert state.last_retrain_settled_count == 25  # Updated to 25

def test_independent_simulation_state_instance():
    """Test that creating custom SimulationState instances works independently."""
    custom_state = SimulationState(start_date=date(2020, 1, 1))
    assert custom_state.simulated_date == date(2020, 1, 1)
    res = custom_state.advance(10)
    assert res["simulated_date"] == "2020-01-11"
    assert res["retrained"] is True  # No model yet
    assert custom_state.model_version == 1
