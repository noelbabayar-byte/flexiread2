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
  && sudo rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user --upgrade pip
if [ -f requirements.txt ]; then
    pip3 install --user -r requirements.txt || echo "⚠️ Warning: Some Python packages failed"
fi

# Create .env if not exists
if [ ! -f .env ]; then
  echo "📝 Creating .env file..."
  cp .env.example .env || echo "APP_ENV=codespaces" > .env
fi

# Docker Compose Setup
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  
  # Clean start
  docker compose -f docker-compose.codespaces.yml down --remove-orphans 2>/dev/null || true
  
  # Build and start
  docker compose -f docker-compose.codespaces.yml up --build -d
  
  echo "⏳ Waiting for services to be healthy..."
  sleep 25
  
  # Migration
  echo "🔄 Running database migrations..."
  docker compose -f docker-compose.codespaces.yml exec -T api alembic upgrade head || echo "⚠️ Migration warning"
else
  echo "⚠️ Docker not available - skipping Docker Compose"
fi

echo "✅ Setup complete!"
