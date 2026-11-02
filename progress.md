# ClaimGuard Progress

## Completed

- **FastAPI Backend Core**: RESTful API built with FastAPI, Pydantic v2 schemas, and CORS middleware.
- **Persistent Claim Store (PostgreSQL & SQLite)**: Dual-database persistence via SQLAlchemy 2 (sync) + psycopg 3, configured by `DATABASE_URL`. Includes connection pooling (`pool_pre_ping`, `pool_recycle=300`), schema reflection, and backfill migration. Stored predictions, fraud scores, risk levels, and explanations are immutable once written; `true_label` is `NULL` until delayed investigation outcomes arrive.
- **Real-World Automobile Claims Dataset**: Processed 15,419 automobile insurance claims with 14 engineered features (`data/processed/carclaims_processed.csv`), including fault, deductible, driver rating, age, accident area, address change, and supplements.
- **Champion Model Benchmark & Serialization**: Offline comparative benchmark (`backend/app/ml/train_comparison.py`) evaluating Logistic Regression, Random Forest, and XGBoost with imbalanced classification metrics (PR-AUC, ROC-AUC, F1). XGBoost champion candidate serialized to `data/models/xgb_champion.joblib`.
- **Fast Production Inference Serving**: `MLPipeline` (`backend/app/ml/pipeline.py`) loads serialized XGBoost model artifact in <10ms during startup without expensive re-training latency.
- **Directional Feature Importance & SHAP Attribution**:
  - Tree Gain/Gini split-based directional attribution (`↑ Risk` or `↓ Risk`) identifying top risk drivers per claim.
  - Tree SHAP local attribution using `shap.TreeExplainer` on the XGBoost champion, computing signed `shap_value` and directional impact (`increases risk` / `decreases risk`).
  - Interactive red/green SHAP contribution bar visualization on the frontend claim detail view (`frontend/src/components/ClaimDetail.jsx`).
- **Delayed-Label Workflow**: Endpoints `PATCH /api/claims/{id}/label` and `POST /api/claims/{id}/settle` allowing delayed ground-truth labels (`true_label: bool`) to be applied without altering initial predictions.
- **Dynamic Model Evaluation**: Endpoint `GET /api/analytics/model-performance` computing Accuracy, Precision, Recall, F1 Score, ROC-AUC, and 2×2 Confusion Matrix dynamically using only claims that have received ground-truth labels.
- **Chronological Delayed-Label Simulation Engine**:
  - Discrete event clock (`app/pipeline/state.py`, `/api/sim/clock`, `/api/sim/advance`) starting at `2015-01-01` and advancing by configurable intervals (default 7 days).
  - Historical chronological dataset (`backend/data/claims_sim.csv`) with 1,000 synthetic automobile insurance claims.
  - Strict Pending vs. Settled contract: `/api/sim/pending` never exposes `is_fraud`, `investigation_days`, or `label_available_at`.
  - Periodic automated retraining: Triggers automatically when $\ge 25$ newly settled claims accumulate since the previous retrain, evaluating Random Forest, Logistic Regression, and XGBoost candidates on a time-based holdout.
- **Model Promotion Gate / Rule**:
  - Compares the winning candidate's PR-AUC against the incumbent champion evaluated on the identical held-out validation set.
  - Promotes candidate to active serving and increments `model_version` only if PR-AUC strictly exceeds the champion (first model is promoted to v1 by default).
  - Rejects inferior candidates (`promoted: False`), preserving the incumbent serving model and version.
- **Population Stability Index (PSI) Drift Monitoring**:
  - Feature drift detection engine (`backend/app/pipeline/drift.py`) computing PSI across 13 contract features between the reference training cohort and recent simulation claims.
  - Endpoint `GET /api/sim/drift` exposing overall status (`ok` or `alert`) and per-feature stability metrics.
- **Settlement-Aware vs. Naive Retraining Experiment**:
  - Comprehensive empirical experiment (`experiments/settlement_comparison.py`, `results/settlement_comparison.csv`) evaluating the impact of delayed feedback.
  - Proves catastrophic recall suppression (0.0000 recall across early cycles) in naive retraining and demonstrates up to 8x recall gains in settlement-aware retraining.
  - Generated visual curves (`docs/figures/settlement_pr_auc_over_time.png`, `docs/figures/settlement_recall_over_time.png`) and documented in `docs/RESULTS.md`.
- **MLflow Experiment Tracking**: `app/pipeline/tracking.py` logs all retrain runs, parameters (`as_of`, `n_train`, `n_pending`, `model_version`), metrics (`precision`, `recall`, `f1`, `pr_auc`, `candidate_pr_auc`, `champion_pr_auc`), and promotion tags (`promoted`) to local `mlruns/` file store.
- **Prometheus Metrics Exporter**: Standalone endpoint `GET /metrics` exporting official Prometheus exposition format gauges (`claimguard_model_version`, `claimguard_settled_claims`, `claimguard_pending_backlog`, `claimguard_newly_settled_since_retrain`, `claimguard_last_retrain_pr_auc`, `claimguard_simulated_date_epoch`) and counter (`claimguard_retrains_total`).
- **React 18 + Tailwind CSS 4 Frontend**: Full single-page application with Overview Dashboard, Claim Submission Form with circular risk gauge, Claims Table & Detail views with SHAP bars, Model Performance dashboard, and dedicated Simulation Dashboard (`SimulationDashboard.jsx`).
- **Containerization & Multi-Service Orchestration**:
  - Production `backend/Dockerfile` featuring automated offline champion model training during build and health check querying `/`.
  - Multi-stage `frontend/Dockerfile` and `frontend/nginx.conf` serving built SPA assets on port 80.
  - Multi-container orchestration via `docker-compose.yml` deploying backend (`:8000`), frontend (`:3000`), MLflow UI (`:5000`), Prometheus (`:9090`), and Grafana (`:3001`). Comprehensive deployment instructions planned in `docs/DOCKER.md`.
- **Data Version Control (DVC)**: Initialized DVC repository tracking (`.dvc/config`, local storage `/tmp/dvc-storage`). Created `.dvc` tracking pointers for raw claims (`data/raw/carclaims.csv.dvc`), processed features (`data/processed/carclaims_processed.csv.dvc`), simulation pool (`backend/data/claims_sim.csv.dvc`), and dynamic cohort snapshots (`data/snapshots/settled_claims.csv.dvc`). Implemented `scripts/snapshot_settled.py` CLI to snapshot settled cohorts at simulation cutoffs and log MD5 hashes to MLflow. Documented in [docs/DVC.md](docs/DVC.md).
- **Prometheus Monitoring & Grafana Dashboards**:
  - Prometheus v2.54.1 (`monitoring/prometheus.yml`) configured to scrape `backend:8000/metrics` every 5 seconds.
  - Grafana v11.2.0 (`monitoring/grafana/`) with automated provisioning for Prometheus datasource and `claimguard.json` ("ClaimGuard Delayed-Label Monitor") featuring 7 telemetry panels (Model Version, Settled Claims, Retrains Total, Newly Settled gauge, Serving model PR-AUC, Pending backlog, and Model Version vs Retrains Total).
- **GitHub Actions CI Workflow**: `.github/workflows/ci.yml` running on push and pull request to `main`, validating backend tests (with XGBoost champion generation and SQLite database initialization) and frontend production build.

## Tested

- **Simulation, Drift & Pipeline Tests** (`backend/tests/`):
  - `test_drift.py`: Validates PSI calculation, binning stability, drift status thresholds, and `/api/sim/drift` endpoint.
  - `test_edge_cases.py`: Validates edge cases in data querying, extreme dates, missing features, and zero-claim scenarios.
  - `test_pipeline.py`: Validates `get_settled` and `get_pending` date filters and contract compliance (omitting label columns for pending claims).
  - `test_prometheus_metrics.py`: Validates `/metrics` Prometheus format, gauges, counters, and values sourced from simulation state.
  - `test_simulation.py`: Validates state initialization, clock advances, and investigation window bounds.
  - `test_sim_routes.py`: Validates `/api/sim/clock`, `/api/sim/advance`, `/api/sim/pending`, `/api/sim/settled`, `/api/sim/metrics`, `/api/sim/drift`, and promotion response fields.
  - `test_state.py`: Validates state transition mechanics, retrain counters, promotion state, and state resets.
  - `test_tracking.py`: Validates MLflow tracking initialization and run parameter logging.
  - `test_training.py`: Validates pipeline training, XGB/RF/LR candidate comparison, promotion rules, and champion retention.
  - *Result: **59 passed** in `backend/tests`.*
- **Production Integration, SHAP & Persistence Tests** (`tests/`):
  - `test_analytics.py`: Unit tests for analytics edge cases (0 claims, single-class labels, metric sanitization).
  - `test_demo_lifecycle.py`: Lifecycle verification across claim submission, delayed labeling, and performance computation.
  - `test_e2e_simulation.py`: End-to-end simulation loop walk from Day 0 through multiple weekly advances, asserting retrain trigger at $\ge 25$ settled, model promotion, pending claim field secrecy, and Prometheus gauge consistency.
  - `test_model_comparison.py`: Benchmark data loader, split integrity, metric calculations, and champion artifact validation.
  - `test_persistence.py`: Validates SQLite claim persistence, immutable initial predictions, delayed label persistence, and labeled-only metric queries.
  - `test_production_integration.py`: End-to-end integration tests for 14-feature XGBoost model loading, feature extraction, inference, explanations, and API responses.
  - `test_real_data_loader.py`: Verifies `carclaims_processed.csv` feature columns, data types, missing value absence, and class balance.
  - `test_seed.py`: Verifies seed data generation and cleanup.
  - `test_settlement_comparison.py`: Validates settlement-aware vs naive experiment execution and CSV output schema.
  - `test_shap_explanations.py`: Validates `shap.TreeExplainer` initialization, caching, signed SHAP direction consistency, top-5 sorting, and fallback behavior.
  - *Result: **76 passed** in `tests`.*
- **Frontend Production Build**: Verified Vite production bundle compilation (`npm run build`) in `frontend/`. 2,355 modules transformed into production assets in `frontend/dist/`.
- **Total Automated Tests**: **135 passed**.

## Current Architecture

```
Docker Compose Orchestration (docker-compose.yml)
 ├── Frontend (React SPA on Nginx, :3000)
 ├── Backend API (FastAPI, :8000)
 │     ├── Claims Ingestion & Settlement (/api/claims)
 │     ├── XGBoost Champion Model (14 features, data/models/xgb_champion.joblib)
 │     ├── Gain/Gini Feature Importance & Tree SHAP (shap.TreeExplainer + UI Bars)
 │     ├── Analytics & Dynamic Metrics (/api/analytics)
 │     ├── Simulation Pipeline (/api/sim)
 │     │     ├── Discrete clock & chronological replay (backend/data/claims_sim.csv)
 │     │     ├── Settled vs. Pending partition (Contract S1/S2)
 │     │     ├── Automated retraining every 25 settled claims (RF, LR, XGB candidates)
 │     │     ├── Model promotion gate (Candidate PR-AUC vs Serving Champion)
 │     │     ├── PSI Drift Detection (/api/sim/drift)
 │     │     ├── MLflow experiment tracking (mlruns/)
 │     │     └── DVC Cohort Snapshotting (scripts/snapshot_settled.py)
 │     └── Prometheus Exporter (/metrics)
 ├── Workflow Orchestration: Airflow DAG (dags/claimguard_retrain.py — written, not run)
 ├── Database Persistence Layer (PostgreSQL Neon / SQLite claims table)
 ├── MLflow Tracking UI (:5000, file store /mlruns)
 ├── Prometheus Server (:9090, scraping /metrics every 5s)
 └── Grafana Dashboards (:3001, provisioned Delayed-Label Monitor)
```

## Known Limitations

- **Two Separate Datasets and Models**: The real-time scoring application operates on the 14-feature automobile dataset with XGBoost, while the simulation pipeline runs on a 13-feature synthetic chronological dataset with RF/LR/XGB retraining.
- **Simulated Delays**: Delays are generated uniformly between 10 and 30 days (seed 42) rather than drawn from complex empirical hazard curves.
- **Small Simulation Dataset**: The simulation dataset contains 1,000 claims.
- **Advisory Drift Monitoring**: Feature drift monitoring via Population Stability Index (PSI) is advisory by default (`DRIFT_TRIGGERS_RETRAIN=False`).
- **Container Documentation Pending**: Multi-container stack (Compose, Prometheus, Grafana) is built and operational; detailed documentation is planned in `docs/DOCKER.md`.
- **Airflow Orchestration**: `dags/claimguard_retrain.py` is written and syntax-checked with task definitions for threshold checks, retraining, and promotion evaluation, but is not run in a live Airflow environment ([docs/AIRFLOW.md](docs/AIRFLOW.md)).
- **No Authentication or RBAC**: API endpoints are public and lack token authentication or role separation.
- **In-Memory Simulation State**: Simulation state is stored in memory and resets when the server process terminates.
- **Destructive Seed Endpoint**: `POST /api/seed` wipes the `claims` table prior to inserting test data.

## Next Steps & Roadmap

### Core MLOps & Simulation
- [x] Build automated retraining pipeline triggered by delayed label accumulation ($\ge 25$ settled).
- [x] Integrate MLflow tracking for retraining parameters, cohort sizes, and metrics.
- [x] Expose Prometheus metrics endpoint (`/metrics`) for simulation observability.
- [x] Implement model promotion rule: compare newly trained model PR-AUC against incumbent baseline before promotion.
- [x] Add Population Stability Index (PSI) drift monitoring for incoming features and predictions (`drift.py`, `/api/sim/drift`).
- [x] Implement settlement-aware vs naive retraining experiment and generate comparison curves.
- [ ] Track performance across distinct investigation cohorts and elapsed time windows.

### Explainability
- [x] Implement directional tree feature importance explanations (Gain/Gini-based).
- [x] Implement SHAP (Shapley Additive exPlanations) for local game-theoretic attribution with frontend contribution bars.

### Data & Model Enhancements
- [x] Integrate real-world automobile insurance claim dataset (`carclaims_processed.csv`, 15,419 rows).
- [x] Train and benchmark multiple model architectures (Logistic Regression, Random Forest, XGBoost).
- [x] Address severe class imbalance using class weights (`scale_pos_weight`) and PR-AUC metric selection.
- [x] Fast model loading from pre-trained serialized artifact (<10ms serving startup).

### Deployment & Observability
- [x] Multi-container orchestration via Docker Compose (`docker-compose.yml`).
- [x] Prometheus server scraping and Grafana dashboard provisioning (`monitoring/`).
- [x] DVC data and model artifact versioning (data versioning via .dvc pointers & snapshot CLI; [docs/DVC.md](docs/DVC.md)).
- [ ] Airflow workflow orchestration (DAG written and syntax-checked in `dags/claimguard_retrain.py`, not run in Airflow; [docs/AIRFLOW.md](docs/AIRFLOW.md)).
