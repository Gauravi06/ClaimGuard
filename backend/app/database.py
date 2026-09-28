from typing import List, Optional, Dict
from uuid import UUID
from app.models import Claim

class ClaimStore:
    def __init__(self):
        self.claims: Dict[UUID, Claim] = {}
        self.claims_list: List[Claim] = []

    def add(self, claim: Claim) -> Claim:
        self.claims[claim.id] = claim
        self.claims_list.append(claim)
        return claim

    def get(self, claim_id: UUID) -> Optional[Claim]:
        return self.claims.get(claim_id)

    def get_all(self) -> List[Claim]:
        return sorted(self.claims_list, key=lambda x: x.submission_date, reverse=True)

    def update_label(self, claim_id: UUID, label: bool) -> Optional[Claim]:
        claim = self.claims.get(claim_id)
        if claim:
            claim.true_label = label
        return claim

db = ClaimStore()
