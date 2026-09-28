import numpy as np
import pandas as pd

def generate_synthetic_data(n_samples: int = 500, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    
    claim_type_encoded = np.random.choice([0, 1, 2, 3], size=n_samples)
    claim_amount = np.random.exponential(scale=5000, size=n_samples) + 500
    days_to_report = np.random.exponential(scale=10, size=n_samples).astype(int)
    prior_claims_count = np.random.poisson(lam=1.0, size=n_samples)
    police_report_filed = np.random.choice([0, 1], size=n_samples, p=[0.4, 0.6])
    witnesses = np.random.poisson(lam=0.5, size=n_samples)
    
    avg_amounts = {0: 4000, 1: 12000, 2: 8000, 3: 50000}
    amount_to_avg_ratio = np.array([amount / avg_amounts[ct] for amount, ct in zip(claim_amount, claim_type_encoded)])
    
    fraud_prob = 0.05 * np.ones(n_samples)
    fraud_prob[claim_amount > 15000] += 0.2
    fraud_prob[prior_claims_count > 3] += 0.3
    fraud_prob[days_to_report > 30] += 0.2
    fraud_prob[police_report_filed == 0] += 0.15
    fraud_prob[witnesses == 0] += 0.1
    
    fraud_prob = np.clip(fraud_prob, 0.01, 0.95)
    is_fraud = np.random.binomial(1, fraud_prob)
    
    return pd.DataFrame({
        'claim_amount': claim_amount,
        'claim_type_encoded': claim_type_encoded,
        'days_to_report': days_to_report,
        'prior_claims_count': prior_claims_count,
        'police_report_filed': police_report_filed,
        'witnesses': witnesses,
        'amount_to_avg_ratio': amount_to_avg_ratio,
        'is_fraud': is_fraud
    })
