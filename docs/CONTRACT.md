# ClaimGuard sim contract (Mon 5 Oct 2026)

## S1. Data (Rashi builds backend/data/claims_sim.csv)
Columns: claim_id, filed_at, investigation_days, label_available_at, is_fraud
Features (13): total_claim_amount, injury_claim, property_claim, vehicle_claim,
incident_severity, witnesses, police_report_available (1/0/unknown),
bodily_injuries, number_of_vehicles_involved, policy_annual_premium,
months_as_customer, age, umbrella_limit
Rules:
- Pending claims NEVER include is_fraud, investigation_days, label_available_at.
- Clock starts at earliest filed_at, advances 7 days per step.
- Investigation window 10-30 days, seed 42.
- Retrain after 25 newly settled claims (and once on first start).

## S2. Functions (backend/app/pipeline/)
get_settled(as_of: date) -> DataFrame   # label_available_at <= as_of, has is_fraud
get_pending(as_of: date) -> DataFrame   # label_available_at > as_of and filed_at <= as_of, no label columns
train_and_log(as_of: date) -> dict
  {"run_id": str, "as_of": "2015-02-08", "n_train": int, "n_pending": int,
   "model_version": int,
   "metrics": {"precision": f, "recall": f, "f1": f, "pr_auc": f}}
score_claims(df: DataFrame) -> list[float]   # fraud probability from latest model

## S3. Endpoints (Om, prefix /api/sim)
GET  /clock    -> {"simulated_date": "..."}
POST /advance  body {"days": 7} -> {"simulated_date", "newly_settled", "retrained", "model_version"}
GET  /pending  -> {"as_of", "count", "claims": [{..., "fraud_score", "risk_level"}]}
GET  /settled  -> same plus is_fraud, label_available_at
GET  /metrics  -> {"model_version", "as_of", "n_train", "precision", "recall", "f1", "pr_auc"}
Risk: low < 0.3, medium 0.3-0.7, high >= 0.7 (lowercase). Prediction = score > 0.5.
Use /api/sim, not /api/claims (the UUID route would return 422).
