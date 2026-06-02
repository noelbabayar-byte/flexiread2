#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Update system packages
echo "📦 Updating system packages..."
apt-get update --allow-unauthenticated && \
    apt-get install -y --no-install-recommends gnupg dirmngr curl && \
    (apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 || \
     apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0E98404D386FA1D9 || \
     echo "GPG key import failed, continuing with unauthenticated fallback...") && \
    echo "Acquire::AllowInsecureRepositories \"true\";" > /etc/apt/apt.conf.d/99allow-insecure && \
    echo "Acquire::AllowUnauthenticated \"true\";" >> /etc/apt/apt.conf.d/99allow-insecure && \
    apt-get update
apt-get install -y --no-install-recommends --allow-unauthenticated \
  build-essential \
  libpq-dev \
  tesseract-ocr \
  libtesseract-dev \
  poppler-utils \
  redis-server \
  postgresql-client \
  curl \
  wget \
  git \
  ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/apt.conf.d/99allow-insecure

# Verify Python is installed
echo "🐍 Checking Python installation..."
python3 --version
pip3 --version

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip setuptools wheel
pip3 install -r requirements.txt || {
  echo "⚠️ Warning: Some Python packages failed to install"
  echo "Continuing with setup..."
}

# Verify Node is installed
echo "📱 Checking Node.js installation..."
node --version
npm --version

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend || exit 1
npm install || {
  echo "⚠️ Warning: npm install had issues"
}
cd ..

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p migrations

# Check if Docker is available
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  docker-compose -f docker-compose.codespaces.yml up -d || {
    echo "⚠️ Warning: Docker Compose failed to start"
    echo "You may need to start it manually"
  }
  
  # Wait for services to be ready
  echo "⏳ Waiting for services to start..."
  sleep 10
else
  echo "⚠️ Docker not available - skipping Docker Compose"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
  echo "📝 Creating .env file with defaults..."
  cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://flexiread:flexiread@localhost:5432/flexiread

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3 / MinIO
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET_NAME=flexiread-dev
AWS_S3_REGION=us-east-1
AWS_S3_INTERNAL_ENDPOINT_URL=http://minio:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Tesseract
TESSERACT_CMD=/usr/bin/tesseract
EOF
fi

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Backend:  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  2. Worker:   celery -A worker.tasks worker --loglevel=info"
echo "  3. Frontend: cd frontend && npm run dev"
echo ""
echo "🌐 Services will be available on:"
echo "  - Frontend:  http://localhost:3000"
echo "  - Backend:   http://localhost:8000"
echo "  - API Docs:  http://localhost:8000/docs"
echo "  - MinIO:     http://localhost:9000"
echo ""
echo "💡 Tip: Open multiple terminals in Codespaces to run each service"
