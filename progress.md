# ClaimGuard Progress

## Completed

- **FastAPI Backend Core**: RESTful API built with FastAPI, Pydantic v2 schemas, and CORS middleware.
- **Persistent Claim Store (Neon PostgreSQL)**: Single `claims` table via SQLAlchemy 2 (sync) + psycopg 3, configured by `DATABASE_URL`. The store keeps the original API (`add/get/get_all/update_label`) plus `add_many/get_labeled/count/clear`. Fraud score, prediction, risk level and explanations are stored at creation and never re-scored; `true_label` is `NULL` until a delayed label arrives. Table created with `create_all` at startup.
- **Scikit-Learn ML Pipeline**: `RandomForestClassifier` baseline trained on synthetic insurance claim features at server startup.
- **Real-time Explainable Risk Scoring**: Ingestion endpoint that predicts fraud probabilities (0–100%), assigns risk levels (`low`, `medium`, `high`), and returns feature importance explanations.
- **Delayed-Label Workflow**: Endpoint (`PATCH /api/claims/{id}/label`) allowing delayed ground-truth labels (`true_label: bool`) to be applied post-investigation.
- **Model Performance Analytics**: Live evaluation endpoint (`GET /api/analytics/model-performance`), querying only claims with `true_label IS NOT NULL`, computing Accuracy, Precision, Recall, F1 Score, ROC-AUC, and Confusion Matrix.
- **Edge-case Protection**: Safe handling of zero-labeled claims and single-class distributions so undefined metrics (like ROC-AUC with 1 class) return `null` without throwing HTTP 500 errors.
- **Delayed Label Simulator**: Endpoint (`POST /api/simulate/delayed-labels`) allowing bulk generation of historical claims with simulated investigation labels.
- **Development Seed Feature**: CLI tool (`python -m backend.seed`) and endpoint (`POST /api/dev/seed`) to populate 20 realistic claims (7 fraud, 7 legitimate, 6 unlabeled).
- **React 18 + Tailwind CSS 4 Frontend**: Professional insurance-tech dashboard featuring Sidebar Navigation, Overview Dashboard, Claim Submission Form with circular risk gauge, Claims Table, Claim Details view with feature risk bars, Model Performance dashboard, and Delayed Label Simulator interface.

## Tested

- **Unit Tests**: Full test suite (`tests/test_analytics.py`, `tests/test_seed.py`) covering:
  - 0 claims (empty state)
  - 1 labeled claim / single-class edge cases (ROC-AUC `null` handling)
  - Multi-class dataset evaluation (Accuracy, Precision, Recall, F1, ROC-AUC calculations)
  - Development seed generation & risk score assignment
- **Persistence tests** (`tests/test_persistence.py`, SQLite): unlabeled-on-create, identical read-back, stored prediction read (not recomputed), label persistence, unlabeled claims excluded from metrics, labeled-only query, simulator and seed persistence (incl. seed wipe behavior).
- **Restart persistence (SQLite, real uvicorn restarts)**: claims, scores, predictions, explanations and delayed labels verified identical across restarts (manual scratch test).
- **Neon smoke test**: `python backend/neon_smoke_test.py` provided; **not yet recorded as run against Neon** (record the result here once run).
- **Frontend Build**: Verified production build (`npm run build`) via Vite compiler without warnings or errors.
- **CLI Seed Tool**: Tested `python -m backend.seed` on Windows environment verifying HTTP and in-memory execution paths.

## Current Architecture

```text
React (Vite + Tailwind v4) ──REST API──> FastAPI Backend ──> Scikit-Learn RandomForest Pipeline
      │                                       │                         │
      └─ Dashboard / Forms / Charts           └─ Neon PostgreSQL        └─ Risk Scoring & Explanations
```

1. **Frontend**: SPA built with React 18, React Router v6, Tailwind CSS v4, Recharts, and Lucide Icons. Uses Vite proxy (`/api` -> `http://localhost:8000`).
2. **Backend**: Python 3.12 FastAPI service structured with routes (`claims`, `analytics`, `seed`), database store (`database.py`, `orm.py`), and ML pipeline module (`app/ml`).
3. **ML Layer**: Baseline `RandomForestClassifier` (100 estimators, max depth 5) trained on 500 synthetic samples.

## Known Limitations

- **Destructive Dev Seed**: `POST /api/dev/seed` (and `/api/seed`, `python -m backend.seed`) deletes ALL claims, is unauthenticated and unguarded. Do not run it against data you want to keep.
- **No Migrations**: Schema is created with `create_all`; there is no Alembic yet.
- **Synthetic Data**: Uses synthetic insurance features rather than proprietary enterprise claim records.
- **Static Baseline**: ML model is trained once at startup; does not yet feature automated online retraining or drift monitoring.

## Tentative Next Steps

*(Planned for future iterations — not yet implemented)*

- [ ] Add Alembic migrations for the existing SQLAlchemy schema, and guard or authenticate the dev seed endpoint.
- [ ] Implement MLOps workflow with MLflow for experiment tracking and automated model re-training.
- [ ] Integrate SHAP (Shapley Additive exPlanations) for advanced local feature explainability.
- [ ] Add user authentication (OAuth2 / JWT) and role-based access control (Adjuster vs Analyst views).
