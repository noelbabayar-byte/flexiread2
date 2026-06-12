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

# Create .env safely
if [ ! -f .env ]; then
  echo "📝 Creating .env file from .env.example..."
  if [ -f .env.example ]; then
    cp .env.example .env
  else
    echo "APP_ENV=codespaces" > .env
    echo "DATABASE_URL=postgresql://flexiread:flexiread_dev_password@db:5432/flexiread" >> .env
    echo "REDIS_URL=redis://:flexiread_redis_dev@redis:6379/0" >> .env
  fi
fi

# Docker Compose Setup
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  
  # Clean up any existing state
  docker compose -f docker-compose.codespaces.yml down --remove-orphans 2>/dev/null || true
  
  # Build and start services
  docker compose -f docker-compose.codespaces.yml up --build -d
  
  # Run migrations in background to not block setup completion
  (
    echo "⏳ Waiting for API to be ready for migrations..."
    for i in {1..30}; do
      if curl -s http://localhost:8000/health > /dev/null; then
        echo "🔄 Running database migrations..."
        docker compose -f docker-compose.codespaces.yml exec -T api alembic upgrade head
        break
      fi
      sleep 2
    done
  ) &
else
  echo "⚠️ Docker not available - skipping Docker Compose"
fi

echo "✅ Setup complete!"
