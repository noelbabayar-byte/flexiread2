#!/bin/bash
set -e

echo "🚀 FlexiRead Codespaces Setup Started..."

# Use sudo if not root
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

# Update system packages
echo "📦 Updating system packages..."
$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  ca-certificates \
  gnupg \
  wget \
  git \
  build-essential \
  libpq-dev \
  tesseract-ocr \
  libtesseract-dev \
  poppler-utils \
  redis-server \
  postgresql-client \
  curl \
  && $SUDO rm -rf /var/lib/apt/lists/*

# Verify Python is installed
echo "🐍 Checking Python installation..."
python3 --version
pip3 --version

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip setuptools wheel
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt || {
      echo "⚠️ Warning: Some Python packages failed to install"
      echo "Continuing with setup..."
    }
fi

# Verify Node is installed
echo "📱 Checking Node.js installation..."
node --version
npm --version

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    # Use pnpm if available, otherwise fallback to npm
    if [ -f pnpm-lock.yaml ]; then
        if ! command -v pnpm &> /dev/null; then
            echo "Installing pnpm..."
            $SUDO npm install -g pnpm
        fi
        echo "Using pnpm..."
        pnpm install
    else
        echo "Using npm..."
        npm install
    fi
    cd ..
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p migrations

# Start Docker Compose services
if command -v docker &> /dev/null; then
  echo "🐳 Starting Docker Compose services..."
  if [ -f docker-compose.codespaces.yml ]; then
      docker compose -f docker-compose.codespaces.yml up -d || {
        echo "⚠️ Warning: Docker Compose failed to start"
        echo "You may need to start it manually"
      }
      
      # Wait for services to be ready
      echo "⏳ Waiting for services to start..."
      sleep 10
  fi
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
