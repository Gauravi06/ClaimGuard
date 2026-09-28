# ClaimGuard Progress

## Completed

- **FastAPI Backend Core**: RESTful API built with FastAPI, Pydantic v2 schemas, and CORS middleware.

- **Persistent Claim Store (Neon PostgreSQL)**: Single `claims` table via SQLAlchemy 2 (sync) + psycopg 3, configured by `DATABASE_URL`. The store keeps the original API (`add/get/get_all/update_label`) plus `add_many/get_labeled/count/clear`. Fraud score, prediction, risk level, and explanations are stored at creation and never re-scored; `true_label` is `NULL` until a delayed label arrives. Table is created with `create_all` at startup.

- **Scikit-Learn ML Pipeline**: `RandomForestClassifier` baseline trained on synthetic insurance claim features at server startup.

- **Real-time Explainable Risk Scoring**: Claim ingestion endpoint predicts fraud probabilities (0–100%), assigns risk levels (`low`, `medium`, `high`), and returns feature importance explanations.

- **Delayed-Label Workflow**: Endpoint (`PATCH /api/claims/{id}/label`) allowing delayed ground-truth labels (`true_label: bool`) to be applied after investigation.

- **Model Performance Analytics**: Live evaluation endpoint (`GET /api/analytics/model-performance`), querying only claims with `true_label IS NOT NULL`, computing Accuracy, Precision, Recall, F1 Score, ROC-AUC, and Confusion Matrix.

- **Edge-case Protection**: Safe handling of zero-labeled claims and single-class distributions so undefined metrics (such as ROC-AUC with only one class) return `null` without throwing HTTP 500 errors.

- **Delayed Label Simulator**: Endpoint (`POST /api/simulate/delayed-labels`) allowing bulk generation of historical claims with simulated investigation labels.

- **Development Seed Feature**: CLI tool (`python -m backend.seed`) and endpoint (`POST /api/dev/seed`) to populate 20 realistic claims (7 fraud, 7 legitimate, 6 unlabeled).

- **React 18 + Tailwind CSS 4 Frontend**: Professional insurance-tech dashboard featuring Sidebar Navigation, Overview Dashboard, Claim Submission Form with circular risk gauge, Claims Table, Claim Details view with feature risk bars, Model Performance dashboard, and Delayed Label Simulator interface.

## Tested

- **Unit Tests**: Full test suite covering:
  - 0 claims (empty state)
  - 1 labeled claim / single-class edge cases (ROC-AUC `null` handling)
  - Multi-class dataset evaluation (Accuracy, Precision, Recall, F1, ROC-AUC calculations)
  - Development seed generation and risk score assignment

- **Persistence Tests** (`tests/test_persistence.py`, SQLite): Verified unlabeled-on-create behavior, identical read-back, stored prediction read-back without re-scoring, label persistence, exclusion of unlabeled claims from metrics, labeled-only queries, simulator persistence, and seed wipe behavior.

- **Restart Persistence (SQLite, real uvicorn restarts)**: Claims, scores, predictions, explanations, and delayed labels verified identical across application restarts.

- **Neon PostgreSQL Smoke Test**: `python backend/neon_smoke_test.py` successfully verified the real Neon PostgreSQL connection and persistence behavior. **13/13 checks passed**, including database connectivity, table creation, claim creation and retrieval, unlabeled claims being excluded from metrics, persistence across restarts, preservation of original prediction fields after delayed labeling, delayed-label persistence, Model Performance updates after labels arrive, PostgreSQL column types, and smoke-test cleanup.

- **Frontend Build**: Verified production build (`npm run build`) via Vite compiler. Build completed successfully; the existing bundle-size warning remains a future optimization item.

- **CLI Seed Tool**: Tested `python -m backend.seed` against the database-backed store, including seed generation and destructive replacement behavior.

## Current Architecture

React (Vite + Tailwind v4)
        │
        │ REST API
        ▼
FastAPI Backend
   ┌────┼────────────┐
   │    │            │
   ▼    ▼            ▼
 Claims Analytics  ML Pipeline
   │                  │
   │                  ▼
   │            RandomForest
   │            Risk Scoring
   │            Explanations
   │
   ▼
Neon PostgreSQL
   │
   └── claims table

### 1. Frontend

SPA built with React 18, React Router v6, Tailwind CSS v4, Recharts, and Lucide Icons.

Uses the Vite development proxy:

`/api` → `http://localhost:8000`

The frontend currently provides:
- Overview Dashboard
- Claim Submission
- Claims Table
- Claim Details
- Risk Score / Risk Level
- Feature Explanations
- Model Performance
- Delayed Label Simulator

### 2. Backend

Python 3.12 FastAPI service structured with:
- `routes/claims.py` — claim submission, retrieval, labeling, simulation
- `routes/analytics.py` — model performance metrics
- `routes/seed.py` — development seed functionality
- `database.py` — database-backed claim store
- `orm.py` — SQLAlchemy `claims` table definition
- `models.py` — Pydantic schemas
- `ml/` — ML dataset generation and RandomForest pipeline
- `main.py` — FastAPI application entry point and lifespan

### 3. Database

Claim persistence uses:
- Neon PostgreSQL
- SQLAlchemy 2
- psycopg 3
- `DATABASE_URL` environment variable

The application stores the prediction generated at claim creation rather than recalculating it when the claim is later retrieved.

A claim can therefore move through:

Submitted
    ↓
Prediction stored
    ↓
true_label = NULL
    ↓
Pending investigation
    ↓
Delayed label arrives
    ↓
true_label stored
    ↓
Original prediction evaluated

### 4. ML Layer

Baseline model:

RandomForestClassifier
├── 100 estimators
└── max_depth = 5

The model is currently trained on **500 synthetic insurance claim samples** at server startup.

Current prediction flow:

Claim features
    ↓
RandomForest
    ↓
Fraud probability
    ↓
Risk level
    ↓
Feature explanations
    ↓
Persist prediction

Current thresholds:

score < 0.30         → low
0.30 ≤ score < 0.70  → medium
score ≥ 0.70         → high

The stored binary prediction is based on:

`fraud_score > 0.50`

## Known Limitations

- **Destructive Dev Seed**: `POST /api/dev/seed` (and related seed functionality, including `python -m backend.seed`) deletes existing claims before inserting the development dataset. It is unauthenticated and unguarded. Do not run it against data you want to keep.

- **No Schema Migrations**: The database schema is currently created with SQLAlchemy `create_all`; Alembic has not yet been introduced.

- **Synthetic Data**: The current ML pipeline uses synthetic insurance features rather than proprietary or real-world insurance claim records.

- **Static Baseline Model**: The model is trained once at application startup. Automated retraining, model promotion, and drift monitoring are not yet implemented.

- **No Model Version Tracking**: Predictions currently do not record an explicit model version alongside the stored prediction.

- **No Production Authentication**: The API currently has no user authentication or role-based access control.

- **Development-Oriented Infrastructure**: The application is currently structured as an MVP/development system rather than a production insurance fraud platform.

## Tentative Next Steps

*(Planned for future iterations — not yet implemented)*

### Core MLOps / Delayed-Label Workflow

- [ ] Add model versioning so every prediction records which model version produced it.
- [ ] Build a retraining workflow using newly arrived delayed labels.
- [ ] Compare newly trained models against the currently deployed baseline before promotion.
- [ ] Track model performance across prediction cohorts and investigation periods.
- [ ] Add drift monitoring for incoming claim features and model predictions.

### Explainability

- [ ] Evaluate SHAP (Shapley Additive exPlanations) for more robust local feature explanations.

### Data / Model Improvements

- [ ] Evaluate the pipeline on a real or public insurance fraud dataset.
- [ ] Address class imbalance and evaluate appropriate fraud-detection metrics.
- [ ] Add reproducible model training and experiment tracking (e.g. MLflow).

### Production Infrastructure

- [ ] Add Alembic migrations for the existing SQLAlchemy schema.
- [ ] Guard or authenticate the destructive development seed endpoint.
- [ ] Add user authentication (OAuth2 / JWT) and role-based access control (e.g. Adjuster vs Analyst views).
- [ ] Add stronger API and frontend integration tests.
- [ ] Add Docker-based deployment and production configuration.