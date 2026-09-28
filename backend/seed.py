import json
import urllib.request
import urllib.error
import sys
import os

# Add parent directory to sys.path to allow imports if run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_seed():
    server_url = "http://localhost:8000/api/dev/seed"
    print("=" * 55)
    print("  ClaimGuard Seed Data Generator (Development)")
    print("=" * 55)

    # Try seeding via HTTP to running FastAPI server first
    try:
        req = urllib.request.Request(server_url, method="POST", data=b"{}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status in (200, 201):
                data = json.loads(response.read().decode("utf-8"))
                total = len(data)
                fraud_count = sum(1 for c in data if c.get("true_label") is True)
                legit_count = sum(1 for c in data if c.get("true_label") is False)
                unlabeled_count = sum(1 for c in data if c.get("true_label") is None)

                print(f"[+] Connected to active ClaimGuard server at http://localhost:8000")
                print(f"[+] Successfully seeded {total} realistic claims:")
                print(f"    - Legitimate claims: {legit_count}")
                print(f"    - Fraud claims:      {fraud_count}")
                print(f"    - Unlabeled claims:  {unlabeled_count}")
                print("\n-> Dashboard, Claims Table, and Model Performance pages are ready!")
                print("=" * 55)
                return
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError):
        pass

    # Fallback to direct Python memory execution if server is offline
    try:
        from app.seed import seed_database
        claims = seed_database(clear_existing=True)
        total = len(claims)
        fraud_count = sum(1 for c in claims if c.true_label is True)
        legit_count = sum(1 for c in claims if c.true_label is False)
        unlabeled_count = sum(1 for c in claims if c.true_label is None)

        print(f"[+] Seeded {total} claims in-memory:")
        print(f"    - Legitimate claims: {legit_count}")
        print(f"    - Fraud claims:      {fraud_count}")
        print(f"    - Unlabeled claims:  {unlabeled_count}")
        print("\nNOTE: FastAPI server is not currently running at http://localhost:8000.")
        print("To seed the live web app, start the backend ('python run.py') and re-run this command.")
        print("=" * 55)
    except Exception as e:
        print(f"[!] Error seeding database: {e}")
        print("=" * 55)
        sys.exit(1)

if __name__ == "__main__":
    run_seed()
