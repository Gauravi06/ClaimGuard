# ClaimGuard — Insurance Fraud Detection System

> A full-stack MVP for early insurance fraud detection that flags suspicious claims immediately upon submission despite ground-truth fraud labels arriving weeks or months later.

---

## Problem Statement

In real-world insurance operations, ground-truth fraud labels are severely delayed. When a claim is submitted, it is unknown whether it is fraudulent or legitimate; investigative outcomes and legal determinations take weeks or months to conclude. Waiting for ground-truth labels before acting leaves insurance providers vulnerable to delayed payouts on fraudulent claims or backlogged manual reviews.

## Core Concept & Architecture

ClaimGuard addresses this delayed-feedback loop by deploying a real-time ML risk assessment layer at claim ingestion time. 

1. **Immediate Scoring**: As soon as a claim is submitted, an explainable Machine Learning model calculates a **Fraud Risk Score** (0–100%), assigns a **Risk Level** (`Low`, `Medium`, `High`), and provides **Feature-Level Risk Explanations**.
2. **Delayed Label Integration**: Ground-truth labels arriving later (via manual review or delayed investigation) can be attached to existing claims at any time.
3. **Dynamic Model Evaluation**: Model performance metrics (Accuracy, Precision, Recall, F1 Score, ROC-AUC, and Confusion Matrix) are computed on-the-fly using only claims that have received ground-truth labels.

```
┌─────────────────────────────────────────────────────────┐
│              React + Tailwind Dashboard                 │
│  (Submit Claim | Claims Table | Performance | Simulator) │
└────────────────────────────┬────────────────────────────┘
                             │ REST API (JSON)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│   - Claim Ingestion & Persistence                       │
│   - Analytics & Model Evaluation Engine                 │
│   - Seed Data & Simulation Services                     │
└────────────────────────────┬────────────────────────────┘
                             │ Feature Extraction & Inference
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 Scikit-Learn ML Pipeline                │
│   - Baseline Random Forest Classifier                   │
│   - Feature Importance Risk Explanations                │
└─────────────────────────────────────────────────────────┘
```

---

## Key Features

- 📋 **Claim Submission Form**: Submit new claim details (claimant name, amount, type, incident date, days to report, prior claims, police report status, witnesses) and receive instant AI risk scoring.
- 🔍 **Explainable AI**: View feature-level explanations (e.g. high claim amount relative to average, slow reporting, lack of police report/witnesses) that drove the prediction.
- 📊 **Claims Management Dashboard**: Filter, search, and view all claims alongside overall risk breakdown charts (by type and risk level).
- ⏱️ **Delayed Label Simulator**: Generate synthetic historical claims that simulate the arrival of delayed investigation outcomes.
- 📈 **Model Performance Analytics**: Monitor Precision, Recall, F1 Score, ROC-AUC, Accuracy, and an interactive 2×2 Confusion Matrix evaluated on labeled claims.
- 🌱 **Development Seed Command**: Populate the app instantly with 20 realistic test claims across legitimate, fraud, and unlabeled categories using `python -m backend.seed`.

---

## Machine Learning Approach

- **Model Architecture**: `RandomForestClassifier` (scikit-learn) trained on synthetic claim feature distributions.
- **Features Used**:
  - `claim_amount` (numeric float)
  - `claim_type_encoded` (auto, health, property, life)
  - `days_to_report` (delay between incident date and claim filing)
  - `prior_claims_count` (historical claims filed by claimant)
  - `police_report_filed` (boolean indicator)
  - `witnesses` (number of witnesses)
  - `amount_to_avg_ratio` (ratio of claim amount to category average)
- **Explainability**: Combines global feature importances with per-claim feature values to generate human-interpretable risk direction indicators (`↑ Risk` or `↓ Risk`).

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Tailwind CSS 4, Recharts, Lucide Icons, React Router v6, Vite |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic v2 |
| **Database** | PostgreSQL (Neon), SQLAlchemy 2 (sync), psycopg 3 |
| **Machine Learning** | scikit-learn, NumPy, Pandas |
| **Testing** | pytest, FastAPI TestClient |

---

## Project Structure

```text
ClaimGuard/
├── backend/
│   ├── app/
│   │   ├── ml/               # ML dataset generator & RandomForest pipeline
│   │   ├── routes/           # FastAPI endpoints (claims, analytics, seed)
│   │   ├── database.py       # Claim store (SQLAlchemy; Neon PostgreSQL / SQLite for tests)
│   │   ├── orm.py            # SQLAlchemy `claims` table definition
│   │   ├── main.py           # FastAPI application entry point & lifespan
│   │   ├── models.py         # Pydantic schemas
│   │   └── seed.py           # Synthetic seed dataset definition & generator
│   ├── neon_smoke_test.py    # Manual persistence smoke test against Neon
│   ├── requirements.txt      # Python backend dependencies
│   ├── run.py                # Server launcher script
│   └── seed.py               # CLI executable seed command
├── frontend/
│   ├── src/
│   │   ├── api/client.js     # Axios API client
│   │   ├── components/       # UI Components (Dashboard, Form, Table, Detail, etc.)
│   │   ├── utils/helpers.js  # Formatters & color mappings
│   │   ├── App.jsx           # Main router application
│   │   └── index.css         # Tailwind v4 configuration
│   ├── package.json
│   └── vite.config.js        # Vite dev server configuration & API proxy
├── tests/
│   ├── conftest.py           # Forces a throwaway SQLite database for tests
│   ├── test_analytics.py     # Unit tests for analytics & metric edge cases
│   ├── test_persistence.py   # Persistence, delayed-label & labeled-only metric tests
│   └── test_seed.py          # Unit tests for seed generator & performance
├── .env.example              # Template for DATABASE_URL (copy to .env; never commit .env)
├── README.md                 # Project documentation
├── progress.md               # Developer progress & roadmap
└── requirements.txt          # Root Python dependencies
```

---

## Local Setup & Quickstart

### Prerequisites
- **Python 3.12+**
- **Node.js 18+** & `npm`

### 1. Clone & Set Up Environment

```bash
git clone <repository-url>
cd ClaimGuard
```

### 2. Database Setup (Neon PostgreSQL)

Claims are stored in PostgreSQL so delayed ground-truth labels survive backend restarts.

1. Create a free project at [neon.tech](https://neon.tech) and copy its **pooled** connection string.
2. Copy the template and set your own value (`.env` is git-ignored; never commit credentials):

```bash
# Linux/macOS
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

3. Edit `.env` and set `DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require`.

The backend refuses to start if `DATABASE_URL` is missing. The `claims` table is created automatically at startup (`create_all`; there are no migrations yet).

### 3. Backend Setup

```bash
# Create and activate Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend
python backend/run.py
```
*Backend server runs at `http://localhost:8000` (API documentation available at `http://localhost:8000/docs`).*

### 4. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```
*Frontend application runs at `http://localhost:5173`.*

---

## How to Use ClaimGuard

### 1. Seed Demo Data (Recommended First Step)
With the backend server running, execute:
```bash
python -m backend.seed
```
This populates the system with 20 realistic claims (7 legitimate, 7 fraud, and 6 unlabeled).

> ⚠️ **WARNING: seeding deletes ALL existing claims.** `python -m backend.seed`, `POST /api/dev/seed` and `POST /api/seed` run with `clear_existing=True` and are **unauthenticated**. Because claims are now persistent, calling any of them against your Neon database permanently wipes the `claims` table. Use them only on a development/branch database, never on data you want to keep. There is currently no guard or authentication (planned for a later iteration).

### 2. Submit a Claim
Navigate to **Submit Claim** in the sidebar. Fill in claimant info and risk indicators to receive instant real-time risk scoring and feature explanations.

### 3. Review Claims & Apply Delayed Labels
Navigate to **Claims** to view all submitted claims. Click any claim to inspect its details and apply a ground-truth label (`Mark Legitimate` or `Mark as Fraud`).

### 4. Run the Delayed-Label Simulator
Navigate to **Simulator** to bulk-generate historical claims with simulated investigation outcomes.

### 5. View Model Performance
Navigate to **Model Performance** to view live metrics (Accuracy, Precision, Recall, F1 Score, ROC-AUC, Confusion Matrix) calculated dynamically from labeled claims.

---

## Running Tests

Run the test suite using `pytest`:

```bash
$env:PYTHONPATH="backend"; python -m pytest tests/
```

The tests always use a throwaway **SQLite** database (`tests/conftest.py` overrides `DATABASE_URL`, so a Neon URL in `.env` is never touched). To run them against a dedicated PostgreSQL test database instead, set `DATABASE_URL_TEST`; the tests clear the `claims` table, so never point it at real data.

### Neon smoke test (manual)

To verify persistence end to end against your real Neon database, including real backend restarts:

```bash
python backend/neon_smoke_test.py
```

It never seeds or clears the table, and removes only its own `SMOKE-TEST-*` claims when finished. Stop your normal backend first.

---

## Current Limitations

- **Persistent Storage, No Migrations Yet**: Claims (including delayed labels) persist in Neon PostgreSQL. The table is created with `create_all` at startup; schema changes are not migrated (Alembic is planned).
- **Destructive Dev Seed Endpoint**: `POST /api/dev/seed` wipes all claims and has no authentication or guard (see warning above).
- **Baseline Model**: Uses a synthetic dataset and Random Forest baseline rather than a live production database.
- **Static Model Training**: Model is trained on application startup; full online retraining/MLOps retraining is planned for future iterations.

---

## Future Improvements

- [x] Support persistent database storage (Neon PostgreSQL via SQLAlchemy).
- [ ] Add Alembic migrations and guard/authenticate the dev seed endpoint.
- [ ] Implement automated MLOps pipeline with drift detection and periodic model retraining.
- [ ] Add SHAP (Shapley Additive exPlanations) for enhanced local feature explainability.
- [ ] Export claim reports to PDF.
