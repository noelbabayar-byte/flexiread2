#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tur \
    curl \
    file \
    libmagic1 \
    && sudo rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user --upgrade pip
if [ -f requirements.txt ]; then
    pip3 install --user -r requirements.txt || echo "⚠️ Warning: Some Python packages failed"
fi
if [ -f requirements-dev.txt ]; then
    pip3 install --user -r requirements-dev.txt || echo "⚠️ Warning: Some dev packages failed"
fi

# Create .env safely
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        echo "APP_ENV=development" > .env
        echo "DATABASE_URL=postgresql://flexiread:flexiread_dev_password@db:5432/flexiread" >> .env
        echo "REDIS_URL=redis://:flexiread_redis_dev@redis:6379/0" >> .env
    fi
fi

echo "✅ Setup complete!"
echo ""
echo "📋 Manuel başlatma komutları:"
echo "   1. PostgreSQL: docker run -d --name postgres -e POSTGRES_USER=flexiread -e POSTGRES_PASSWORD=flexiread_dev_password -e POSTGRES_DB=flexiread -p 5432:5432 postgres:15-alpine"
echo "   2. Redis: docker run -d --name redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes --requirepass flexiread_redis_dev"
echo "   3. MinIO: docker run -d --name minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio/minio server /data --console-address ':9001'"
echo "   4. API: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "   5. Worker: celery -A app.core.celery_app worker --loglevel=info"
echo "   6. Frontend: cd frontend && npm install && npm run dev"
