from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.ml.pipeline import ml_pipeline
from app.routes import claims, analytics, seed, sim
from app.metrics import get_metrics_bytes, CONTENT_TYPE_LATEST

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Loading ClaimGuard ML pipeline (XGBoost real-data champion)...")
    ml_pipeline.load_or_train()
    print("ML pipeline loaded successfully.")
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
app.include_router(sim.router)

@app.get("/")
def root():
    return {"message": "Welcome to ClaimGuard API"}

@app.get("/metrics")
def prometheus_metrics():
    """Prometheus exposition format metrics for ClaimGuard simulation."""
    return Response(content=get_metrics_bytes(), media_type=CONTENT_TYPE_LATEST)

