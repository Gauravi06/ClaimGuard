# Data Version Control (DVC) Architecture & Workflow

## 1. Overview & Motivation

In production insurance fraud detection, **ground-truth fraud labels arrive with variable, long delays** (adjuster interviews, field inspections, and litigation taking 10 to 30+ days). Consequently, the training cohort grows dynamically across simulation time:
- At Day 21: 61 claims have settled.
- At Day 28: 167 claims have settled.
- At Day 60: 420 claims have settled.

Without data versioning, reproducing a model trained at a past timestamp is difficult because the database state has shifted. **Data Version Control (DVC)** solves this by decoupling large data files from Git while preserving cryptographic hashes in small, version-controlled `.dvc` pointer files.

---

## 2. Settled Claims Snapshotting (`scripts/snapshot_settled.py`)

ClaimGuard provides a dedicated CLI utility to snapshot the exact cohort of settled claims available as of any simulated cutoff date:

```bash
python scripts/snapshot_settled.py --as-of 2015-01-22 --output-dir data/snapshots
```

### Script Execution Flow
1. Imports `get_settled(as_of)` from `app.pipeline.simulation`.
2. Filters claims where `label_available_at <= as_of`.
3. Exports the settled cohort with true labels (`is_fraud`) to `data/snapshots/settled_claims.csv`.
4. Computes the cryptographic MD5 hash and file size.
5. Emits the companion DVC tracking file `data/snapshots/settled_claims.csv.dvc`.

---

## 3. DVC Tracking Files in ClaimGuard

The repository includes pre-configured DVC pointers for key datasets:

| Dataset Pointer | Target File | MD5 Hash | Records / Size | Purpose |
|---|---|---|---|---|
| `data/raw/carclaims.csv.dvc` | `data/raw/carclaims.csv` | `6a5b26864361444b9c714f0523911a26` | 3.69 MB (15,420 rows) | Raw historical automobile claims |
| `data/processed/carclaims_processed.csv.dvc` | `data/processed/carclaims_processed.csv` | `85f75b29961fac057a90fa1bac4519b0` | 1.08 MB (14 features) | Processed feature matrix for XGBoost champion |
| `backend/data/claims_sim.csv.dvc` | `backend/data/claims_sim.csv` | `c89b083c898bad9c37ac62c3781c0a37` | 88.9 KB (1,000 rows) | Chronological replay simulation pool |
| `data/snapshots/settled_claims.csv.dvc` | `data/snapshots/settled_claims.csv` | Dynamic | Cohort snapshot | Settled claims training cohort at retrain time |

### Pointer File Schema (`.dvc`)
```yaml
outs:
- md5: 85f75b29961fac057a90fa1bac4519b0
  size: 1082864
  hash: md5
  path: carclaims_processed.csv
```

---

## 4. DVC Remote Storage & CLI Commands

### Configuration (`.dvc/config`)
```ini
[core]
    analytics = false
    remote = localstorage
['remote "localstorage"']
    url = /tmp/dvc-storage
```

To configure cloud storage (e.g., AWS S3 or Google Cloud Storage):
```bash
dvc remote add -d s3remote s3://my-claimguard-dvc-bucket/storage
dvc remote modify s3remote region us-east-1
```

### Daily Operations Workflow

1. **Snapshot new training data**:
   ```bash
   python scripts/snapshot_settled.py --as-of 2015-02-01
   ```

2. **Track with DVC**:
   ```bash
   dvc add data/snapshots/settled_claims.csv
   ```
   *(Adds `settled_claims.csv` to `.gitignore` and creates/updates `settled_claims.csv.dvc`)*.

3. **Commit pointers to Git**:
   ```bash
   git add data/snapshots/settled_claims.csv.dvc data/snapshots/.gitignore
   git commit -m "chore(dvc): snapshot settled claims cohort as of 2015-02-01"
   ```

4. **Push data artifacts to remote**:
   ```bash
   dvc push
   ```

5. **Pull data on a clean clone / CI runner**:
   ```bash
   git checkout <commit-hash>
   dvc pull
   ```

---

## 5. Integration with MLflow & Retraining

When `app.pipeline.training.train_and_log(as_of)` executes:
1. `snapshot_settled.py` can be triggered to freeze the training cohort.
2. The snapshot's MD5 checksum is logged as an MLflow run tag:
   ```python
   mlflow.set_tag("dvc.dataset_md5", compute_md5(snapshot_path))
   mlflow.set_tag("dvc.snapshot_date", as_of.isoformat())
   ```
3. This creates a bidirectional link: **MLflow Run $\longleftrightarrow$ DVC Snapshot $\longleftrightarrow$ Git Commit**, enabling exact point-in-time auditability.

