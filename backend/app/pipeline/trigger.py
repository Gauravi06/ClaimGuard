"""
backend/app/pipeline/trigger.py
Retrain trigger helper and re-exports for O3.
"""
from typing import Dict, Any
from .state import state, advance, SimulationState

__all__ = ["advance", "state", "SimulationState"]
