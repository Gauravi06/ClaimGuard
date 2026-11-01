"""
scripts/snapshot_settled.py
Snapshot settled claims at a specified simulated date and generate DVC tracking metadata.

Usage:
    python scripts/snapshot_settled.py [--as-of YYYY-MM-DD] [--output-dir data/snapshots]
"""

import argparse
import hashlib
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Add backend directory to sys.path so app.pipeline can be imported
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipeline.simulation import get_settled
from app.pipeline.state import state


def compute_md5(file_path: Path) -> str:
    """Calculate the MD5 checksum of a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_dvc_pointer(csv_path: Path) -> Path:
    """Generate a valid DVC pointer file (.dvc) for the generated snapshot."""
    file_size = csv_path.stat().st_size
    md5_hash = compute_md5(csv_path)
    dvc_path = csv_path.with_name(f"{csv_path.name}.dvc")

    content = (
        f"outs:\n"
        f"- md5: {md5_hash}\n"
        f"  size: {file_size}\n"
        f"  hash: md5\n"
        f"  path: {csv_path.name}\n"
    )
    dvc_path.write_text(content, encoding="utf-8")
    return dvc_path


def snapshot_settled(as_of: date, output_dir: Path, filename: str = "settled_claims.csv") -> Path:
    """
    Filter claims settled on or before `as_of`, export to CSV,
    and generate the companion .dvc file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    df = get_settled(as_of)

    if df.empty:
        print(f"[WARN] No settled claims found as of {as_of.isoformat()}.")
    else:
        fraud_count = int(df["is_fraud"].sum()) if "is_fraud" in df.columns else 0
        fraud_rate = (fraud_count / len(df) * 100.0) if len(df) > 0 else 0.0
        print(f"[INFO] Settled claims snapshot as of {as_of.isoformat()}:")
        print(f"       Total rows: {len(df)}")
        print(f"       Fraudulent claims: {fraud_count} ({fraud_rate:.2f}%)")

    # Save target CSV
    csv_path = output_dir / filename
    df.to_csv(csv_path, index=False)
    print(f"[INFO] Saved snapshot to: {csv_path}")

    # Generate companion .dvc file
    dvc_path = write_dvc_pointer(csv_path)
    print(f"[INFO] Generated DVC pointer: {dvc_path}")

    return csv_path


def main():
    parser = argparse.ArgumentParser(description="Snapshot settled claims for DVC versioning.")
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Simulated cutoff date (YYYY-MM-DD). Defaults to current simulation state date or 2015-01-22.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/snapshots",
        help="Output directory for snapshot CSV and .dvc files (default: data/snapshots).",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default="settled_claims.csv",
        help="Output CSV filename (default: settled_claims.csv).",
    )
    args = parser.parse_args()

    if args.as_of:
        as_of_date = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    else:
        # Default to 2015-01-22 (first retrain milestone: 61 settled claims)
        as_of_date = getattr(state, "simulated_date", date(2015, 1, 22))
        if as_of_date <= date(2015, 1, 1):
            as_of_date = date(2015, 1, 22)

    output_path = REPO_ROOT / args.output_dir
    snapshot_settled(as_of=as_of_date, output_dir=output_path, filename=args.filename)


if __name__ == "__main__":
    main()

