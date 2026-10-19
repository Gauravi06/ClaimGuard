from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.ml.pipeline import CLAIM_TYPE_MAP

class ClaimBase(BaseModel):
    claimant_name: str
    claim_amount: float = Field(ge=0)
    claim_type: str
    incident_date: str
    days_to_report: int = Field(ge=0)
    description: str
    prior_claims_count: int = Field(ge=0)
    police_report_filed: bool
    witnesses: int = Field(ge=0)

    # The 14 production model features are all required: the API must receive
    # explicit, intentional values for every real-data feature needed for a
    # prediction. No silent defaults are fabricated anywhere in the pipeline.
    fault: int = Field(ge=0, le=1, description="0 = Third Party, 1 = Policy Holder")
    deductible: float = Field(gt=0, description="Deductible tier ($300, $400, $500, $700)")
    driver_rating: int = Field(ge=1, le=4, description="Driver risk tier 1-4")
    age: float = Field(ge=16.0, description="Driver/policyholder age")
    accident_area: int = Field(ge=0, le=1, description="0 = Rural, 1 = Urban")
    address_change_claim: int = Field(ge=0, le=4, description="0=no change, 1=4-8yr, 2=2-3yr, 3=1yr, 4=<6mo")
    number_of_suppliments: float = Field(ge=0.0, description="Supplemental claims requested count")

class ClaimCreate(ClaimBase):
    @field_validator("claim_type")
    @classmethod
    def claim_type_must_be_supported(cls, v: str) -> str:
        # claim_type feeds claim_type_encoded; reject unknown values at the API
        # boundary instead of defaulting them.
        if v.lower() not in CLAIM_TYPE_MAP:
            raise ValueError(f"Unsupported claim_type {v!r}. Supported values: {sorted(CLAIM_TYPE_MAP)}")
        return v

class Explanation(BaseModel):
    feature: str
    importance: float
    value: float
    direction: str

class Claim(ClaimBase):
    id: UUID = Field(default_factory=uuid4)
    fraud_score: float
    risk_level: str
    explanations: List[Explanation]
    status: str = "pending"
    submission_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    true_label: Optional[bool] = None
    prediction: Optional[bool] = None

    @model_validator(mode="after")
    def status_follows_label(self):
        # Lifecycle: PENDING while true_label is NULL, SETTLED once the label exists.
        self.status = "settled" if self.true_label is not None else "pending"
        return self

class LabelUpdate(BaseModel):
    true_label: bool

class SimulationRequest(BaseModel):
    count: int
    fraud_rate: float