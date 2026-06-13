#!/bin/bash

# Docker çalışıyor mu kontrol et
if ! docker ps > /dev/null 2>&1; then
    echo "🔧 Restarting Docker daemon..."
    nohup dockerd > /var/log/dockerd.log 2>&1 &
    sleep 3
fi

echo ""
echo "🐳 Docker: $(docker --version 2>/dev/null || echo 'NOT RUNNING')"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No containers yet"
echo ""
