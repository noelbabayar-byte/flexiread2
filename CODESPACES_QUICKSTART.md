# 🚀 FlexiRead on GitHub Codespaces - Complete Quick Start

## Overview

This guide walks you through running FlexiRead on GitHub Codespaces using your iPad Pro (or any browser).

**What you'll get:**
- ✅ Full backend (FastAPI) + frontend (React) running in the cloud
- ✅ PostgreSQL database, Redis cache, MinIO S3 storage
- ✅ Celery async workers for PDF processing
- ✅ Public URLs (no localhost needed)
- ✅ Accessible from iPad, phone, or any device

---

## Step 1: Create a GitHub Codespace

1. **Fork the repository** (if you haven't already)
   - Go to: https://github.com/your-username/flexiread-backend
   - Click "Fork" button

2. **Create a Codespace**
   - Click the green "Code" button
   - Select "Codespaces" tab
   - Click "Create codespace on main"
   - Wait ~2 minutes for the environment to initialize

3. **Verify Setup**
   - You should see VS Code in your browser
   - Terminal should show: `✅ Setup Complete!`
   - Check the `.env` file was created with your Codespaces URLs

---

## Step 2: Start Docker Services

Once Codespaces is ready, open a terminal and run:

```bash
docker-compose -f docker-compose.codespaces.yml up --build -d
```

**What this does:**
- Builds and starts 6 services (db, redis, minio, api, worker, frontend)
- Creates volumes for persistent data
- Sets up networking between services

**Wait for services to start** (~60-90 seconds):

```bash
docker-compose -f docker-compose.codespaces.yml ps
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

**To find your Codespace name:**
- Look at the URL in your browser: `https://[codespace-name].github.dev/...`
- Or check the Codespaces tab on GitHub

---

## Step 4: Test the API

### 4.1 Check API Health

```bash
curl https://[codespace-name]-8000.github.dev/health
```

Expected response:
```json
{"status": "healthy"}
```

### 4.2 Register a User

```bash
curl -X POST https://[codespace-name]-8000.github.dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

Expected response:
```json
{
  "id": "uuid-here",
  "email": "test@example.com",
  "full_name": "Test User",
  "plan_type": "free"
}
```

### 4.3 Login and Get JWT Token

```bash
curl -X POST https://[codespace-name]-8000.github.dev/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

Expected response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "test@example.com"
  }
}
```

**Save the `access_token`** - you'll need it for the next steps.

---

## Step 5: Test PDF Upload (Presigned URL)

### 5.1 Request Presigned Upload URL

```bash
TOKEN="your-access-token-from-step-4.3"

curl -X POST https://[codespace-name]-8000.github.dev/books/upload-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-book.pdf",
    "file_size": 1024000,
    "content_type": "application/pdf"
  }'
```

Expected response:
```json
{
  "presigned_url": "https://[codespace-name]-9000.github.dev/flexiread-dev/...",
  "book_id": "uuid-here",
  "expires_in": 3600
}
```

### 5.2 Upload PDF to S3 (via Presigned URL)

```bash
PRESIGNED_URL="url-from-step-5.1"
PDF_FILE="path/to/your/test.pdf"

curl -X PUT "$PRESIGNED_URL" \
  --data-binary @"$PDF_FILE" \
  -H "Content-Type: application/pdf"
```

Expected: HTTP 200 (no response body)

---

## Step 6: Trigger PDF Processing

### 6.1 Start Processing

```bash
TOKEN="your-access-token"
BOOK_ID="book-id-from-step-5.1"

curl -X POST https://[codespace-name]-8000.github.dev/books/$BOOK_ID/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "book_id": "uuid-here",
  "status": "processing",
  "progress_percentage": 0,
  "message": "PDF processing started"
}
```

### 6.2 Check Processing Status (Poll)

```bash
TOKEN="your-access-token"
BOOK_ID="book-id-from-step-5.1"

# Check every 5 seconds
for i in {1..20}; do
  curl -s https://[codespace-name]-8000.github.dev/books/$BOOK_ID/status \
    -H "Authorization: Bearer $TOKEN" | jq .
  sleep 5
done
```

Expected progression:
```json
{"status": "processing", "progress_percentage": 25}
{"status": "processing", "progress_percentage": 50}
{"status": "processing", "progress_percentage": 75}
{"status": "completed", "progress_percentage": 100}
```

---

## Step 7: Retrieve Processed Content

### 7.1 Get Content URL

```bash
TOKEN="your-access-token"
BOOK_ID="book-id-from-step-5.1"

curl -s https://[codespace-name]-8000.github.dev/books/$BOOK_ID/content \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Expected response:
```json
{
  "book_id": "uuid-here",
  "title": "test-book.pdf",
  "content_url": "https://[codespace-name]-9000.github.dev/flexiread-dev/...",
  "total_pages": 120,
  "is_ocr": true
}
```

### 7.2 Download Content (JSON)

```bash
CONTENT_URL="url-from-step-7.1"

curl -s "$CONTENT_URL" | jq . | head -50
```

Expected: JSON with structure:
```json
{
  "book_id": "uuid",
  "total_pages": 120,
  "pages": [
    {
      "page_number": 1,
      "is_ocr": true,
      "blocks": [
        {
          "id": "block-1",
          "type": "text",
          "content": "Chapter 1: Introduction..."
        }
      ]
    }
  ]
}
```

---

## Step 8: Test Frontend (Browser)

1. **Open Frontend URL**
   - Go to: `https://[codespace-name]-5173.github.dev`

2. **Register/Login**
   - Use the same email/password from Step 4.2

3. **Upload PDF**
   - Click "Upload PDF" button
   - Select a PDF file from your device
   - Watch the progress bar

4. **View Processed Content**
   - Once processing completes, click "Read"
   - You should see the reflowed text with your reading preferences

---

## Step 9: Monitor Services

### View Logs

```bash
# All services
docker-compose -f docker-compose.codespaces.yml logs -f

# Specific service
docker-compose -f docker-compose.codespaces.yml logs -f api
docker-compose -f docker-compose.codespaces.yml logs -f worker
```

### Check Database

```bash
docker-compose -f docker-compose.codespaces.yml exec db psql -U flexiread -d flexiread -c "SELECT * FROM users;"
```

### Check Redis

```bash
docker-compose -f docker-compose.codespaces.yml exec redis redis-cli -a flexiread_redis_dev KEYS "*"
```

### Access MinIO Console

- URL: `https://[codespace-name]-9001.github.dev`
- Username: `minioadmin`
- Password: `minioadmin`

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose -f docker-compose.codespaces.yml logs

# Restart all services
docker-compose -f docker-compose.codespaces.yml restart

# Full reset
docker-compose -f docker-compose.codespaces.yml down -v
docker-compose -f docker-compose.codespaces.yml up --build -d
```

### Port forwarding not working

- Check "Ports" tab in VS Code
- If ports aren't listed, manually add them:
  - Click "Add Port" → 8000, 5173, 9000, 9001

### Database connection error

```bash
# Check if DB is healthy
docker-compose -f docker-compose.codespaces.yml ps db

# Connect directly
docker-compose -f docker-compose.codespaces.yml exec db psql -U flexiread
```

### API returns 404

- Make sure `PUBLIC_API_URL` in `.env` matches your Codespace URL
- Check: `docker-compose -f docker-compose.codespaces.yml logs api`

### PDF processing stuck

```bash
# Check Celery worker logs
docker-compose -f docker-compose.codespaces.yml logs worker

# Check Redis queue
docker-compose -f docker-compose.codespaces.yml exec redis redis-cli -a flexiread_redis_dev LLEN celery
```

---

## Useful Commands

```bash
# Start services
docker-compose -f docker-compose.codespaces.yml up -d

# Stop services
docker-compose -f docker-compose.codespaces.yml down

# View running services
docker-compose -f docker-compose.codespaces.yml ps

# View logs (live)
docker-compose -f docker-compose.codespaces.yml logs -f

# Restart a service
docker-compose -f docker-compose.codespaces.yml restart api

# Execute command in container
docker-compose -f docker-compose.codespaces.yml exec api bash

# View environment variables
docker-compose -f docker-compose.codespaces.yml config | grep -A 50 "environment:"

# Full reset (warning: deletes all data)
docker-compose -f docker-compose.codespaces.yml down -v
```

---

## Next Steps

1. **Customize Settings**
   - Edit `.env` to change quotas, timeouts, etc.
   - Restart services: `docker-compose -f docker-compose.codespaces.yml restart`

2. **Deploy to Production**
   - See `PRODUCTION_DEPLOYMENT.md` for AWS/GCP/Azure setup

3. **Run Tests**
   - See `E2E_TEST_PROTOCOL.md` for automated testing

4. **Develop Locally**
   - Make code changes in your editor
   - Services auto-reload (hot reload enabled)

---

## Support

- **Logs**: Check `docker-compose -f docker-compose.codespaces.yml logs`
- **Docs**: See `README.md` and individual module docs
- **Issues**: Check GitHub Issues or create a new one

---

Happy coding! 🎉
