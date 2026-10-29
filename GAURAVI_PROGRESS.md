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
- Installed dependencies: `scikit-learn`, `xgboost`, `pandas`, `fastapi`, `uvicorn`, `mlflow`, `sqlalchemy`, `psycopg-binary`, `prometheus_client`, `pytest`, `shap`.
- SQLite `test.db` initialized with `init_db()`.
- Verified test suites:
  - `pytest backend/tests`: 45 passed (with `DATABASE_URL=sqlite:///./test.db`, `PYTHONPATH=backend`).
  - `pytest tests`: 73 passed (including all 5 SHAP tests in `tests/test_shap_explanations.py`).
  - Total: 118 passed, 0 failures.

---

## 2. Work Breakdown & Task Tracking

| Task | Description | Status | Commit | Notes |
|------|-------------|--------|--------|-------|
| **Setup** | Repo check, branch audit, dataset verification, branch `gauravi/shap-results` | **DONE** | - | Clean state verified |
| **G1** | SHAP in scoring explanation (`TreeExplainer`, top-5, lazy import fallback, requirements, tests) | **DONE** | `feat(ml): SHAP explanations` | Fully tested (45 + 73 passed) |
| **G2** | SHAP bars on Claim Detail UI (`ClaimDetail.jsx`, horizontal signed bars) | **DONE** | `feat(frontend): SHAP bars on claim detail` | Build & tests verified |
| **G3** | Settlement-aware vs naive experiment (`experiments/settlement_comparison.py`, charts) | Pending | `feat(experiments): settlement-aware vs naive comparison` | Next prompt |
| **G4** | Results document (`docs/RESULTS.md` with empirical data & figures) | Pending | `docs: results write-up` | Next |

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
