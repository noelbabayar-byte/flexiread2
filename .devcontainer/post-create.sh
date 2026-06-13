#!/bin/bash
set -e

echo "🚀 FlexiRead setup starting..."

# 1. Docker CLI kur (apt ile, feature yerine)
echo "📦 Installing Docker..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-v2 curl wget git

# 2. Docker daemon'u başlat
echo "🔧 Starting Docker daemon..."
nohup dockerd > /var/log/dockerd.log 2>&1 &
sleep 3

# 3. Docker'ın hazır olduğunu doğrula (max 60 saniye bekle)
echo "⏳ Waiting for Docker..."
for i in {1..30}; do
    if docker ps > /dev/null 2>&1; then
        echo "✅ Docker ready! ($(docker --version))"
        break
    fi
    echo "   Still waiting... ($i/30)"
    sleep 2
done

# 4. Docker hâlâ çalışmıyorsa hata ver
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker failed to start"
    cat /var/log/dockerd.log | tail -30
    exit 1
fi

# 5. pnpm kur
echo "📦 Installing pnpm..."
npm install -g pnpm

# 6. Backend bağımlılıkları
echo "🐍 Installing Python deps..."
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt || echo "⚠️ requirements.txt install had issues"

# 7. Frontend bağımlılıkları
echo "⚛️ Installing frontend deps..."
cd frontend
pnpm install
cd ..

# 8. .env oluştur
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Run these commands:"
echo "   docker compose up -d"
echo "   docker compose exec api alembic upgrade head"
echo "   cd frontend && pnpm dev"
