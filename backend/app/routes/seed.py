from fastapi import APIRouter
from typing import List
from app.models import Claim
from app.seed import seed_database

router = APIRouter(tags=["Development"])

@router.post("/api/dev/seed", response_model=List[Claim])
@router.post("/api/seed", response_model=List[Claim])
def seed_data():
    """Development endpoint to seed database with 20 realistic demo claims."""
    return seed_database(clear_existing=True)
