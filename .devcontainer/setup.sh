#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update 2>/dev/null || sudo apk update 2>/dev/null || true
sudo apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tur curl 2>/dev/null || sudo apk add tesseract-ocr tesseract-ocr-data-tur curl 2>/dev/null || true

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user --upgrade pip
if [ -f requirements.txt ]; then
    pip3 install --user -r requirements.txt || echo "⚠️ Warning: Some Python packages failed"
fi

# Create .env safely
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        echo "APP_ENV=development" > .env
        echo "DATABASE_URL=postgresql://flexiread:flexiread_dev_password@db:5432/flexiread" >> .env
        echo "REDIS_URL=redis://:flexiread_redis_dev@redis:6379/0" >> .env
    fi
fi

# Docker Compose Setup
if command -v docker &> /dev/null; then
    echo "🐳 Docker found, starting services..."
    docker compose -f docker-compose.codespaces.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.codespaces.yml up --build -d
    echo "⏳ Waiting for services..."
    sleep 10
    docker compose -f docker-compose.codespaces.yml exec -T api alembic upgrade head 2>/dev/null || echo "⚠️ Migration may need manual run"
    echo "✅ Setup complete!"
else
    echo "⚠️ Docker not found in PATH"
    echo "📋 Manual start commands:"
    echo "   sudo apk add docker docker-cli docker-compose"
    echo "   sudo dockerd &"
    echo "   docker compose -f docker-compose.codespaces.yml up --build -d"
fi
