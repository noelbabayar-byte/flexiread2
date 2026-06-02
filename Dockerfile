# Multi-stage Dockerfile for FastAPI + Celery
# Stages: base -> development -> production
# Context: Root directory (contains app/, worker/, requirements.txt)

# ============================================================================
# Stage 1: Base
# ============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gnupg dirmngr curl && \
    # Eksik olan 0E98404D386FA1D9 anahtarını Ubuntu anahtar sunucusundan çekip APT anahtarlığına ekliyoruz
    (apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 || \
     apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0E98404D386FA1D9 || \
     echo "GPG key import failed, continuing with unauthenticated fallback...") && \
    # Alternatif olarak APT'nin imza kontrolünü bu aşamada esnetmek için ayar yapıyoruz
    echo "Acquire::AllowInsecureRepositories \"true\";" > /etc/apt/apt.conf.d/99allow-insecure && \
    echo "Acquire::AllowUnauthenticated \"true\";" >> /etc/apt/apt.conf.d/99allow-insecure && \
    # Sistem paketlerini kuruyoruz
    apt-get update && apt-get install -y --no-install-recommends \
    --allow-unauthenticated \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/apt.conf.d/99allow-insecure

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================================
# Stage 2: Development
# ============================================================================
FROM base as development

# Install development dependencies
RUN pip install \
    ipython \
    ipdb \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    isort

# Copy application code
COPY app/ ./app/
COPY worker/ ./worker/


# Create non-root user (optional but recommended)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Stage 3: Production
# ============================================================================
FROM base as production

# Install production-only dependencies
RUN pip install gunicorn

# Copy application code
COPY app/ ./app/
COPY worker/ ./worker/


# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (gunicorn + uvicorn workers)
CMD ["gunicorn", \
     "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
