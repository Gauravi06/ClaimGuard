FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    DATABASE_URL="sqlite:////data/claims.db"

WORKDIR /app

# Install curl for HEALTHCHECK and runtime container inspection
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application code and dataset directories
COPY backend/ /app/backend/
COPY data/ /app/data/

# Pre-train and serialize the XGBoost champion model artifact during image build.
# This ensures data/models/xgb_champion.joblib exists at container startup with zero
# manual steps, providing instant (<10ms) serving without startup latency or failures.
RUN python -c "from app.ml.train_comparison import train_and_save_champion; train_and_save_champion()"

# Create mount point for persistent SQLite database volume
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Container healthcheck querying the root endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start FastAPI application with uvicorn listening on 0.0.0.0:8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
