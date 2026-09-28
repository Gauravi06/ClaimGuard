"""SQLAlchemy ORM model for persisted claims.

One table mirrors the existing Pydantic ``Claim`` model column for column.
``explanations`` is JSONB on PostgreSQL (Neon) and generic JSON elsewhere
(SQLite, used by the automated tests).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Double, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ClaimRow(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    # --- claim inputs (ClaimBase) ---
    claimant_name: Mapped[str] = mapped_column(Text, nullable=False)
    claim_amount: Mapped[float] = mapped_column(Double, nullable=False)
    claim_type: Mapped[str] = mapped_column(String, nullable=False)
    # Kept as text on purpose: the form sends YYYY-MM-DD, the simulator an ISO datetime.
    incident_date: Mapped[str] = mapped_column(String, nullable=False)
    days_to_report: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prior_claims_count: Mapped[int] = mapped_column(Integer, nullable=False)
    police_report_filed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    witnesses: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- prediction, computed once at creation and never re-scored ---
    fraud_score: Mapped[float] = mapped_column(Double, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    explanations: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    prediction: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # --- lifecycle ---
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    submission_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # NULL = unlabeled; True = fraud; False = legitimate. Arrives later.
    true_label: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (Index("ix_claims_submission_date", "submission_date"),)
