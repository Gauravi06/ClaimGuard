# ClaimGuard Progress

## Completed

- **FastAPI Backend Core**: RESTful API built with FastAPI, Pydantic v2 schemas, and CORS middleware.
- **Persistent Claim Store (PostgreSQL & SQLite)**: Dual-database persistence via SQLAlchemy 2 (sync) + psycopg 3, configured by `DATABASE_URL`. Includes connection pooling (`pool_pre_ping`, `pool_recycle=300`), schema reflection, and backfill migration. Stored predictions, fraud scores, risk levels, and explanations are immutable once written; `true_label` is `NULL` until delayed investigation outcomes arrive.
- **Real-World Automobile Claims Dataset**: Processed 15,420 automobile insurance claims with 14 engineered features (`data/processed/carclaims_processed.csv`), including fault, deductible, driver rating, age, accident area, address change, and supplements.
- **Champion Model Benchmark & Serialization**: Offline comparative benchmark (`backend/app/ml/train_comparison.py`) evaluating Logistic Regression, Random Forest, and XGBoost with imbalanced classification metrics (PR-AUC, ROC-AUC, F1). XGBoost champion candidate serialized to `data/models/xgb_champion.joblib`.
- **Fast Production Inference Serving**: `MLPipeline` (`backend/app/ml/pipeline.py`) loads serialized XGBoost model artifact in <10ms during startup without expensive re-training latency.
- **Directional Feature Importance Explanations**: Tree Gain/Gini split-based directional attribution (`↑ Risk` or `↓ Risk`) identifying top risk drivers per claim.
- **Delayed-Label Workflow**: Endpoints `PATCH /api/claims/{id}/label` and `POST /api/claims/{id}/settle` allowing delayed ground-truth labels (`true_label: bool`) to be applied without altering initial predictions.
- **Dynamic Model Evaluation**: Endpoint `GET /api/analytics/model-performance` computing Accuracy, Precision, Recall, F1 Score, ROC-AUC, and 2×2 Confusion Matrix dynamically using only claims that have received ground-truth labels.
- **Chronological Delayed-Label Simulation Engine**:
  - Discrete event clock (`app/pipeline/state.py`, `/api/sim/clock`, `/api/sim/advance`) starting at `2015-01-01` and advancing by configurable intervals (default 7 days).
  - Historical chronological dataset (`backend/data/claims_sim.csv`) with 1,000 synthetic automobile insurance claims.
  - Strict Pending vs. Settled contract: `/api/sim/pending` never exposes `is_fraud`, `investigation_days`, or `label_available_at`.
  - Periodic automated retraining: Triggers automatically when $\ge 25$ newly settled claims accumulate since the previous retrain, comparing Random Forest and Logistic Regression using PR-AUC and fitting the winner on all settled claims.
- **MLflow Experiment Tracking**: `app/pipeline/tracking.py` logs all retrain runs, parameters (`as_of`, `n_train`, `n_pending`, `model_version`), and metrics (`precision`, `recall`, `f1`, `pr_auc`) to local `mlruns/` file store.
- **Prometheus Metrics Exporter**: Standalone endpoint `GET /metrics` exporting official Prometheus exposition format gauges (`claimguard_model_version`, `claimguard_settled_claims`, `claimguard_pending_backlog`, `claimguard_newly_settled_since_retrain`, `claimguard_last_retrain_pr_auc`, `claimguard_simulated_date_epoch`) and counter (`claimguard_retrains_total`).
- **React 18 + Tailwind CSS 4 Frontend**: Full single-page application with Overview Dashboard, Claim Submission Form with circular risk gauge, Claims Table & Detail views, Model Performance dashboard, and dedicated Simulation Dashboard (`SimulationDashboard.jsx`).
- **Containerization**: Production `backend/Dockerfile` featuring an automated offline champion model training step during build, non-root execution considerations, and health check querying `/`.
- **GitHub Actions CI Workflow**: `.github/workflows/ci.yml` running on push and pull request to `main`, validating backend tests (with XGBoost champion generation and SQLite database initialization) and frontend production build.

## Tested

- **Simulation & Pipeline Unit Tests** (`backend/tests/`):
  - `test_pipeline.py`: Validates `get_settled` and `get_pending` date filters and contract compliance (omitting label columns for pending claims).
  - `test_prometheus_metrics.py`: Validates `/metrics` Prometheus format, gauges, counters, and values sourced from simulation state.
  - `test_simulation.py`: Validates state initialization, clock advances, and investigation window bounds.
  - `test_sim_routes.py`: Validates `/api/sim/clock`, `/api/sim/advance`, `/api/sim/pending`, `/api/sim/settled`, `/api/sim/metrics`, and backward compatibility with `/api/claims`.
  - `test_state.py`: Validates state transition mechanics, retrain counters, and state resets.
  - `test_tracking.py`: Validates MLflow tracking initialization and run parameter logging.
  - `test_training.py`: Validates pipeline training, model comparison by PR-AUC, and scoring fallback behaviors.
  - *Result: 45 passed in `backend/tests`.*
- **Production Integration & Persistence Tests** (`tests/`):
  - `test_analytics.py`: Unit tests for analytics edge cases (0 claims, single-class labels, metric sanitization).
  - `test_demo_lifecycle.py`: Lifecycle verification across claim submission, delayed labeling, and performance computation.
  - `test_model_comparison.py`: Benchmark data loader, split integrity, metric calculations, and champion artifact validation.
  - `test_persistence.py`: Validates SQLite claim persistence, immutable initial predictions, delayed label persistence, and labeled-only metric queries.
  - `test_production_integration.py`: End-to-end integration tests for 14-feature XGBoost model loading, feature extraction, inference, explanations, and API responses.
  - `test_real_data_loader.py`: Verifies `carclaims_processed.csv` feature columns, data types, missing value absence, and class balance.
  - `test_seed.py`: Verifies seed data generation and cleanup.
  - *Result: 68 passed in `tests`.*
- **Frontend Production Build**: Verified Vite production bundle compilation (`npm run build`) in `frontend/`. 2,355 modules transformed into production assets in `frontend/dist/`.
- **Total Automated Tests**: **113 passed**.

## Current Architecture

```
React (Vite + Tailwind CSS v4)
        │
        │ REST API (JSON)
        ▼
FastAPI Backend
 ├── Claims Ingestion & Settlement (/api/claims)
 │     ├── XGBoost Champion Model (14 features, data/models/xgb_champion.joblib)
 │     └── Gain/Gini Feature Importance Explanations
 ├── Analytics & Metrics (/api/analytics)
 │     └── On-the-fly evaluation on settled claims
 ├── Simulation Pipeline (/api/sim)
 │     ├── Discrete clock & chronological replay (backend/data/claims_sim.csv)
 │     ├── Settled vs. Pending partition (Contract S1/S2)
 │     ├── Automated retraining every 25 settled claims (RF vs LR by PR-AUC)
 │     └── MLflow experiment tracking (mlruns/)
 ├── Prometheus Exporter (/metrics)
 │     └── 6 gauges + 1 counter from app/pipeline/state.py
 └── Database Persistence Layer (app/database.py)
       └── PostgreSQL (Neon) / SQLite (claims table)
```

## Known Limitations

- **Two Separate Datasets and Models**: The real-time scoring application operates on the 14-feature automobile dataset with XGBoost, while the simulation pipeline runs on a 13-feature synthetic chronological dataset with RF/LR retraining.
- **Simulated Delays**: Delays are generated uniformly between 10 and 30 days (seed 42) rather than drawn from complex empirical hazard curves.
- **Small Simulation Dataset**: The simulation dataset contains 1,000 claims.
- **Advisory / Unimplemented Drift Monitoring**: Feature drift monitoring via Population Stability Index (PSI) is designed but not yet coded.
- **No Promotion Rule**: Newly retrained simulation models unconditionally replace the active model without evaluating candidate performance against the incumbent champion.
- **No Authentication or RBAC**: API endpoints are public and lack token authentication or role separation.
- **In-Memory Simulation State**: Simulation state is stored in memory and resets when the server process terminates.
- **Destructive Seed Endpoint**: `POST /api/seed` wipes the `claims` table prior to inserting test data.

## Next Steps & Roadmap

### Core MLOps & Simulation
- [x] Build automated retraining pipeline triggered by delayed label accumulation ($\ge 25$ settled).
- [x] Integrate MLflow tracking for retraining parameters, cohort sizes, and metrics.
- [x] Expose Prometheus metrics endpoint (`/metrics`) for simulation observability.
- [ ] Implement model promotion rule: compare newly trained model PR-AUC against incumbent baseline before promotion.
- [ ] Add Population Stability Index (PSI) drift monitoring for incoming features and predictions (`drift.py`, `/api/sim/drift`).
- [ ] Track performance across distinct investigation cohorts and elapsed time windows.

### Explainability
- [x] Implement directional tree feature importance explanations (Gain/Gini-based).
- [ ] Evaluate SHAP (Shapley Additive exPlanations) for local game-theoretic attribution.

### Data & Model Enhancements
- [x] Integrate real-world automobile insurance claim dataset (`carclaims_processed.csv`, 15,420 rows).
- [x] Train and benchmark multiple model architectures (Logistic Regression, Random Forest, XGBoost).
- [x] Address severe class imbalance using class weights (`scale_pos_weight`) and PR-AUC metric selection.
- [x] Fast model loading from pre-trained serialized artifact (<10ms serving startup).
- [ ] Unify feature space between production scoring model and chronological simulation pipeline.

### Infrastructure & Deployment
- [x] Dockerfile for containerized backend serving with automated build-time model generation.
- [x] GitHub Actions CI workflow for backend tests and frontend build.
- [ ] Docker Compose multi-service orchestration (TODO: docs/DOCKER.md).
- [ ] Add Alembic database migrations.
- [ ] Add user authentication (OAuth2 / JWT) and role-based access control.
- [ ] Workflow orchestration with Apache Airflow.
- [ ] Data and artifact version control with DVC.
