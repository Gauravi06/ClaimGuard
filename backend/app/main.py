from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.ml.pipeline import ml_pipeline
from app.routes import claims, analytics, seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Training ML pipeline on synthetic data...")
    ml_pipeline.train()
    print("ML pipeline trained successfully.")
    yield
    print("Shutting down ClaimGuard API...")

app = FastAPI(title="ClaimGuard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.claims_router)
app.include_router(claims.simulate_router)
app.include_router(seed.router)
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

@app.get("/")
def root():
    return {"message": "Welcome to ClaimGuard API"}
