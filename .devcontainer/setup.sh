#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Update system packages
echo "📦 Updating system packages..."
apt-get update && apt-get install -y \
  build-essential \
  libpq-dev \
  tesseract-ocr \
  libtesseract-dev \
  poppler-utils \
  redis-server \
  postgresql-client \
  curl \
  wget

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Install Node.js dependencies
echo "📱 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p migrations

# Start Docker Compose services
echo "🐳 Starting Docker Compose services..."
docker-compose -f docker-compose.codespaces.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run database migrations
echo "🗄️ Running database migrations..."
python -m alembic upgrade head || echo "⚠️ Migrations skipped (may not be configured)"

# Start background services
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Backend:  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  2. Worker:   celery -A worker.tasks worker --loglevel=info"
echo "  3. Frontend: cd frontend && npm run dev"
echo ""
echo "🌐 Services running on:"
echo "  - Frontend:  http://localhost:3000"
echo "  - Backend:   http://localhost:8000"
echo "  - MinIO:     http://localhost:9000"
echo "  - Docs:      http://localhost:8000/docs"
