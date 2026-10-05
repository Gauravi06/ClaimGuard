"""
backend/app/pipeline/state.py
Simulation state holder and clock advance/retrain logic (O2 and O3).
"""
from datetime import date, timedelta
from typing import Optional, Dict, Any

from . import simulation
from . import training

def get_earliest_filed_at() -> date:
    """Return the earliest filed_at date from simulation data, defaulting to 2015-02-01."""
    try:
        if not simulation._df_pool.empty and "filed_at" in simulation._df_pool.columns:
            return simulation._df_pool["filed_at"].min()
    except Exception:
        pass
    return date(2015, 2, 1)

class SimulationState:
    def __init__(self, start_date: Optional[date] = None):
        self.start_date: date = start_date if start_date is not None else get_earliest_filed_at()
        self.simulated_date: date = self.start_date
        self.last_retrain_settled_count: int = 0
        self.model_version: int = 0
        self.latest_metrics: Optional[Dict[str, Any]] = None

    def reset(self, start_date: Optional[date] = None) -> None:
        """Reset state to initial values for test isolation."""
        self.start_date = start_date if start_date is not None else get_earliest_filed_at()
        self.simulated_date = self.start_date
        self.last_retrain_settled_count = 0
        self.model_version = 0
        self.latest_metrics = None

    def advance_date(self, days: int) -> date:
        """Increase simulated_date by the specified number of days and return it."""
        self.simulated_date += timedelta(days=days)
        return self.simulated_date

    def advance(self, days: int = 7) -> Dict[str, Any]:
        """
        Advance the clock and evaluate the retrain trigger.
        1. Advance simulated_date by days.
        2. Calculate settled_count = len(get_settled(as_of)).
        3. Calculate newly_settled = settled_count - last_retrain_settled_count.
        4. Retrain if there has never been a model yet (model_version == 0) or newly_settled >= 25.
        5. When retraining:
           - call train_and_log(as_of)
           - store result in latest_metrics
           - set last_retrain_settled_count = settled_count
           - increment model_version
        6. Return {simulated_date, newly_settled, retrained, model_version}.
        """
        self.advance_date(days)
        as_of = self.simulated_date

        settled_df = simulation.get_settled(as_of)
        settled_count = len(settled_df)
        newly_settled = settled_count - self.last_retrain_settled_count

        should_retrain = (self.model_version == 0) or (newly_settled >= 25)

        if should_retrain:
            metrics_dict = training.train_and_log(as_of)
            self.model_version += 1
            metrics_dict["model_version"] = self.model_version
            self.latest_metrics = metrics_dict
            self.last_retrain_settled_count = settled_count
            retrained = True
        else:
            retrained = False

        return {
            "simulated_date": self.simulated_date.isoformat(),
            "newly_settled": newly_settled,
            "retrained": retrained,
            "model_version": self.model_version,
        }

# Global in-memory simulation state
state = SimulationState()

def advance(days: int = 7) -> Dict[str, Any]:
    return state.advance(days)

def advance_date(days: int) -> date:
    return state.advance_date(days)

def reset_state(start_date: Optional[date] = None) -> None:
    state.reset(start_date)

def get_state() -> SimulationState:
    return state
