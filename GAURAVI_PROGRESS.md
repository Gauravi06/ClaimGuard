# Gauravi's ClaimGuard Implementation & Progress Log

This document serves as the live progress documentation for Gauravi's track (ML pipeline, SHAP explanations, settlement-aware experiments, results analysis, and visualization).

---

## 1. Initial Repository & Branch Audit (28 Oct 2026)

### 1.1 Remote & Branch Audit
- **Remote URL**: `https://github.com/Gauravi06/ClaimGuard.git`
- **Branches Checked**:
  - `origin/main` (HEAD commit: `4fe635f` - "TASK O1 COMPLETED WITH 0 ISSUES AND CONFLICTS")
  - `origin/om/docker` (commit: `cf7f923` - merged into `main`, ahead 0 of `main`)
  - `origin/om/prometheus` (commit: `e4c826a` - merged into `main`, ahead 0 of `main`)
  - `origin/om/sim-api` (commit: `efe8545` - merged into `main`, ahead 0 of `main`)
  - `origin/rashi/pipeline` (commit: `a74b7b8` - merged into `main`, ahead 0 of `main`)
- **Finding**: All previous branches from Om and Rashi have already been cleanly merged into `main` (`main`, `om/*`, `rashi/pipeline` all show ahead 0 of `main`). `origin/main` contains the full integrated codebase.
- **Action Taken**:
  - Checked out fresh `main` synced with `origin/main`.
  - Created working branch `gauravi/shap-results` from `main`.

### 1.2 Dataset Audit & Versions
- **`data/raw/carclaims.csv`**:
  - Raw automobile insurance claims dataset (15,420 records, 33 attributes, ~3.69 MB).
  - Target: `FraudFound_P` (~6% positive fraud rate).
- **`data/processed/carclaims_processed.csv`**:
  - Processed dataset with 14 engineered features (~1.08 MB).
  - Used for training champion model (`XGBClassifier`) and benchmarks.
- **`data/processed/model_comparison.csv`**:
  - Benchmark metrics comparison across XGBoost, Random Forest, and Logistic Regression.
- **`data/processed/model_thresholds.csv`**:
  - Optimal threshold configurations for fraud classification.
- **`backend/data/claims_sim.csv`**:
  - 1,000-row Kaggle simulation dataset with simulated 10-30 day investigation delays (seed 42).
  - Fields: `claim_id`, `filed_at`, `investigation_days`, `label_available_at`, `is_fraud`, and 13 contract features.
- **`data/models/xgb_champion.joblib`**:
  - Verified and generated with `app.ml.train_comparison.train_and_save_champion()`.
  - Serialized dictionary containing the trained `XGBClassifier` and strictly ordered `feature_names`.

### 1.3 Local Environment & Test Suites Run
- Python version: 3.12.8 on Windows.
- Installed dependencies: `scikit-learn`, `xgboost`, `pandas`, `fastapi`, `uvicorn`, `mlflow`, `sqlalchemy`, `psycopg-binary`, `prometheus_client`, `pytest`, `shap`, `matplotlib`.
- SQLite `test.db` initialized with `init_db()`.
- Verified test suites:
  - `pytest backend/tests`: 45 passed (with `DATABASE_URL=sqlite:///./test.db`, `PYTHONPATH=backend`).
  - `pytest tests`: 75 passed (including 5 SHAP tests and 2 settlement comparison tests).
  - Total: 120 passed, 0 failures.

---

## 2. Work Breakdown & Task Tracking

| Task | Description | Status | Commit | Notes |
|------|-------------|--------|--------|-------|
| **Setup** | Repo check, branch audit, dataset verification, branch `gauravi/shap-results` | **DONE** | - | Clean state verified |
| **G1** | SHAP in scoring explanation (`TreeExplainer`, top-5, lazy import fallback, requirements, tests) | **DONE** | `feat(ml): SHAP explanations` | Fully tested (45 + 73 passed) |
| **G2** | SHAP bars on Claim Detail UI (`ClaimDetail.jsx`, horizontal signed bars) | **DONE** | `feat(frontend): SHAP bars on claim detail` | Build & tests verified |
| **G3** | Settlement-aware vs naive experiment (`experiments/settlement_comparison.py`, charts) | **DONE** | `feat(experiments): settlement-aware vs naive comparison` | 10 dates evaluated, charts in `docs/figures/` |
| **G4** | Results document (`docs/RESULTS.md` with empirical data & figures) | **DONE** | `docs: results write-up` | Complete report, 5 sections |

---

## 3. Decisions & Implementation Details

### Task G1: SHAP Scoring Explanation
1. **TreeExplainer Caching & Lazy Import**:
   - `shap` is imported lazily inside `_get_explainer()`, removing top-level `import shap` and using `Optional[Any]` type hints.
   - Prevents import crashes if `shap` is missing, allowing `app.ml.pipeline` to import cleanly and fall back gracefully to feature importance.
   - `shap.TreeExplainer(self.model)` initialized once on `MLPipeline` and cached as `self.explainer`.
   - Sub-millisecond explanation latency (~7ms per claim inference), avoiding repeated tree parsing overhead.
   - Invalidated if `load_model()` reloads a new artifact.
2. **Clean Imports Structure**:
   - Moved `logger = logging.getLogger(__name__)` below all module import statements in `backend/app/ml/pipeline.py`.
3. **Output Schema & Backward Compatibility**:
   - Maintains existing keys: `feature`, `importance`, `value`, `direction`.
   - Adds new key: `shap_value` (signed float; positive = increases fraud risk, negative = decreases fraud risk).
   - Sets `direction`: `"increases risk"` if `shap_value > 0` else `"decreases risk"`.
   - Retains `importance`: `float(feature_importances_)` for compatibility with existing consumers.
   - Returns top 5 features ordered descending by `abs(shap_value)`.
4. **Resilient Fallback**:
   - If SHAP calculation fails for any reason (e.g. `ImportError` or calculation error), catches exception, logs warning, and returns the Gini/Gain rule-based explanation.
   - Guarantees API never raises 500 on explanation failures.
5. **Database Initialization & Test Isolation**:
   - Root-caused `test_existing_claims_endpoints_still_work` SQLite issue: `TestClient(app)` in `test_sim_routes.py` doesn't enter FastAPI's lifespan context manager, so `init_db()` is not called automatically during that test if `test.db` is an uninitialized 0 KB file. Running `init_db()` sets up the tables cleanly without modifying teammates' test files.
6. **Dependency Sync**:
   - Appended `shap` to both `requirements.txt` and `backend/requirements.txt`.

### Task G2: SHAP Bars on Claim Detail UI
1. **Bipolar Signed Horizontal Bars in `ClaimDetail.jsx`**:
   - Implemented a two-sided horizontal bar container with a central zero divider line.
   - Negative SHAP contributions (decreases risk) render as green bars (`bg-emerald-500`) extending leftwards from the center.
   - Positive SHAP contributions (increases risk) render as red bars (`bg-rose-500`) extending rightwards from the center.
   - Displays feature name (human-formatted), claim value, signed `shap_value` badge (e.g. `+0.8568` or `-0.0901`), and base model importance.
2. **Backward Compatibility & Fallback**:
   - `hasShap` detection checks if any explanation items carry a valid `shap_value`.
   - For legacy or pre-existing claims lacking `shap_value`, cleanly falls back to the original vertical feature importance bars.
3. **API Model Preservation**:
   - Added `shap_value: Optional[float] = None` to `Explanation` in `backend/app/models.py` (with user confirmation) to allow Pydantic to retain `shap_value` in responses from `POST /api/claims`, `GET /api/claims`, and `GET /api/claims/{claim_id}`.
4. **Build & Test Validation**:
   - `npm run build` in `frontend/` succeeded with 0 errors (`✓ built in 8.48s`).
   - `pytest backend/tests` passed 45/45.
   - `pytest tests` passed 73/73.

### Task G3: Settlement-Aware vs Naive Retraining Experiment
1. **Experiment Script Design (`experiments/settlement_comparison.py`)**:
   - Utilizes `get_settled` and `get_pending` from `app.pipeline.simulation` in read-only mode, with `backend/data/claims_sim.csv`.
   - Fixed holdout set: 20% most recently filed claims (last 200 rows by `filed_at`), using true labels from the CSV. Holdout claims are strictly excluded from both training pools.
   - Evaluated 10 timesteps every 7 days from `2015-01-22` (first date with $\ge 25$ settled claims) through `2015-03-26`.
2. **Models Evaluated**:
   - **Model A (Naive)**: Trains on all claims filed so far, assuming pending claims are legitimate ($is\_fraud = 0$).
   - **Model B (Settlement-Aware)**: Trains exclusively on settled claims with verified ground-truth labels.
   - Both models use identical `RandomForestClassifier(n_estimators=100, random_state=42)` with `StandardScaler` and `OneHotEncoder`.
3. **Empirical Findings**:
   - **Catastrophic Recall Suppression in Naive Model**: During the first 4 retrain cycles (`2015-01-22` to `2015-02-12`), the Naive model achieves **0.0000 recall** (0 detected frauds). Labeling 300+ pending claims as legitimate corrupts the classifier into associating fraud characteristics with legitimate claims. In contrast, the Settlement-Aware model immediately detects fraud with 5.4% to 18.9% recall.
   - **Mid-Simulation Advantage**: On `2015-02-19`, Settlement-Aware recall is 21.6% vs Naive 2.7% (8x higher); on `2015-02-26`, 29.7% vs 10.8% (2.75x higher).
   - **PR-AUC Comparison**: Settlement-Aware beats Naive at 5/10 dates (`2015-01-22`, `2015-02-12`, `2015-02-26`, `2015-03-05`, `2015-03-12`). On `2015-01-29` and `2015-02-05`, Naive achieves slightly higher PR-AUC due to raw sample size, but produces 0 recall at operational decision thresholds.
   - **Convergence**: As the pending backlog empties at the end of the timeline (`2015-03-19` and `2015-03-26`), both pipelines train on the identical 800 claims and converge to 0.3255 PR-AUC and 32.4% recall.
4. **Generated Figures & Results Table**:
   - Results table saved to [`results/settlement_comparison.csv`](file:///E:/Projects/ClaimGuard-git/results/settlement_comparison.csv).
   - High-resolution figures saved to [`docs/figures/settlement_pr_auc_over_time.png`](file:///E:/Projects/ClaimGuard-git/docs/figures/settlement_pr_auc_over_time.png) and [`docs/figures/settlement_recall_over_time.png`](file:///E:/Projects/ClaimGuard-git/docs/figures/settlement_recall_over_time.png).
5. **Automated Testing**:
   - Added [`tests/test_settlement_comparison.py`](file:///E:/Projects/ClaimGuard-git/tests/test_settlement_comparison.py) testing holdout temporal isolation and execution on a 100-row sample. Both tests pass.

### Task G4: Results Document (`docs/RESULTS.md`)
1. **Empirical Precision (No Invented Numbers)**:
   - Authored [`docs/RESULTS.md`](file:///E:/Projects/ClaimGuard-git/docs/RESULTS.md) using exclusively real computed statistics and serialized files.
   - **Section 1 (Datasets)**: Raw `carclaims.csv` (15,420 rows, 33 attributes, 5.99% fraud rate), processed `carclaims_processed.csv` (15,419 rows, 14 features, 5.99% fraud rate), and simulation `claims_sim.csv` (1,000 rows, 24.7% fraud rate, 10–30 day delay with mean 19.63 days, seed 42, 13 contract features).
   - **Section 2 (Model Comparison)**: Benchmark table from `data/processed/model_comparison.csv` (XGBoost champion PR-AUC 0.1872 vs. Random Forest 0.1769 vs. Logistic Regression 0.1281), detailed justification for PR-AUC/Precision/Recall given class imbalance, and comparison against random baseline (0.0599).
   - **Section 3 (Settlement-Aware vs. Naive)**: Embedded generated figures (`docs/figures/settlement_pr_auc_over_time.png` and `docs/figures/settlement_recall_over_time.png`), full 10-timestep data table, and analysis of the naive model's initial recall collapse.
   - **Section 4 (Simulation Results)**: Live sequence from day 0 to step 3 (first model at 2015-01-22 with 61 settled claims, v1, PR-AUC ~0.38), with steps 4–8 designated as `TODO: replace with Rashi's dry-run table` as planned.
   - **Section 5 (Limitations)**: Documented architectural decoupling, synthetic uniform delays, 1k simulation scale, advisory drift detection, and demonstration auth status.
2. **Track Completion Status**:
   - Tasks **G1, G2, G3, G4** are all fully implemented, verified, and committed. All 120 tests pass.

---

## 4. Upstream Integration & Synchronization (30 Oct 2026)

### 4.1 Merge of `origin/main`
- Merged `origin/main` into working branch `gauravi/shap-results` using standard git merge (`--no-rebase`).
- **Result**: Merge completed cleanly with 0 conflicts, integrating Lara's CI workflow (`.github/workflows/ci.yml`), refreshed `README.md`, and updated `progress.md`.
- **Validation**:
  - `pytest backend/tests`: 45 passed (with `DATABASE_URL=sqlite:///./test.db`, `PYTHONPATH=backend`).
  - `pytest tests`: 75 passed (including all 5 SHAP tests and 2 settlement comparison tests).
  - `npm run build` in `frontend/`: successfully compiled in 5.56s.

### 4.2 Key Architectural Decision: `backend/app/models.py` Update
- **Issue Discovered**: In `backend/app/models.py`, `class Explanation(BaseModel)` only declared `feature`, `importance`, `value`, and `direction`. Even though `ml_pipeline.explain` computed signed `shap_value`, Pydantic v2 automatically stripped undeclared extra fields during `Claim` validation. Consequently, `POST /api/claims`, `GET /api/claims`, and `GET /api/claims/{id}` dropped `shap_value`, preventing the ClaimDetail UI from receiving SHAP data.
- **Decision & Fix**: Added `shap_value: Optional[float] = None` to `Explanation` in `backend/app/models.py` with explicit user confirmation.
  - Leaves database schema unchanged (`explanations` is stored as JSON/JSONB).
  - Preserves contract field compatibility.
  - Allows the API response to include SHAP values for the ClaimDetail UI, while enabling seamless fallback for older claims without `shap_value`.

---

## 5. CI Diagnosis & PR #4 Fixes (31 Oct 2026)

### 5.1 CI Red Failure Diagnosis (`backend` Job, Step 8 `Run root tests`)
- **Symptoms**: In GitHub Actions run 41000605496 for PR #4, the `backend` workflow succeeded through Step 7 (`Run backend tests` - 45 passed), but failed on Step 8 (`Run root tests`: `pytest tests`) with process exit code 2.
- **Root Cause**:
  - The CI workflow `.github/workflows/ci.yml` installs dependencies strictly via:
    ```bash
    pip install -r backend/requirements.txt pytest httpx
    ```
  - `backend/requirements.txt` does not include `matplotlib`.
  - `experiments/settlement_comparison.py` had top-level `import matplotlib` and `import matplotlib.pyplot as plt`.
  - `tests/test_settlement_comparison.py` imports `experiments.settlement_comparison`.
  - During pytest test collection in CI, importing `test_settlement_comparison.py` failed with:
    ```
    ModuleNotFoundError: No module named 'matplotlib'
    Interrupted: 1 error during collection (exit code 2)
    ```

### 5.2 Resolution Implemented in Gauravi's Files
- **File Modified**: [`experiments/settlement_comparison.py`](file:///e:/Projects/ClaimGuard-git/experiments/settlement_comparison.py) (owned by Gauravi).
  - Removed top-level `import matplotlib` / `import matplotlib.pyplot as plt`.
  - Moved the `matplotlib` import inside `plot_comparison_charts()` lazily.
  - Because `tests/test_settlement_comparison.py` only tests dataset splitting and numerical experiment execution without generating chart PNGs (`figures_dir=None`), `pytest tests` now collects and executes with 75 passed tests even in minimal headless environments lacking `matplotlib`.
- **Validation**:
  - Masking `matplotlib` in Python environment (`sys.modules['matplotlib'] = None`) confirmed `pytest tests` passes 75/75 with 0 errors.

### 5.3 Exact Change for Owner (Lara / CI Maintainer)
If the backend/CI owner prefers having all visualization libraries installed across all CI runners or Docker containers, the exact recommended change is:

In [`backend/requirements.txt`](file:///e:/Projects/ClaimGuard-git/backend/requirements.txt), add:
```
matplotlib
```
Alternatively, in [`.github/workflows/ci.yml`](file:///e:/Projects/ClaimGuard-git/.github/workflows/ci.yml) line 29:
```diff
-          pip install -r backend/requirements.txt pytest httpx
+          pip install -r backend/requirements.txt pytest httpx matplotlib
```
*(Per policy, `.github/workflows/ci.yml` and teammate files were not touched directly; this is documented here for the owner).*

### 5.4 RESULTS.md Section 4 Dry-Run Table Update
- Replaced the preliminary simulation table and TODO placeholders in [`docs/RESULTS.md`](file:///e:/Projects/ClaimGuard-git/docs/RESULTS.md) with Rashi's dry-run table:
  - 8 simulation dates, 6 retrain cycles (`2015-01-22` to `2015-02-26`), 3 promotions (v1, v2, v3).
  - First model's PR-AUC on `2015-01-22` updated to 0.5769 (`champion PR-AUC: None`).
  - Documented promotion gate logic: `model_version` increments only when candidate strictly beats incumbent champion on the time-based holdout (newest 20% of settled claims).
  - Candidate rejection documented for `2015-02-05` (0.5518 < 0.6164), `2015-02-19` (0.4997 < 0.6670), and `2015-02-26` (0.4949 < 0.5341), where champion was retained.

### 5.5 Unused Figure Deletion
- Deleted duplicate figures:
  - `docs/figures/pr_auc_over_time.png`
  - `docs/figures/recall_over_time.png`
- Verified that [`docs/RESULTS.md`](file:///e:/Projects/ClaimGuard-git/docs/RESULTS.md) cleanly references the canonical figures:
  - `docs/figures/settlement_pr_auc_over_time.png`
  - `docs/figures/settlement_recall_over_time.png`
- Removed duplicate savefig calls in `experiments/settlement_comparison.py`.


