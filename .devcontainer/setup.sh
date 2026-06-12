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
  cp .env.example .env || echo "APP_ENV=codespaces" > .env
fi

# Start Docker Compose in background
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  (docker compose -f docker-compose.codespaces.yml up -d && \
   sleep 20 && \
   docker compose -f docker-compose.codespaces.yml exec -T api alembic upgrade head) &
fi

echo "✅ Setup complete!"
