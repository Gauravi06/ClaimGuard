"""Manual smoke test: verify ClaimGuard persistence against a real Neon database.

    python backend/neon_smoke_test.py

Reads DATABASE_URL from your environment or the git-ignored .env at the repo root.
It NEVER calls the seed endpoint and NEVER clears the table. It creates two claims
named SMOKE-TEST-<timestamp>-C / -U, checks them across real backend restarts, and
finally deletes only rows whose name starts with SMOKE-TEST- (so your real metrics
are not polluted). Checks are relative to a baseline, so existing data is fine.

Stop your normal backend and avoid using the app while this runs.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--allow-sqlite", action="store_true", help="developer dry-run only; skips PostgreSQL checks")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = f"http://127.0.0.1:{args.port}"
MARK = "SMOKE-TEST-"
DESC = "neon smoke test"

try:
    from sqlalchemy import delete, func, inspect, select, text

    from app.database import engine, init_db, SessionLocal
    from app.orm import ClaimRow
except RuntimeError as e:  # DATABASE_URL missing
    print(f"[ABORT] {e}")
    sys.exit(2)

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n         {detail}" if detail else ""))


def http(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


_logs = []
_proc = None
_wrote = False  # set once we are about to write; cleanup only runs after that


def start_backend():
    global _proc
    log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    _logs.append(log.name)
    _proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(args.port)],
        cwd=HERE, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT,
    )
    for _ in range(300):  # up to ~60s: Neon cold start + model training
        if _proc.poll() is not None:
            break
        try:
            http("GET", "/")
            return
        except Exception:
            time.sleep(0.2)
    stop_backend()
    print(open(log.name).read()[-1500:])
    raise RuntimeError("backend did not start (see log above)")


def stop_backend():
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None


def restart_backend():
    stop_backend()
    start_backend()


def perf():
    return http("GET", "/api/analytics/model-performance")


def metrics_only(p):
    return {k: v for k, v in p.items() if k != "total_predictions"}


def row_count():
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(ClaimRow))


def payload(name, **kw):
    d = dict(claimant_name=name, claim_amount=30000.0, claim_type="auto", incident_date="2026-09-01",
             days_to_report=40, description=DESC, prior_claims_count=4, police_report_filed=False, witnesses=0)
    d.update(kw)
    return d


def main():
    is_pg = engine.dialect.name == "postgresql"
    if not is_pg and not args.allow_sqlite:
        print(f"[ABORT] DATABASE_URL points at '{engine.dialect.name}', not PostgreSQL/Neon. "
              "Set your Neon URL in .env (see .env.example).")
        sys.exit(2)

    run_id = f"{MARK}{int(time.time())}"
    same4 = ("fraud_score", "prediction", "risk_level", "explanations")

    # 1. connection + table creation (host/db only; never prints credentials)
    u = engine.url
    print(f"Target: {engine.dialect.name} host={u.host} database={u.database}\n")
    try:
        with engine.connect() as c:
            info = c.execute(text("select version()")).scalar() if is_pg else "sqlite"
        check("connected to database", True, str(info)[:80])
    except Exception as e:
        check("connected to database", False, f"{type(e).__name__}: {str(e)[:300]}")
        return
    existed = inspect(engine).has_table("claims")
    init_db()
    check("table 'claims' exists after create_all", inspect(engine).has_table("claims"),
          "already existed" if existed else "created now")
    global _wrote
    _wrote = True
    baseline = row_count()
    print(f"         existing rows in claims: {baseline} (left untouched)\n")

    # 2. first backend run
    start_backend()
    p0 = perf()
    c0 = http("POST", "/api/claims", payload(f"{run_id}-C"))
    u0 = http("POST", "/api/claims", payload(f"{run_id}-U", claim_amount=800.0, days_to_report=1,
                                             prior_claims_count=0, police_report_filed=True, witnesses=3))
    check("claims created unlabeled (true_label = null, status pending)",
          c0["true_label"] is None and u0["true_label"] is None and c0["status"] == "pending")
    check("claim retrieved by id equals the create response", http("GET", f"/api/claims/{c0['id']}") == c0,
          f"score={c0['fraud_score']:.4f} prediction={c0['prediction']} risk={c0['risk_level']} "
          f"explanations={len(c0['explanations'])}")
    p1 = perf()
    check("unlabeled claims do NOT affect metrics (only total_predictions +2)",
          metrics_only(p1) == metrics_only(p0) and p1["total_predictions"] == p0["total_predictions"] + 2,
          f"labeled {p0['total_labeled']}->{p1['total_labeled']}, predictions "
          f"{p0['total_predictions']}->{p1['total_predictions']}")

    # 3. restart #1
    restart_backend()
    c1, u1 = http("GET", f"/api/claims/{c0['id']}"), http("GET", f"/api/claims/{u0['id']}")
    check("after restart #1: claims identical to originals (all fields)", c1 == c0 and u1 == u0)
    check("after restart #1: score/prediction/risk/explanations unchanged",
          all(c1[k] == c0[k] for k in same4), f"score {c0['fraud_score']} == {c1['fraud_score']}")

    # 4. delayed label
    lab = http("PATCH", f"/api/claims/{c0['id']}/label", {"true_label": True})
    check("delayed label applied; original prediction fields unchanged",
          lab["true_label"] is True and all(lab[k] == c0[k] for k in same4))
    p2 = perf()
    cell = "tp" if c0["prediction"] else "fn"  # label is True
    delta = {k: p2["confusion_matrix"][k] - p0["confusion_matrix"][k] for k in p2["confusion_matrix"]}
    check("Model Performance now includes the labeled claim (and only it)",
          p2["total_labeled"] == p0["total_labeled"] + 1 and p2["total_predictions"] == p0["total_predictions"] + 2
          and delta == {k: (1 if k == cell else 0) for k in delta},
          f"labeled {p0['total_labeled']}->{p2['total_labeled']}, confusion delta {delta} (expected +1 {cell})")

    # 5. restart #2
    restart_backend()
    c2, u2 = http("GET", f"/api/claims/{c0['id']}"), http("GET", f"/api/claims/{u0['id']}")
    check("after restart #2: label persisted, unlabeled claim still unlabeled",
          c2["true_label"] is True and u2["true_label"] is None)
    check("after restart #2: prediction fields still unchanged", all(c2[k] == c0[k] for k in same4))
    check("after restart #2: Model Performance identical to before restart", perf() == p2)

    # 6. PostgreSQL-specific column types
    if is_pg:
        with engine.connect() as c:
            row = c.execute(text(
                "select pg_typeof(id)::text, pg_typeof(explanations)::text, pg_typeof(submission_date)::text, "
                "pg_typeof(fraud_score)::text, pg_typeof(true_label)::text from claims where claimant_name = :n"),
                {"n": f"{run_id}-C"}).one()
        check("PostgreSQL column types (uuid, jsonb, timestamptz, double precision, boolean)",
              tuple(row) == ("uuid", "jsonb", "timestamp with time zone", "double precision", "boolean"), str(tuple(row)))


try:
    main()
except Exception as e:
    check("smoke test ran to completion", False, f"{type(e).__name__}: {str(e)[:400]}")
finally:
    stop_backend()
    try:  # remove ONLY this test's rows (never the whole table)
        if not _wrote:
            raise SystemExit
        with SessionLocal() as s:
            removed = s.execute(delete(ClaimRow).where(ClaimRow.claimant_name.like(f"{MARK}%"),
                                                       ClaimRow.description == DESC)).rowcount
            s.commit()
        print(f"\nCleanup: removed {removed} SMOKE-TEST claim(s); {row_count()} row(s) remain in claims")
    except SystemExit:
        pass  # aborted before writing anything: nothing to clean up
    except Exception as e:
        print(f"\n[WARN] cleanup failed: {e}. Delete rows where claimant_name LIKE 'SMOKE-TEST-%' manually.")
    for f in _logs:
        try:
            os.remove(f)
        except OSError:
            pass

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("FAILED: " + "; ".join(failed))
    sys.exit(1)
print("ALL CHECKS PASSED")
