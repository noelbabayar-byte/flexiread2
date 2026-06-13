#!/bin/bash
set -e

echo "🔄 FlexiRead post-start check..."

# Docker daemon zaten çalışıyor mu kontrol et
if ! docker ps > /dev/null 2>&1; then
    echo "📦 Docker daemon not running, starting..."
    sudo dockerd > /var/log/dockerd.log 2>&1 &
    sleep 5
fi

# Docker versiyonlarını göster
echo ""
echo "🐳 Docker Status:"
docker --version
docker compose version
echo ""

echo "✅ Post-start check complete!"
