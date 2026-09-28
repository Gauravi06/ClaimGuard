from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

class ClaimBase(BaseModel):
    claimant_name: str
    claim_amount: float
    claim_type: str
    incident_date: str
    days_to_report: int
    description: str
    prior_claims_count: int
    police_report_filed: bool
    witnesses: int

class ClaimCreate(ClaimBase):
    pass

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

class LabelUpdate(BaseModel):
    true_label: bool

class SimulationRequest(BaseModel):
    count: int
    fraud_rate: float
