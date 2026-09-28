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
│   │   ├── database.py       # In-memory claim store
│   │   ├── main.py           # FastAPI application entry point & lifespan
│   │   ├── models.py         # Pydantic schemas
│   │   └── seed.py           # Synthetic seed dataset definition & generator
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
│   ├── test_analytics.py     # Unit tests for analytics & metric edge cases
│   └── test_seed.py          # Unit tests for seed generator & performance
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

### 2. Backend Setup

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

### 3. Frontend Setup

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

---

## Current Limitations

- **In-Memory Storage**: Claims are stored in-memory for MVP simplicity and reset when the backend process restarts.
- **Baseline Model**: Uses a synthetic dataset and Random Forest baseline rather than a live production database.
- **Static Model Training**: Model is trained on application startup; full online retraining/MLOps retraining is planned for future iterations.

---

## Future Improvements

- [ ] Support persistent database storage (PostgreSQL / SQLite via SQLAlchemy).
- [ ] Implement automated MLOps pipeline with drift detection and periodic model retraining.
- [ ] Add SHAP (Shapley Additive exPlanations) for enhanced local feature explainability.
- [ ] Export claim reports to PDF.
