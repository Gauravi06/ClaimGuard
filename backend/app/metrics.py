"""
backend/app/metrics.py
Prometheus metrics exporter for ClaimGuard simulation.
Gauges and counter sourced exclusively from app/pipeline/state.py.
"""
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    Counter,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from app.pipeline.state import state

# Dedicated CollectorRegistry for ClaimGuard Prometheus metrics
registry = CollectorRegistry()

claimguard_model_version = Gauge(
    "claimguard_model_version",
    "Current simulation model version (0 before first model exists)",
    registry=registry,
)
claimguard_settled_claims = Gauge(
    "claimguard_settled_claims",
    "Total settled claims count as of current simulated date",
    registry=registry,
)
claimguard_pending_backlog = Gauge(
    "claimguard_pending_backlog",
    "Total pending claims backlog count as of current simulated date",
    registry=registry,
)
claimguard_newly_settled_since_retrain = Gauge(
    "claimguard_newly_settled_since_retrain",
    "Newly settled claims accumulated since last retraining event",
    registry=registry,
)
claimguard_last_retrain_pr_auc = Gauge(
    "claimguard_last_retrain_pr_auc",
    "PR-AUC score from the latest model retrain run (0.0 before first model exists)",
    registry=registry,
)
claimguard_simulated_date_epoch = Gauge(
    "claimguard_simulated_date_epoch",
    "Current simulated date represented as seconds since Unix epoch",
    registry=registry,
)
claimguard_retrains_total = Counter(
    "claimguard_retrains_total",
    "Total number of model retraining events executed",
    registry=registry,
)


def update_metrics() -> None:
    """Update all prometheus gauges and counters using values from state.py only."""
    data = state.get_prometheus_metrics()

    claimguard_model_version.set(data["model_version"])
    claimguard_settled_claims.set(data["settled_claims"])
    claimguard_pending_backlog.set(data["pending_backlog"])
    claimguard_newly_settled_since_retrain.set(data["newly_settled_since_retrain"])
    claimguard_last_retrain_pr_auc.set(data["last_retrain_pr_auc"])
    claimguard_simulated_date_epoch.set(data["simulated_date_epoch"])
    claimguard_retrains_total._value.set(data["retrains_total"])


def get_metrics_text() -> str:
    """Return the prometheus exposition text decoded as string."""
    update_metrics()
    return generate_latest(registry).decode("utf-8")


def get_metrics_bytes() -> bytes:
    """Return the prometheus exposition format bytes for the HTTP response."""
    update_metrics()
    return generate_latest(registry)
