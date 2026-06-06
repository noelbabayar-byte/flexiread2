#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Update system packages
echo "📦 Updating system packages..."
apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  gnupg \
  wget \
  git \
  build-essential \
  libpq-dev \
  tesseract-ocr \
  libtesseract-dev \
  postgresql-client \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip setuptools wheel
pip3 install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
if [ -f pnpm-lock.yaml ]; then
  npm install -g pnpm
  pnpm install
else
  npm install
fi
cd ..

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p uploads

# Start Docker Compose services
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  docker compose -f docker-compose.codespaces.yml up -d
else
  echo "⚠️ Docker not available - skipping Docker Compose"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
  echo "📝 Creating .env file from .env.example..."
  if [ -f .env.example ]; then
    cp .env.example .env
    # Customize for Codespaces
    sed -i "s/APP_ENV=development/APP_ENV=codespaces/g" .env
    sed -i "s/DEBUG=True/DEBUG=True/g" .env
  else
    echo "⚠️ .env.example not found, creating basic .env"
    cat > .env << 'EOF'
APP_ENV=codespaces
DATABASE_URL=postgresql://flexiread:flexiread_dev_password@db:5432/flexiread
REDIS_URL=redis://:flexiread_redis_dev@redis:6379/0
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET=flexiread-dev
JWT_SECRET_KEY=change-me-in-production-min-32-chars-long
EOF
  fi
fi

echo "✅ Setup complete!"
