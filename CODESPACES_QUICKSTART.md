# 🚀 FlexiRead on GitHub Codespaces - Complete Quick Start

## Overview

This guide walks you through running FlexiRead on GitHub Codespaces.

**What you'll get:**
- ✅ Full backend (FastAPI) + frontend (React) running in the cloud
- ✅ PostgreSQL database, Redis cache, MinIO S3 storage
- ✅ Celery async workers for PDF processing
- ✅ Public URLs (no localhost needed)

---

## Step 1: Create a GitHub Codespace

1. **Fork the repository** (if you haven't already)
2. **Create a Codespace**
   - Click the green "Code" button
   - Select "Codespaces" tab
   - Click "Create codespace on main"
   - Wait ~2 minutes for the environment to initialize

3. **Verify Setup**
   - You should see VS Code in your browser
   - Terminal should show: `✅ Setup complete!`
   - Check the `.env` file was created with your Codespaces URLs

---

## Step 2: Start Docker Services

Once Codespaces is ready, open a terminal and run:

```bash
docker compose -f docker-compose.codespaces.yml up --build -d
```

**Wait for services to start** (~60-90 seconds):

```bash
docker compose -f docker-compose.codespaces.yml ps
```

Expected output:
```
NAME                    STATUS              PORTS
flexiread-db            Up (healthy)        5432/tcp
flexiread-redis         Up (healthy)        6379/tcp
flexiread-minio         Up (healthy)        9000/tcp, 9001/tcp
flexiread-minio-init    Exited (0)          
flexiread-api           Up (healthy)        8000/tcp
flexiread-worker        Up                  
flexiread-frontend      Up                  5173/tcp
```

---

## Step 3: Access Services

GitHub Codespaces automatically forwards ports to public URLs. Check the "Ports" tab in VS Code:

| Service | Local Port | Public URL |
|---------|-----------|-----------|
| **Frontend** | 5173 | `https://[codespace-name]-5173.github.dev` |
| **API** | 8000 | `https://[codespace-name]-8000.github.dev` |
| **MinIO** | 9001 | `https://[codespace-name]-9001.github.dev` |

---

## Step 4: Useful Commands

### View Logs

```bash
# All services
docker compose -f docker-compose.codespaces.yml logs -f

# Specific service
docker compose -f docker-compose.codespaces.yml logs -f api
docker compose -f docker-compose.codespaces.yml logs -f worker
```

### Check Database

```bash
docker compose -f docker-compose.codespaces.yml exec db psql -U flexiread -d flexiread -c "SELECT * FROM users;"
```

### Check Redis

```bash
docker compose -f docker-compose.codespaces.yml exec redis redis-cli -a flexiread_redis_dev KEYS "*"
```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose -f docker-compose.codespaces.yml logs

# Restart all services
docker compose -f docker-compose.codespaces.yml restart

# Full reset
docker compose -f docker-compose.codespaces.yml down -v
docker compose -f docker-compose.codespaces.yml up --build -d
```

### API returns 404

- Make sure `PUBLIC_API_URL` in `.env` matches your Codespace URL
- Check: `docker compose -f docker-compose.codespaces.yml logs api`

---

Happy coding! 🎉
