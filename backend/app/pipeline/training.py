import pandas as pd
from datetime import date
import random

def train_and_log(as_of: date) -> dict:
    """
    Stub for the training pipeline logging function.
    Returns a deterministic dictionary representing the logged metrics and model metadata.
    """
    return {
        "run_id": "dummy_run_12345",
        "as_of": as_of.isoformat(),
        "n_train": 30,
        "n_pending": 20,
        "model_version": 1,
        "metrics": {
            "precision": 0.85,
            "recall": 0.78,
            "f1": 0.81,
            "pr_auc": 0.88
        }
    }

def score_claims(df: pd.DataFrame) -> list[float]:
    """
    Return one dummy fraud probability between 0 and 1 for each input row.
    Uses deterministic values for testing reproducibility.
    """
    rng = random.Random(42)
    return [rng.uniform(0.1, 0.9) for _ in range(len(df))]
