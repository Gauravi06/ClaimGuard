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

MIN_SETTLED: int = 25

class SimulationState:
    def __init__(self, start_date: Optional[date] = None):
        self.start_date: date = start_date if start_date is not None else get_earliest_filed_at()
        self.simulated_date: date = self.start_date
        self.last_retrain_settled_count: int = 0
        self.model_version: int = 0
        self.retrains_total: int = 0
        self.latest_metrics: Optional[Dict[str, Any]] = None
        self._last_retrain_fingerprint: Optional[str] = None

    def reset(self, start_date: Optional[date] = None) -> None:
        """Reset state to initial values for test isolation."""
        training.reset_model()
        self.start_date = start_date if start_date is not None else get_earliest_filed_at()
        self.simulated_date = self.start_date
        self.last_retrain_settled_count = 0
        self.model_version = 0
        self.retrains_total = 0
        self.latest_metrics = None
        self._last_retrain_fingerprint = None

    def advance_date(self, days: int) -> date:
        """Increase simulated_date by the specified number of days and return it."""
        self.simulated_date += timedelta(days=days)
        return self.simulated_date

    @property
    def settled_claims_count(self) -> int:
        return len(simulation.get_settled(self.simulated_date))

    @property
    def pending_backlog_count(self) -> int:
        return len(simulation.get_pending(self.simulated_date))

    @property
    def newly_settled_since_retrain(self) -> int:
        return self.settled_claims_count - self.last_retrain_settled_count

    @property
    def last_retrain_pr_auc(self) -> float:
        if self.model_version == 0 or not self.latest_metrics:
            return 0.0
        return float(self.latest_metrics.get("metrics", {}).get("pr_auc", 0.0))

    @property
    def simulated_date_epoch(self) -> float:
        from datetime import datetime, timezone
        dt = datetime(self.simulated_date.year, self.simulated_date.month, self.simulated_date.day, tzinfo=timezone.utc)
        return dt.timestamp()

    def get_prometheus_metrics(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "settled_claims": self.settled_claims_count,
            "pending_backlog": self.pending_backlog_count,
            "newly_settled_since_retrain": self.newly_settled_since_retrain,
            "last_retrain_pr_auc": self.last_retrain_pr_auc,
            "simulated_date_epoch": self.simulated_date_epoch,
            "retrains_total": self.retrains_total,
        }

    def advance(self, days: int = 7) -> Dict[str, Any]:
        """
        Advance the clock and evaluate the retrain trigger.
        1. Advance simulated_date by days.
        2. Calculate settled_count = len(get_settled(as_of)).
        3. Calculate newly_settled = settled_count - self.last_retrain_settled_count.
        4. Retrain only when settled_count >= MIN_SETTLED and:
           - either no model exists yet (model_version == 0), OR
           - newly_settled >= MIN_SETTLED.
        5. When retraining:
           - increment retrains_total
           - call train_and_log(as_of)
           - update model_version (increases only on promotion)
           - store result in latest_metrics
           - set last_retrain_settled_count = settled_count
        6. Return {simulated_date, newly_settled, retrained, model_version, promoted, ...}.
        """
        self.advance_date(days)
        as_of = self.simulated_date

        settled_df = simulation.get_settled(as_of)
        settled_count = len(settled_df)
        newly_settled = settled_count - self.last_retrain_settled_count

        should_retrain = (
            (settled_count >= MIN_SETTLED)
            and (newly_settled > 0)
            and (self.model_version == 0 or newly_settled >= MIN_SETTLED)
        )

        retrained = False
        reason: Optional[str] = None
        error: Optional[str] = None

        if should_retrain:
            fingerprint = f"{as_of.isoformat()}_{settled_count}"
            try:
                metrics_dict = training.train_and_log(as_of)
                if metrics_dict.get("retrained", True) is False:
                    retrained = False
                    reason = metrics_dict.get("reason")
                    error = metrics_dict.get("error")
                else:
                    retrained = True
                    if fingerprint != self._last_retrain_fingerprint:
                        self.retrains_total += 1
                        self._last_retrain_fingerprint = fingerprint
                    self.model_version = metrics_dict.get("model_version", self.model_version)
                    self.latest_metrics = metrics_dict
                    self.last_retrain_settled_count = settled_count
            except Exception as exc:
                import logging
                logging.getLogger(__name__).exception("Retraining failed in SimulationState.advance: %s", exc)
                retrained = False
                error = str(exc)

        res = {
            "simulated_date": self.simulated_date.isoformat(),
            "newly_settled": newly_settled,
            "retrained": retrained,
            "model_version": self.model_version,
        }
        if retrained and self.latest_metrics:
            res["promoted"] = self.latest_metrics.get("promoted", False)
            res["champion_pr_auc"] = self.latest_metrics.get("champion_pr_auc")
            res["candidate_pr_auc"] = self.latest_metrics.get("candidate_pr_auc")
            res["best_model"] = self.latest_metrics.get("best_model")
        else:
            if reason:
                res["reason"] = reason
            if error:
                res["error"] = error
        return res

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

def get_prometheus_metrics() -> Dict[str, Any]:
    return state.get_prometheus_metrics()

