#!/usr/bin/env python3
"""
scripts/smoke_test.py
End-to-end smoke test for ClaimGuard Docker Compose deployment.
Verifies backend API, clock advancement, Prometheus scraping,
Grafana dashboard provisioning, and MLflow run logging.
Uses only the standard library and the `requests` library.
"""
import os
import sys
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001").rstrip("/")
MLFLOW_URL = os.getenv("MLFLOW_URL", "http://localhost:5000").rstrip("/")

GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")


def run_checks() -> bool:
    all_passed = True

    # 1. Root API check
    try:
        resp = requests.get(f"{BACKEND_URL}/", timeout=10)
        if resp.status_code == 200:
            print("[PASS] 1. GET / returns HTTP 200")
        else:
            print(f"[FAIL] 1. GET / returned HTTP {resp.status_code}")
            all_passed = False
    except Exception as exc:
        print(f"[FAIL] 1. GET / connection error: {exc}")
        return False

    # 2. Clock initial check
    try:
        resp = requests.get(f"{BACKEND_URL}/api/sim/clock", timeout=10)
        if resp.status_code != 200:
            print(f"[FAIL] 2. GET /api/sim/clock returned HTTP {resp.status_code}")
            return False

        clock_data = resp.json()
        sim_date = clock_data.get("simulated_date")
        if sim_date != "2015-01-01":
            print(
                f"\n[FAIL] 2. Clock is at {sim_date!r}, expected '2015-01-01' for smoke test.\n"
                f"       Please run 'docker compose restart backend' first to reset the simulation clock, then rerun."
            )
            sys.exit(1)
        print(f"[PASS] 2. GET /api/sim/clock verified at initial date '{sim_date}'")
    except Exception as exc:
        print(f"[FAIL] 2. GET /api/sim/clock error: {exc}")
        return False

    # 3. Three POST /api/sim/advance calls
    try:
        advance_payload = {"days": 7}
        advance_3_data = None
        for step in (1, 2, 3):
            adv_resp = requests.post(
                f"{BACKEND_URL}/api/sim/advance",
                json=advance_payload,
                timeout=30,
            )
            if adv_resp.status_code != 200:
                print(f"[FAIL] 3. Advance step {step} returned HTTP {adv_resp.status_code}: {adv_resp.text}")
                all_passed = False
                break
            if step == 3:
                advance_3_data = adv_resp.json()

        if advance_3_data:
            retrained = advance_3_data.get("retrained")
            model_version = advance_3_data.get("model_version")
            if retrained is True and model_version == 1:
                print(
                    f"[PASS] 3. Three advances successful: retrained={retrained}, "
                    f"model_version={model_version}, as_of='{advance_3_data.get('simulated_date')}'"
                )
            else:
                print(
                    f"[FAIL] 3. Advance 3 assertion failed: expected retrained=True, model_version=1; "
                    f"got retrained={retrained}, model_version={model_version}"
                )
                all_passed = False
    except Exception as exc:
        print(f"[FAIL] 3. Advance calls failed with exception: {exc}")
        all_passed = False

    # 4. GET /metrics check
    try:
        resp = requests.get(f"{BACKEND_URL}/metrics", timeout=10)
        if resp.status_code == 200 and "claimguard_model_version" in resp.text:
            print("[PASS] 4. GET /metrics contains 'claimguard_model_version'")
        else:
            print(f"[FAIL] 4. GET /metrics returned HTTP {resp.status_code} or missing claimguard_model_version")
            all_passed = False
    except Exception as exc:
        print(f"[FAIL] 4. GET /metrics error: {exc}")
        all_passed = False

    # 5. Prometheus target health check
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            active_targets = data.get("activeTargets", [])
            claimguard_up = any(
                t.get("labels", {}).get("job") == "claimguard" and t.get("health") == "up"
                for t in active_targets
            )
            if claimguard_up:
                print("[PASS] 5. Prometheus target 'claimguard' is UP")
            else:
                print(f"[FAIL] 5. Prometheus target 'claimguard' is not UP. Targets: {active_targets}")
                all_passed = False
        else:
            print(f"[FAIL] 5. GET {PROMETHEUS_URL}/api/v1/targets returned HTTP {resp.status_code}")
            all_passed = False
    except Exception as exc:
        print(f"[FAIL] 5. Prometheus target check error: {exc}")
        all_passed = False

    # 6. Grafana health check
    try:
        resp = requests.get(f"{GRAFANA_URL}/api/health", timeout=10)
        if resp.status_code == 200 and resp.json().get("database") == "ok":
            print("[PASS] 6. Grafana /api/health is ok")
        else:
            print(f"[FAIL] 6. Grafana /api/health returned HTTP {resp.status_code}: {resp.text}")
            all_passed = False
    except Exception as exc:
        print(f"[FAIL] 6. Grafana health error: {exc}")
        all_passed = False

    # 7. Grafana dashboard provisioning check
    try:
        dashboard_url = f"{GRAFANA_URL}/api/dashboards/uid/claimguard-delayed-label-monitor"
        resp = requests.get(
            dashboard_url,
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
            timeout=10,
        )
        if resp.status_code == 200:
            dash = resp.json().get("dashboard", {})
            title = dash.get("title", "")
            print(f"[PASS] 7. Grafana dashboard exists: '{title}' (UID: claimguard-delayed-label-monitor)")
        else:
            print(f"[FAIL] 7. Grafana dashboard lookup returned HTTP {resp.status_code}: {resp.text}")
            all_passed = False
    except Exception as exc:
        print(f"[FAIL] 7. Grafana dashboard error: {exc}")
        all_passed = False

    # 8. MLflow runs search check
    try:
        # Search all active experiments to locate run records
        exp_resp = requests.get(f"{MLFLOW_URL}/api/2.0/mlflow/experiments/search?max_results=100", timeout=10)
        if exp_resp.status_code != 200:
            print(f"[FAIL] 8. MLflow experiments/search returned HTTP {exp_resp.status_code}")
            all_passed = False
        else:
            exps = exp_resp.json().get("experiments", [])
            exp_ids = [e["experiment_id"] for e in exps]
            runs_resp = requests.post(
                f"{MLFLOW_URL}/api/2.0/mlflow/runs/search",
                json={"experiment_ids": exp_ids},
                timeout=10,
            )
            if runs_resp.status_code == 200:
                runs = runs_resp.json().get("runs", [])
                if len(runs) >= 1:
                    print(f"[PASS] 8. MLflow runs/search verified ({len(runs)} run(s) found)")
                else:
                    print("[FAIL] 8. MLflow runs/search returned 0 runs")
                    all_passed = False
            else:
                print(f"[FAIL] 8. MLflow runs/search returned HTTP {runs_resp.status_code}: {runs_resp.text}")
                all_passed = False
    except Exception as exc:
        print(f"[FAIL] 8. MLflow runs check error: {exc}")
        all_passed = False

    return all_passed


if __name__ == "__main__":
    success = run_checks()
    if success:
        print("\nAll ClaimGuard Docker smoke tests PASSED successfully.")
        sys.exit(0)
    else:
        print("\nClaimGuard Docker smoke test FAILED.")
        sys.exit(1)
