# ClaimGuard Docker Orchestration Guide

This guide details how to build, run, monitor, and troubleshoot the ClaimGuard multi-container stack with Docker Compose.

---

## 1. Prerequisites

- **Docker Desktop**: Installed and running (ensure the whale icon in the system tray is green/active).
- **WSL 2 Backend (Windows)**: Ensure Docker Desktop is configured to use the WSL 2 engine (*Settings -> General -> Use the WSL 2 based engine*).
- **Sufficient Disk Space & RAM**: At least 8 GB of free RAM and 10 GB of disk space for Docker image layers and cache.

---

## 2. Quick Start

1. Clone the repository and navigate to the project root:
   ```bash
   git clone https://github.com/Gauravi06/ClaimGuard.git
   cd ClaimGuard
   ```

2. (Optional) Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Build and launch all services:
   ```bash
   docker compose up --build -d
   ```

> [!NOTE]
> **Initial Build Time**: The first image build downloads and compiles machine learning packages (including XGBoost, Scikit-Learn, SHAP, and PyArrow) and trains the baseline champion model. This can take **10–15 minutes** depending on your internet connection. Subsequent builds are cached and take under 30 seconds.

---

## 3. Service Endpoints & URLs

| Service | Host URL | Description | Default Credentials |
|---|---|---|---|
| **Web Frontend** | [http://localhost:3000](http://localhost:3000) | React SPA served via Nginx with reverse proxy to backend | None |
| **Backend API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | FastAPI interactive Swagger documentation | None |
| **Backend Raw Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Prometheus exposition format metrics | None |
| **MLflow UI** | [http://localhost:5000](http://localhost:5000) | Experiment tracking server and artifact viewer | None |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Metric scraper and time-series database (`targets` at `/targets`) | None |
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Operational dashboards and telemetry visualization | `admin` / `admin` (or configured in `.env`) |

> [!TIP]
> **MLflow View Toggle**: When opening MLflow at [http://localhost:5000](http://localhost:5000), switch the top toggle from **GenAI** to **Model training**, click **Experiments**, and select `ClaimGuard_Simulation` to view training runs with `pr_auc`, `precision`, and promotion status.

---

## 4. Interactive Simulation Demo Walkthrough

### Step 1: Baseline Inspection
1. Open the **Simulation** dashboard at [http://localhost:3000/simulation](http://localhost:3000/simulation).
2. The initial clock displays `2015-01-01`, model version is `0` ("no model yet"), and settled claims count is `0`.

### Step 2: First Model Training (3 Advances)
1. Click **Advance 7 Days** 3 times:
   - **Advance 1 (`2015-01-08`)**: 0 claims settled, clock moves forward.
   - **Advance 2 (`2015-01-15`)**: 8 claims settled, backlog accumulates.
   - **Advance 3 (`2015-01-22`)**: 61 claims settled (exceeds the 25-settled retrain threshold). The pipeline trains candidate models and promotes **Model v1** (`best_model: XGBoost`, holdout `PR-AUC ~0.5769`).
2. Refresh the MLflow UI at [http://localhost:5000](http://localhost:5000) to see run `retrain_v1_2015-01-22`.

### Step 3: Model Governance & Promotion Gap (2 More Advances)
1. Click **Advance 7 Days** 2 additional times:
   - **Advance 4 (`2015-01-29`)**: 106 newly settled claims. Champion PR-AUC evaluated on time-based holdout is 0.2095; candidate achieves 0.6451. **Promoted to Model v2**.
   - **Advance 5 (`2015-02-05`)**: 107 newly settled claims. Candidate achieves PR-AUC 0.5518, but champion holdout PR-AUC is 0.6164. Candidate is **rejected (unpromoted)**.
2. Open Grafana at [http://localhost:3001](http://localhost:3001) (*ClaimGuard Delayed-Label Monitor*):
   - **Model Version**: `2`
   - **Retrains Total**: `3`
   - **Settled Claims**: `274`
   - **Pending Backlog**: `341`
   - **Retrains vs Promotions Panel**: The gap between Retrains Total (`3`) and Model Version (`2`) visually demonstrates model governance rejecting an underperforming model.

> [!IMPORTANT]
> **Backlog Threshold**: The backlog panel in Grafana displays a horizontal red indicator line at `300` claims. This is a visual UI threshold to monitor delayed-settlement queue pressure, not an external notification alert.

---

## 5. Container Lifecycle & Data Persistence

### Stopping Containers
To stop the running services:
```bash
docker compose down
```
This gracefully terminates containers while preserving persistent volumes (`claimguard_mlruns_data` and `claimguard_claims_data`).

> [!CAUTION]
> **Do NOT run `docker compose down -v`** during normal operations. Adding the `-v` flag removes named Docker volumes and irreversibly deletes all historical MLflow runs and SQLite claims data. Use `-v` only when explicitly performing a clean factory reset before a fresh demo.

### Clock Memory Model
The simulation clock and in-memory state tracker reside in the backend application memory. If the backend container restarts (`docker compose restart backend`), the clock resets to `2015-01-01`. However, MLflow run history stored in `/mlruns` remains intact on the persistent volume.

---

## 6. Windows Troubleshooting

### 1. Docker Desktop Not Running
- **Symptom**: `error during connect: This error may indicate that the docker daemon is not running.`
- **Fix**: Launch Docker Desktop from the Start menu. Verify that WSL 2 is installed and running (`wsl --status`).

### 2. Port Already In Use
- **Symptom**: `Bind for 0.0.0.0:3000 failed: port is already allocated.`
- **Fix**: Check what process is occupying the port (`netstat -ano | findstr :3000`). Alternatively, override the host port in `.env`:
  ```env
  FRONTEND_PORT=3002
  BACKEND_PORT=8002
  GRAFANA_PORT=3003
  ```

### 3. Slow Initial Build
- **Symptom**: Build appears paused at wheel installations.
- **Fix**: The backend image downloads full wheels for PyData and machine learning frameworks (~400 MB). Docker is actively downloading; do not terminate the process.
