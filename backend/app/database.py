"""Persistent claim store (SQLAlchemy sync).

Production uses Neon PostgreSQL via the ``DATABASE_URL`` environment variable
(loaded from a git-ignored ``.env`` at the repo root if present). The automated
tests point ``DATABASE_URL`` at SQLite.

The public ``db`` API is unchanged:
add / get / get_all / update_label, plus clear / add_many / get_labeled / count.

Lifecycle: a claim is PENDING while ``true_label`` is NULL and becomes SETTLED the
moment its ground-truth label arrives. Only ``true_label`` and ``status`` change at
settlement; the stored prediction, score, risk level and explanations never do.

The PostgreSQL compatibility migration exists because SQLAlchemy's
Base.metadata.create_all() only creates missing tables; it does not add columns
to an already-existing table. This keeps an existing Neon database compatible
with the current ClaimRow schema without requiring Alembic.
"""

import os
from datetime import timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, func, inspect, select, text
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
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
    )
else:
    # pool_pre_ping / pool_recycle: Neon suspends idle compute and drops connections.
    engine = create_engine(
        _url,
        pool_pre_ping=True,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# These columns were added when ClaimGuard moved from the original 7-feature
# contract to the 14-feature real-data model.
#
# They are only used to bring an existing PostgreSQL database up to the current
# schema. New claims still provide these values explicitly through the API.
#
# Defaults are used only to backfill rows that already existed before these
# columns were introduced. The defaults are removed immediately after the
# migration so future inserts cannot silently omit these fields.
_POSTGRES_SCHEMA_MIGRATION = {
    "fault": ("INTEGER", "1"),
    "deductible": ("DOUBLE PRECISION", "400.0"),
    "driver_rating": ("INTEGER", "2"),
    "age": ("DOUBLE PRECISION", "40.0"),
    "accident_area": ("INTEGER", "1"),
    "address_change_claim": ("INTEGER", "0"),
    "number_of_suppliments": ("DOUBLE PRECISION", "0.0"),
}


def _migrate_existing_postgres_schema() -> None:
    """Bring an existing PostgreSQL claims table up to the current ORM schema.

    ``create_all()`` does not alter existing tables. This migration therefore
    checks the actual PostgreSQL columns and adds only those that are missing.

    Existing rows are backfilled once using the legacy-compatible values above.
    The SQL defaults are then removed so new API requests must provide the
    corresponding fields explicitly.
    """
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)

    if not inspector.has_table("claims"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("claims")
    }

    missing_columns = [
        column_name
        for column_name in _POSTGRES_SCHEMA_MIGRATION
        if column_name not in existing_columns
    ]

    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name in missing_columns:
            sql_type, default_value = _POSTGRES_SCHEMA_MIGRATION[column_name]

            # PostgreSQL requires a value for existing rows when adding a
            # non-nullable column. The temporary DEFAULT backfills those rows.
            connection.execute(
                text(
                    f'ALTER TABLE claims '
                    f'ADD COLUMN "{column_name}" {sql_type} '
                    f"NOT NULL DEFAULT {default_value}"
                )
            )

            # Remove the SQL default immediately. Future inserts must supply
            # the field explicitly through the validated API.
            connection.execute(
                text(
                    f'ALTER TABLE claims '
                    f'ALTER COLUMN "{column_name}" DROP DEFAULT'
                )
            )


def init_db() -> None:
    """Create the claims table and upgrade an existing PostgreSQL schema."""
    Base.metadata.create_all(engine)
    _migrate_existing_postgres_schema()


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
        fault=claim.fault,
        deductible=claim.deductible,
        driver_rating=claim.driver_rating,
        age=claim.age,
        accident_area=claim.accident_area,
        address_change_claim=claim.address_change_claim,
        number_of_suppliments=claim.number_of_suppliments,
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
    if submitted.tzinfo is None:
        # SQLite drops tzinfo; values are always stored as UTC.
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
        fault=row.fault,
        deductible=row.deductible,
        driver_rating=row.driver_rating,
        age=row.age,
        accident_area=row.accident_area,
        address_change_claim=row.address_change_claim,
        number_of_suppliments=row.number_of_suppliments,
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
            rows = session.scalars(
                select(ClaimRow).order_by(*_NEWEST_FIRST)
            ).all()
            return [_to_claim(r) for r in rows]

    def get_labeled(self) -> List[Claim]:
        """Only claims with a ground-truth label (and a stored prediction)."""
        with SessionLocal() as session:
            stmt = (
                select(ClaimRow)
                .where(
                    ClaimRow.true_label.is_not(None),
                    ClaimRow.prediction.is_not(None),
                )
                .order_by(*_NEWEST_FIRST)
            )
            return [_to_claim(r) for r in session.scalars(stmt).all()]

    def count(self) -> int:
        with SessionLocal() as session:
            return session.scalar(
                select(func.count()).select_from(ClaimRow)
            ) or 0

    def update_label(
        self,
        claim_id: UUID,
        label: bool,
    ) -> Optional[Claim]:
        with SessionLocal() as session:
            row = session.get(ClaimRow, claim_id)

            if row is None:
                return None

            row.true_label = label
            row.status = "settled"

            session.commit()

            return _to_claim(row)

    def clear(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(ClaimRow))
            session.commit()


db = ClaimStore()