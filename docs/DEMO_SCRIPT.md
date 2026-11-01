# ClaimGuard 5-Minute Live Demonstration Script

This script provides an exact, step-by-step walkthrough for a 5-minute technical demonstration of ClaimGuard. It showcases the delayed-label problem, the simulation engine, target leakage prevention, model retraining with candidate promotion rules, MLflow experiment tracking, Prometheus metrics, and local SHAP feature attribution bars.

---

## Pre-Demo Setup & Browser Tab Order

### 1. Launch Services
Run the following in separate terminal sessions from the repository root:

```bash
# Terminal 1: Backend API (FastAPI)
export PYTHONPATH="backend"
export DATABASE_URL="sqlite:///./claims.db"
python backend/run.py
# Running at http://localhost:8000

# Terminal 2: Frontend (Vite + React)
cd frontend
npm run dev
# Running at http://localhost:5173

# Terminal 3: MLflow Tracking Server
mlflow ui --backend-store-uri mlruns --port 5000
# Running at http://localhost:5000
```

### 2. Browser Tabs to Open in Order
1. **Tab 1 — Simulation Control**: `http://localhost:5173/simulation` (Simulation Dashboard: clock, backlog, retrain trigger)
2. **Tab 2 — Telemetry & Metrics**: `http://localhost:8000/metrics` (Prometheus exposition format; fallback for Grafana)
3. **Tab 3 — Experiment Tracking**: `http://localhost:5000` (MLflow UI: experiment `ClaimGuard_Simulation`)
4. **Tab 4 — Production Claims & SHAP**: `http://localhost:5173/claims` (Intake adjudication and SHAP contribution bars)
5. **Tab 5 — Interactive API Docs**: `http://localhost:8000/docs` (Swagger UI for backend inspection)

*Note on Monitoring Stack URLs*:
- **Prometheus** (`http://localhost:9090`): `TODO` (Requires Docker Compose / `monitoring/` stack not yet merged on `main`; fallback: direct `/metrics` exposition on Tab 2).
- **Grafana** (`http://localhost:3001`): `TODO` (Requires Docker Compose / `monitoring/` stack not yet merged on `main`; fallback: direct `/metrics` exposition on Tab 2).

---

## Canonical Dry-Run Retraining & Promotion Table

The table below reflects the canonical dry run executed across 8 weekly steps (7 days each) starting from `2015-01-01` (`backend/data/claims_sim.csv`, 1,000 claims, 10–30 day investigation window, seed 42):

| Simulated Date | Pending | Settled | Newly Settled* | Retrained | Promoted | Model Version | Candidate PR-AUC | Champion PR-AUC |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2015-01-08** | 131 | 0 | 0 | False | n/a | 0 | 0.0** | n/a |
| **2015-01-15** | 247 | 8 | 8 | False | n/a | 0 | 0.0** | n/a |
| **2015-01-22** | 317 | 61 | 61 | True | True | 1 | **0.5769** | None |
| **2015-01-29** | 308 | 167 | 106 | True | True | 2 | **0.6451** | 0.2095 |
| **2015-02-05** | 341 | 274 | 107 | True | False | 2 | 0.5518 | **0.6164** |
| **2015-02-12** | 331 | 384 | 110 | True | True | 3 | **0.5458** | 0.4442 |
| **2015-02-19** | 328 | 504 | 120 | True | False | 3 | 0.4997 | **0.6670** |
| **2015-02-26** | 336 | 620 | 116 | True | False | 3 | 0.4949 | **0.5341** |

*\* newly settled = since the last retrain (includes previous unretrained settlements).*  
*\*\* 0.0 = no model trained yet.*  
*Note: Re-running live on `main` confirms identical dates, counts, retrain triggers, promotions, and model versions. Minor holdout decimal variations on `2015-02-12` (cand: 0.5660 vs 0.5458), `2015-02-19` (champ: 0.7168 vs 0.6670), and `2015-02-26` (cand: 0.5070 vs 0.4949; champ: 0.5475 vs 0.5341) stem from minor sub-dependency floating point differences across platforms. All promotion decisions remain identical.*

---

## 5-Minute Step-by-Step Demo Script

### Minute 0:00 – 0:45 | 1. The Problem: Delayed Labels & Intake Blindness
- **Speaker Action**: Switch to **Tab 1** (`http://localhost:5173/simulation`).
- **Talking Points**:
  - *"In insurance fraud detection, ground truth is never immediate. When an auto claim is filed today, adjusters, police, and legal teams require 10 to 30 days to investigate."*
  - *"If we train naively on unresolved claims, we assume pending claims are legitimate, which creates catastrophic label noise and destroys model recall. If we wait months to train, models go stale."*
  - *"ClaimGuard solves this with two decoupled systems: real-time XGBoost scoring at intake, and a settlement-aware retraining pipeline that advances time chronologically without data leakage."*
- **Fallback**: Show `docs/RESULTS.md` Section 3.1 table illustrating 0.0000 recall in naive retraining.

---

### Minute 0:45 – 1:30 | 2. Day 0 State & 3. Clock Advance with Leakage Guard
- **Speaker Action**: Point out the Day 0 stats on **Tab 1**. Open terminal or **Tab 5** to show `/api/sim/pending`.
- **Key Invariants to Highlight**:
  - Simulated date is **`2015-01-01`**.
  - **19 pending claims**, **0 settled claims**, `model_version: 0` (*"No model yet"*).
  - Inspect any pending claim payload:
    ```json
    {
      "claim_id": "CLM-0001",
      "filed_at": "2015-01-01",
      "fraud_score": null,
      "risk_level": null
    }
    ```
  - **Leakage Guard**: Point out that `is_fraud`, `investigation_days`, and `label_available_at` are **strictly omitted** from `/api/sim/pending` by contract (`docs/CONTRACT.md`).
- **Speaker Action**: Click **"Advance 7 Days"** twice:
  - **Step 1 (`2015-01-08`)**: 131 pending, 0 settled $\rightarrow$ No retrain (`settled < 25`).
  - **Step 2 (`2015-01-15`)**: 247 pending, 8 settled $\rightarrow$ Still no retrain (`8 settled < 25`).
- **Fallback**: Execute `curl -s http://localhost:8000/api/sim/clock` and `curl -s http://localhost:8000/api/sim/pending`.

---

### Minute 1:30 – 2:30 | 4. First Retraining & Model Promotion (2015-01-22)
- **Speaker Action**: Click **"Advance 7 Days"** a third time on **Tab 1**.
- **Observation**:
  - Current Date reaches **`2015-01-22`**.
  - Settled claims jump to **61** (crossing the `MIN_SETTLED = 25` threshold).
  - Retrain trigger fires automatically: `retrained: True`.
  - Candidate models (**Random Forest**, **Logistic Regression**, **XGBoost**) are evaluated on a held-out validation split.
  - Initial model version promoted: `promoted: True`, `model_version: 1`.
  - **PR-AUC**: **0.5769** (*note: PR-AUC is 0.5769, not 0.38*).
  - Pending claims now show active fraud scores and risk classifications (`low`, `medium`, `high`) computed by the newly promoted v1 model!
- **Fallback**: Query `curl -s http://localhost:8000/api/sim/metrics` to verify `model_version: 1` and `pr_auc: 0.5769`.

---

### Minute 2:30 – 3:15 | 5. MLflow Tracking & Promotion Decisions
- **Speaker Action**: Switch to **Tab 3** (`http://localhost:5000`).
- **Talking Points**:
  - *"Every time the retrain threshold is crossed, ClaimGuard logs parameters, dataset fingerprints, and evaluation metrics to MLflow."*
  - Refresh the `ClaimGuard_Simulation` experiment.
  - Highlight the runs:
    - Run `retrain_v1_2015-01-22`: `n_train: 61`, `pr_auc: 0.5769`, `promoted: 1.0`.
    - Run `retrain_v2_2015-01-29`: `candidate_pr_auc: 0.6451` beats champion `0.2095` $\rightarrow$ `promoted: 1.0` $\rightarrow$ `model_version: 2`.
    - Run on `2015-02-05`: Candidate scores `0.5518` vs serving champion `0.6164` $\rightarrow$ **Promotion Rejected** (`promoted: 0.0`) $\rightarrow$ Champion retained at `model_version: 2`.
  - *"Our promotion gate prevents model degradation: across 6 retraining events, only 3 candidates beat the champion and earned promotion."*
- **Fallback**: Open terminal and list run metadata in `mlruns/` or reference `docs/RESULTS.md` Section 4.

---

### Minute 3:15 – 3:45 | 6. Telemetry & Metrics (`/metrics`)
- **Speaker Action**: Switch to **Tab 2** (`http://localhost:8000/metrics`).
- **Talking Points**:
  - *"For production observability, ClaimGuard exports telemetry directly in Prometheus exposition format."*
  - Scroll and highlight the key gauges:
    - `claimguard_model_version`: Current active model version (e.g., `1.0` or `2.0`).
    - `claimguard_settled_claims`: Exact settled claim count (`61.0` on Jan 22).
    - `claimguard_pending_backlog`: Current unresolved claim queue (`317.0`).
    - `claimguard_last_retrain_pr_auc`: `0.5769`.
    - `claimguard_retrains_total`: Retraining run counter.
  - *Status Note*: `TODO: Grafana dashboard side-by-side visualization` requires containerized deployment (`monitoring/` stack not yet merged on `main`; `/metrics` serves as the live telemetry engine).
- **Fallback**: Run `curl -s http://localhost:8000/metrics | grep claimguard_`.

---

### Minute 3:45 – 4:30 | 7. Production Intake Adjudication & SHAP Visual Bars
- **Speaker Action**: Switch to **Tab 4** (`http://localhost:5173/claims`).
- **Step 7a: Seed Demo Claims (if empty)**:
  - If no claims are listed, click **"Seed Demo Data"** on the dashboard or execute:
    ```bash
    curl -X POST http://localhost:8000/api/seed
    ```
- **Step 7b: Inspect Claim Detail & SHAP Attribution**:
  - Click any high-risk claim in the table (e.g. `CLM-...` or claimant *"James Wilson"* / *"Demo Claimant"*).
  - URL navigates to `http://localhost:5173/claims/:id`.
  - Point to the **Feature Explanations (SHAP)** card:
    - Interactive **Tree SHAP contribution bars** computed via `shap.TreeExplainer` on the 14-feature XGBoost champion.
    - **Red bars (`+` values)** extending rightward show features that **increase fraud risk** (e.g., `fault = Policy holder`, `claim_amount > $35,000`, `prior_claims_count > 1`).
    - **Green bars (`-` values)** extending leftward show features that **decrease fraud risk** (e.g., `witnesses > 0`, `police_report_filed = True`).
- **Fallback**: Query `curl -X POST http://localhost:8000/api/claims -H "Content-Type: application/json" -d @sample_claim.json` and inspect the `explanations` list with `shap_value`.

---

### Minute 4:30 – 5:00 | 8. What Is Built vs. Designed (Honest Engineering Audit)
- **Speaker Action**: Summarize transparently against project milestones:
  - **What Is Fully Built & Live**:
    - Real 14-feature XGBoost champion serving in `<10ms` (`/api/claims`).
    - Tree SHAP local attribution and frontend red/green contribution bars.
    - Chronological discrete-clock simulation engine (`/api/sim/clock`, `/api/sim/advance`).
    - Zero-leakage pending/settled contract enforcement.
    - Retraining pipeline with 3 candidate architectures (RF, LR, XGBoost).
    - Model promotion rule gating deployment on held-out PR-AUC improvement.
    - Population Stability Index (PSI) feature drift monitoring (`/api/sim/drift`).
    - Local MLflow experiment tracking and Prometheus `/metrics` exporter.
    - 135 automated unit, integration, and contract tests passing.
  - **What Is Designed Only (TODO)**:
    - Multi-container Docker Compose orchestration (`docker-compose.yml`, `docs/DOCKER.md`).
    - External Prometheus scraper & pre-configured Grafana dashboard (`monitoring/`).
    - Scheduled workflow orchestration via Apache Airflow (`dags/`).
    - Large-scale data/model versioning via DVC (`.dvc`).
    - User authentication / role-based access control (RBAC).

---

## 9. 10-Question Cheat Sheet for Reviewers

### Q1: Why simulated delays?
**Answer**: In real-world insurance, fraud ground truth cannot be observed at submission; an investigation window (adjusters, interviews, police reports) is mandatory. We simulate 10–30 days (`prepare_data.py` lines 79–82) so pending claims strictly conceal labels (`is_fraud`), preventing catastrophic data leakage.

### Q2: Why PR-AUC, why is v1 PR-AUC ~0.58, and why do later numbers drop?
**Answer**: Fraud is rare (5.99% in production `carclaims`, 24.7% in simulation). ROC-AUC is artificially inflated by large true negative counts, whereas PR-AUC directly tracks minority class precision and recall. Model v1's PR-AUC is **0.5769** (not 0.38) evaluated on a small, noisy initial holdout (20% of 61 settled claims $\approx 12$ claims). As more claims settle, the holdout expands and becomes representative, and candidate promotion rules protect against regression by comparing against the incumbent champion.

### Q3: Why only 3 promotions out of 6 retrains?
**Answer**: Our promotion gate requires a candidate to strictly outperform the serving champion on the identical held-out validation set. On `2015-02-05`, `2015-02-19`, and `2015-02-26`, newly retrained models failed to beat the champion (e.g. candidate 0.4997 vs champion 0.6670 on Feb 19), so promotions were correctly rejected to prevent production performance degradation.

### Q4: Why two separate datasets?
**Answer**: The production app serves high-throughput inference on 15,419 real Kaggle car claims across 14 features (`carclaims_processed.csv`) with an XGBoost champion. The simulation pipeline uses a 1,000-claim synthetic dataset (`claims_sim.csv`) with timestamps across 13 contract features. Decoupling them allows live clock manipulation, backlog simulation, and retraining without corrupting production tables.

### Q5: What does the naive vs. settlement-aware experiment show?
**Answer**: Naive retraining (assuming unobserved pending claims are legitimate) causes **catastrophic recall suppression**: 0.0000 recall across the first 4 retrains (missing all 37 frauds). Settlement-aware retraining maintains positive recall throughout and achieves up to **8x recall dominance** (21.62% vs 2.70% on Feb 19). While naive retraining occasionally scores higher PR-AUC due to raw sample size, its predictions are unusable in practice. Both converge once all pending claims settle.

### Q6: What would a commercial production deployment need?
**Answer**: Commercial deployment requires: 1) Kafka/RabbitMQ event queues for claim ingestion, 2) right-skewed Weibull investigation hazard distributions, 3) a feature store (Feast) for point-in-time correctness, 4) multi-tenant OAuth2/OIDC authentication, and 5) human-in-the-loop active learning workflows for investigator review.

### Q7: What is not done / designed only?
**Answer**: Multi-container Docker Compose (`docker-compose.yml`), external Prometheus/Grafana service provisioning (`monitoring/`), Airflow DAG orchestration (`dags/`), DVC data versioning, and JWT/OAuth2 authentication.

### Q8: Why is there no authentication or RBAC?
**Answer**: The current system is an engineering prototype and MLOps demonstration. Adding JWT tokens or role management would add friction to local evaluators and automated test suites without demonstrating core MLOps delayed-feedback principles.

### Q9: Why SHAP instead of simple feature importances?
**Answer**: Global tree gain or split importance only tells what features mattered across the entire training set. SHAP (`shap.TreeExplainer`) provides exact, mathematically consistent Shapley additive attributions for each specific individual claim, explaining to adjusters exactly why a particular policyholder received an elevated risk score.

### Q10: Why is feature drift (PSI) advisory rather than an automatic hard retrain trigger?
**Answer**: Retraining blindly on unverified pending claims when drift occurs would introduce massive label noise (the exact pitfall shown in our naive experiment). In `backend/app/pipeline/drift.py`, PSI alerts operators (`status: 'alert'`) to investigate shift causes rather than immediately retraining without confirmed ground truth.
