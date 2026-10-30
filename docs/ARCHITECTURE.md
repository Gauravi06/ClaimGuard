# ClaimGuard Architecture & System Design

This document details the architectural layout, simulation demo lifecycle, and core design decisions of ClaimGuard.

---

## 1. System Architecture Flowchart

```mermaid
flowchart TD
    classDef planned stroke-dasharray: 5 5;

    subgraph Storage ["Storage & Data Sources"]
        CarClaimsData["carclaims data<br/>data/raw/carclaims.csv<br/>data/processed/carclaims_processed.csv"]
        SimClaimsCSV["claims_sim.csv<br/>backend/data/claims_sim.csv"]
        AppDatabase[("Application DB<br/>Neon PostgreSQL / SQLite")]
    end

    subgraph ProdScoring ["Production Scoring Service"]
        ScoringAPI["Scoring API<br/>POST /api/claims<br/>POST /api/claims/predict"]
        XGBChampion["XGBoost Champion Model<br/>data/models/xgb_champion.joblib"]
        GiniExplain["Tree Feature Explanations<br/>Gain/Gini-based"]
        SHAPExplain["SHAP Explanations<br/>backend/app/ml/"]
    end

    subgraph SimPipeline ["Simulation & Retraining Pipeline"]
        SimClock["Simulated Clock<br/>GET /api/sim/clock<br/>POST /api/sim/advance"]
        StateHolder["Simulation State<br/>backend/app/pipeline/state.py"]
        SplitLogic["Settled / Pending Split<br/>get_settled() / get_pending()"]
        RetrainTrigger{"Retrain Trigger<br/>settled >= 25"}
        TrainPipeline["Model Retraining<br/>train_and_log()<br/>(RF vs LR candidates)"]
        PromotionRule["Candidate Promotion Rule<br/>XGBoost Candidate & Threshold"]
        MLflowTracking["MLflow Tracking<br/>backend/app/pipeline/tracking.py<br/>mlruns/"]
    end

    subgraph Observability ["Observability & Deployment"]
        MetricsRoute["Metrics Exposition<br/>GET /metrics"]
        PrometheusServer["Prometheus Server<br/>monitoring/prometheus.yml"]
        GrafanaDash["Grafana Dashboards<br/>monitoring/grafana/"]
        DockerCompose["Docker Compose<br/>docker-compose.yml"]
    end

    subgraph FrontendUI ["User Interface"]
        ReactDashboard["React Dashboards<br/>frontend/src/"]
    end

    CarClaimsData --> XGBChampion
    XGBChampion --> ScoringAPI
    ScoringAPI --> GiniExplain
    ScoringAPI -.-> SHAPExplain
    ScoringAPI --> AppDatabase

    SimClaimsCSV --> SplitLogic
    ReactDashboard --> SimClock
    ReactDashboard --> ScoringAPI
    SimClock --> StateHolder
    StateHolder --> SplitLogic
    SplitLogic --> RetrainTrigger
    RetrainTrigger -->|Yes| TrainPipeline
    TrainPipeline -.-> PromotionRule
    TrainPipeline --> MLflowTracking
    StateHolder --> MetricsRoute
    MetricsRoute -.-> PrometheusServer
    PrometheusServer -.-> GrafanaDash

    DockerCompose -.-> ProdScoring
    DockerCompose -.-> SimPipeline
    DockerCompose -.-> Observability
    DockerCompose -.-> FrontendUI

    class SHAPExplain,PromotionRule,PrometheusServer,GrafanaDash,DockerCompose planned;
```

**Legend**: Solid boxes = built components; Dashed boxes = designed only (planned).

---

## 2. Simulation Demo Sequence Diagram

The following sequence diagram outlines the end-to-end execution flow during a simulation clock advance: advancing the clock, settling claims past their investigation window, triggering model retraining at threshold, logging runs to MLflow, and exposing metrics for monitoring.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / React Dashboard
    participant SimRoute as sim.py (POST /api/sim/advance)
    participant State as state.py (SimulationState.advance)
    participant SimData as simulation.py (get_settled / get_pending)
    participant Trigger as trigger.py (MIN_SETTLED = 25)
    participant Train as training.py (train_and_log)
    participant Promo as Candidate Promotion Rule [planned]
    participant Track as tracking.py (log_training_run / MLflow)
    participant Metrics as metrics.py (GET /metrics)
    participant Prom as Prometheus Server [planned]
    participant Graf as Grafana Dashboard [planned]

    User->>SimRoute: POST /api/sim/advance {"days": 7}
    SimRoute->>State: advance(days=7)
    State->>State: advance_date(days=7)
    State->>SimData: get_settled(as_of)
    SimData-->>State: settled_df (label_available_at <= as_of)
    State->>Trigger: Check settled_count >= 25 and (model_version == 0 or newly_settled >= 25)
    alt Retrain Trigger Fires (settled >= 25)
        State->>Train: train_and_log(as_of)
        Train->>Train: Train RF & LR candidates on settled_df
        Train-->>Promo: Compare candidates & evaluate promotion rule [planned]
        Train->>Track: log_training_run(model_version, metrics, best_model)
        Track-->>Train: run_id
        Train-->>State: {"run_id", "model_version", "metrics"}
        State->>State: model_version += 1, update latest_metrics
    else No Retrain
        State->>State: Maintain existing model_version
    end
    State-->>SimRoute: {"simulated_date", "newly_settled", "retrained", "model_version"}
    SimRoute-->>User: 200 OK Response

    Note over User,Graf: Monitoring & Telemetry Scraping Loop
    User->>Metrics: GET /metrics
    Metrics->>State: get_prometheus_metrics()
    State-->>Metrics: Gauges & counters (claimguard_model_version, claimguard_settled_claims, etc.)
    Metrics-->>User: Prometheus Exposition Text
    Prom->>Metrics: Scrape /metrics [planned]
    Metrics-->>Prom: Exposition metric samples [planned]
    Graf->>Prom: Query PromQL metrics [planned]
    Prom-->>Graf: Render dashboard charts [planned]
```

---

## 3. Design Decisions

### Why Simulated Delays
In real-world automobile insurance, fraud ground-truth is never known at the initial moment of filing; claims require an investigation window before an adjuster confirms or denies fraud. As defined in `backend/app/pipeline/prepare_data.py` (lines 79–82) and `docs/CONTRACT.md` (line 12), ClaimGuard simulates an investigation duration of 10 to 30 days (`label_available_at = filed_at + investigation_days`). This prevents target label leakage by ensuring pending claims strictly conceal `is_fraud`, `investigation_days`, and `label_available_at` while under active review.

### Why No Model Before 25 Settled Claims
As declared in `backend/app/pipeline/state.py` (lines 20, 103–105) and `docs/CONTRACT.md` (line 13), `MIN_SETTLED = 25` acts as an absolute guardrail before the initial retrain. Fitting models on fewer than 25 settled claims risks degenerate training folds where positive fraud instances are completely absent during validation splits (`_split_settled_data` in `backend/app/pipeline/training.py`). Waiting for at least 25 settled claims establishes the minimal statistical support required to train and cross-evaluate baseline estimators reliably.

### Why PR-AUC
Automobile insurance fraud is inherently class-imbalanced, with fraudulent claims representing a small fraction of total submissions. As implemented in `backend/app/pipeline/training.py` (lines 141, 147, 150) and required by `docs/CONTRACT.md` (line 21), model selection relies on Precision-Recall AUC (`average_precision_score`). Unlike ROC-AUC, which can appear artificially optimistic due to large counts of true negatives, PR-AUC focuses specifically on precision and recall over the minority fraud class.

### Why Two Separate Parts of the System
The production scoring application (`backend/app/routes/claims.py`, `backend/app/ml/pipeline.py`) provides fast synchronous inference backed by a pre-trained XGBoost champion (`data/models/xgb_champion.joblib`) evaluated across 14 processed features (`data/processed/carclaims_processed.csv`). Conversely, the simulation pipeline (`backend/app/routes/sim.py`, `backend/app/pipeline/`) models temporal dynamics, delayed ground-truth arrival, and periodic retraining on 13 simulation features (`backend/data/claims_sim.csv`). Isolating the simulation pipeline prevents synthetic clock manipulations and batch retraining runs from interfering with or corrupting real-time transactional scoring data.
