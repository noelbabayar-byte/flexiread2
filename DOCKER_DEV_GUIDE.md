# FlexiRead - Docker Development Environment Guide

## Overview

This guide explains how to run the complete FlexiRead system locally using Docker Compose. The setup includes:

- **PostgreSQL**: Database
- **Redis**: Cache & Celery broker
- **FastAPI**: Backend API
- **Celery Worker**: Async PDF processing
- **React/Vite**: Frontend
- **MinIO**: S3-compatible storage (local development)

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Docker version: 20.10+
- Docker Compose version: 2.0+
- 4GB+ RAM available
- 10GB+ disk space

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd flexiread-backend

# Copy environment template
cp .env.example .env

# (Optional) Edit .env for custom configuration
# nano .env
```

### 2. Build and Start Services

```bash
# Build images and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f frontend
```

### 3. Wait for Services to Be Ready

The system will take 30-60 seconds to fully initialize. You'll see health checks passing:

```
db is healthy
redis is healthy
api is healthy
```

### 4. Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | React Reader Engine |
| **API** | http://localhost:8000 | FastAPI Backend |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **MinIO Console** | http://localhost:9001 | S3 Storage Management |
| **PostgreSQL** | localhost:5432 | Database (psql client) |
| **Redis** | localhost:6379 | Cache/Broker (redis-cli) |

## Common Commands

### Start Services

```bash
# Start all services
docker-compose up

# Start specific service
docker-compose up api
docker-compose up worker
docker-compose up frontend

# Start in background
docker-compose up -d
```

### Stop Services

```bash
# Stop all services (containers still exist)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service (last 100 lines)
docker-compose logs --tail=100 api

# Follow logs in real-time
docker-compose logs -f worker
```

### Execute Commands

```bash
# Run command in API container
docker-compose exec api bash

# Run command in Worker container
docker-compose exec worker bash

# Run command in Frontend container
docker-compose exec frontend bash

# Run database migrations
docker-compose exec api alembic upgrade head

# Create database tables
docker-compose exec api python -m app.core.database
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U flexiread -d flexiread

# Backup database
docker-compose exec db pg_dump -U flexiread -d flexiread > backup.sql

# Restore database
docker-compose exec -T db psql -U flexiread -d flexiread < backup.sql
```

### Redis Management

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli -a flexiread_redis_dev

# View all keys
> KEYS *

# Flush all data
> FLUSHALL

# Exit
> EXIT
```

### MinIO Management

```bash
# Access MinIO Console
# URL: http://localhost:9001
# Username: minioadmin
# Password: minioadmin

# Or use MinIO CLI (mc)
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/flexiread-dev
```

## Development Workflow

### 1. Backend Development (FastAPI)

The API service runs with `--reload` flag, so changes to Python files automatically restart the server.

```bash
# Edit backend code
vim backend/app/main.py

# Changes are automatically applied
docker-compose logs -f api
```

### 2. Frontend Development (React/Vite)

The frontend runs with Vite's HMR (Hot Module Replacement), so changes are reflected instantly.

```bash
# Edit frontend code
vim frontend/src/components/ReaderView.tsx

# Changes are instantly reflected in browser
# Just refresh http://localhost:5173
```

### 3. Celery Worker Development

The worker runs with `--loglevel=debug`, so you can see all task execution details.

```bash
# Monitor worker logs
docker-compose logs -f worker

# Trigger a test task
docker-compose exec api python -c "from app.core.celery_app import app; app.send_task('app.worker.tasks.process_pdf_task', args=('test-book-id',))"
```

### 4. Database Schema Changes

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Add new column"

# Apply migrations
docker-compose exec api alembic upgrade head

# View migration history
docker-compose exec api alembic history
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs api

# Rebuild images
docker-compose build --no-cache

# Restart service
docker-compose restart api
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
# Change "8000:8000" to "8001:8000"
```

### Database Connection Error

```bash
# Check if db is healthy
docker-compose ps db

# Check database logs
docker-compose logs db

# Verify connection string in .env
cat .env | grep DATABASE_URL

# Try connecting directly
docker-compose exec db psql -U flexiread -d flexiread -c "SELECT 1"
```

### Redis Connection Error

```bash
# Check if redis is healthy
docker-compose ps redis

# Check redis logs
docker-compose logs redis

# Try connecting directly
docker-compose exec redis redis-cli -a flexiread_redis_dev ping
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose logs -f worker

# Verify Redis connection
docker-compose exec redis redis-cli -a flexiread_redis_dev KEYS "*"

# Check Celery tasks
docker-compose exec api python -c "from app.core.celery_app import app; app.control.inspect().active()"
```

### Frontend Can't Connect to API

```bash
# Check API is running
docker-compose ps api

# Test API endpoint
curl http://localhost:8000/health

# Check CORS configuration
# Edit .env: ALLOWED_ORIGINS=http://localhost:5173,...

# Restart frontend
docker-compose restart frontend
```

## Performance Optimization

### Reduce Memory Usage

```bash
# Limit memory per service in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Increase Worker Concurrency (for production only)

```bash
# In docker-compose.yml, change worker command:
# command: celery -A app.core.celery_app worker --concurrency=4
# WARNING: Only for production with sufficient resources
```

### Enable Caching

```bash
# Redis is already configured for caching
# Use in your code:
from app.core.cache import cache
cache.set(key, value, ttl=3600)
```

## Cleanup

### Remove Stopped Containers

```bash
docker-compose rm
```

### Remove Unused Images

```bash
docker image prune
```

### Remove All Data (Start Fresh)

```bash
docker-compose down -v
docker-compose up --build
```

## Production Deployment

This docker-compose setup is for **local development only**. For production:

1. Use managed databases (AWS RDS, Google Cloud SQL)
2. Use managed Redis (AWS ElastiCache, Redis Cloud)
3. Use AWS S3 instead of MinIO
4. Use Kubernetes or container orchestration
5. Add reverse proxy (Nginx, Traefik)
6. Enable SSL/TLS certificates
7. Configure proper logging and monitoring

See `DEPLOYMENT.md` for production setup.

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.io/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Check health: `docker-compose ps`
3. Read error messages carefully
4. Try rebuilding: `docker-compose build --no-cache`
5. Start fresh: `docker-compose down -v && docker-compose up --build`
