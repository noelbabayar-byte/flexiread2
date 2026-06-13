#!/bin/bash
set -e

echo "🚀 FlexiRead post-create setup starting..."

# 1. Docker daemon'u başlat (arka planda)
echo "📦 Starting Docker daemon..."
sudo dockerd > /var/log/dockerd.log 2>&1 &
sleep 5

# 2. Docker'ın hazır olduğunu doğrula
echo "🔍 Checking Docker..."
until docker ps > /dev/null 2>&1; do
    echo "   Waiting for Docker daemon..."
    sleep 2
done
echo "✅ Docker is ready!"

# 3. pnpm kur (repo'nun paket yöneticisi)
echo "📦 Installing pnpm..."
npm install -g pnpm

# 4. Backend Python bağımlılıkları
echo "🐍 Installing Python dependencies..."
cd /workspaces/flexiread2 || cd /workspace/flexiread2 || cd .
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt 2>/dev/null || echo "⚠️ requirements.txt not found"

# 5. Frontend bağımlılıkları (pnpm kullan!)
echo "⚛️ Installing frontend dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    pnpm install
    cd ..
else
    echo "⚠️ frontend directory not found"
fi

# 6. .env dosyasını oluştur (yoksa)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

echo "✅ Post-create setup complete!"
echo ""
echo "📋 Next steps:"
echo "   docker compose up -d"
echo "   docker compose exec api alembic upgrade head"
echo "   cd frontend && pnpm dev"
