"""Persistent claim store (SQLAlchemy sync).

Production uses Neon PostgreSQL via the ``DATABASE_URL`` environment variable
(loaded from a git-ignored ``.env`` at the repo root if present). The automated
tests point ``DATABASE_URL`` at SQLite. The public ``db`` API is unchanged:
add / get / get_all / update_label, plus clear / add_many / get_labeled / count.
"""
import os
from datetime import timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Claim
from app.orm import Base, ClaimRow

# Real environment variables always win over .env (override=False).
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _normalize_url(url: str) -> str:
    # Neon hands out "postgresql://..."; force the psycopg (v3) driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and set it to your "
        "Neon PostgreSQL connection string."
    )

_url = _normalize_url(DATABASE_URL)
if _url.startswith("sqlite"):
    # FastAPI runs sync routes in a threadpool.
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping / pool_recycle: Neon suspends idle compute and drops connections.
    engine = create_engine(_url, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create the claims table if it does not exist (no migrations yet)."""
    Base.metadata.create_all(engine)


def _to_row(claim: Claim) -> ClaimRow:
    return ClaimRow(
        id=claim.id,
        claimant_name=claim.claimant_name,
        claim_amount=claim.claim_amount,
        claim_type=claim.claim_type,
        incident_date=claim.incident_date,
        days_to_report=claim.days_to_report,
        description=claim.description,
        prior_claims_count=claim.prior_claims_count,
        police_report_filed=claim.police_report_filed,
        witnesses=claim.witnesses,
        fraud_score=claim.fraud_score,
        risk_level=claim.risk_level,
        explanations=[e.model_dump() for e in claim.explanations],
        prediction=claim.prediction,
        status=claim.status,
        submission_date=claim.submission_date,
        true_label=claim.true_label,
    )


def _to_claim(row: ClaimRow) -> Claim:
    submitted = row.submission_date
    if submitted.tzinfo is None:  # SQLite drops tzinfo; values are always stored as UTC
        submitted = submitted.replace(tzinfo=timezone.utc)
    return Claim(
        id=row.id,
        claimant_name=row.claimant_name,
        claim_amount=row.claim_amount,
        claim_type=row.claim_type,
        incident_date=row.incident_date,
        days_to_report=row.days_to_report,
        description=row.description,
        prior_claims_count=row.prior_claims_count,
        police_report_filed=row.police_report_filed,
        witnesses=row.witnesses,
        fraud_score=row.fraud_score,
        risk_level=row.risk_level,
        explanations=row.explanations,
        prediction=row.prediction,
        status=row.status,
        submission_date=submitted,
        true_label=row.true_label,
    )


_NEWEST_FIRST = (ClaimRow.submission_date.desc(), ClaimRow.id)


class ClaimStore:
    def add(self, claim: Claim) -> Claim:
        with SessionLocal() as session:
            session.add(_to_row(claim))
            session.commit()
        return claim

    def add_many(self, claims: List[Claim]) -> List[Claim]:
        with SessionLocal() as session:
            session.add_all([_to_row(c) for c in claims])
            session.commit()
        return claims

    def get(self, claim_id: UUID) -> Optional[Claim]:
        with SessionLocal() as session:
            row = session.get(ClaimRow, claim_id)
            return _to_claim(row) if row else None

    def get_all(self) -> List[Claim]:
        with SessionLocal() as session:
            rows = session.scalars(select(ClaimRow).order_by(*_NEWEST_FIRST)).all()
            return [_to_claim(r) for r in rows]

    def get_labeled(self) -> List[Claim]:
        """Only claims with a ground-truth label (and a stored prediction)."""
        with SessionLocal() as session:
            stmt = (
                select(ClaimRow)
                .where(ClaimRow.true_label.is_not(None), ClaimRow.prediction.is_not(None))
                .order_by(*_NEWEST_FIRST)
            )
            return [_to_claim(r) for r in session.scalars(stmt).all()]

    def count(self) -> int:
        with SessionLocal() as session:
            return session.scalar(select(func.count()).select_from(ClaimRow)) or 0

    def update_label(self, claim_id: UUID, label: bool) -> Optional[Claim]:
        with SessionLocal() as session:
            row = session.get(ClaimRow, claim_id)
            if row is None:
                return None
            row.true_label = label
            session.commit()
            return _to_claim(row)

    def clear(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(ClaimRow))
            session.commit()


db = ClaimStore()
