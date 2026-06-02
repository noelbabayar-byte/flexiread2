# FlexiRead - End-to-End (E2E) Test Protocol

Complete manual testing guide using cURL, Postman, and Browser.

---

## Prerequisites

- Docker Compose running: `docker-compose up --build -d`
- All services healthy: `docker-compose ps` (all showing "healthy")
- cURL installed: `curl --version`
- Browser (Chrome/Firefox) with DevTools

---

## Test Flow Overview

```
1. Auth: Register & Login → Get JWT Token
2. Presigned URL: Request upload URL from API
3. S3 Upload: PUT file to MinIO via Presigned URL (CORS test)
4. Task Trigger: POST /books/process/{id} to start Celery task
5. Status Poll: GET /books/{id}/status (check Redis cache)
6. Content Fetch: GET /books/{id}/content (fetch from S3)
7. Frontend Render: Load Reader Engine with JSON content
```

---

## STEP 1: Authentication (Register & Login)

### 1.1 Register New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@flexiread.com",
    "password": "SecurePassword123!",
    "full_name": "Test User"
  }'
```

**Expected Response (201):**
```json
{
  "id": "uuid-here",
  "email": "testuser@flexiread.com",
  "full_name": "Test User",
  "plan_type": "free",
  "ocr_quota_remaining": 50,
  "is_active": true
}
```

### 1.2 Login & Get JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@flexiread.com",
    "password": "SecurePassword123!"
  }'
```

**Expected Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid-here",
    "email": "testuser@flexiread.com",
    "plan_type": "free"
  }
}
```

**Save the token:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## STEP 2: Request Presigned Upload URL

### 2.1 Get Upload URL

```bash
curl -X POST http://localhost:8000/api/v1/books/upload-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-book.pdf",
    "file_size_bytes": 1048576,
    "content_type": "application/pdf"
  }'
```

**Expected Response (200):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_url": "http://minio:9000/flexiread-dev/550e8400-e29b-41d4-a716-446655440000?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
  "expires_in_seconds": 3600,
  "fields": {
    "bucket": "flexiread-dev",
    "key": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Save the book_id and upload_url:**
```bash
export BOOK_ID="550e8400-e29b-41d4-a716-446655440000"
export UPLOAD_URL="http://minio:9000/flexiread-dev/550e8400-e29b-41d4-a716-446655440000?X-Amz-Algorithm=..."
```

---

## STEP 3: Upload PDF to MinIO (S3) via Presigned URL

### 3.1 Create Test PDF

```bash
# Create a simple test PDF
echo "Test PDF Content" | \
  python3 -c "
import sys
from reportlab.pdfgen import canvas
from io import BytesIO

buffer = BytesIO()
c = canvas.Canvas(buffer)
c.drawString(100, 750, 'FlexiRead Test Book')
c.drawString(100, 700, 'This is a test PDF for E2E testing')
c.showPage()
c.save()
buffer.seek(0)
sys.stdout.buffer.write(buffer.read())
" > test-book.pdf
```

### 3.2 Upload to MinIO (CORS Test)

```bash
# Upload using presigned URL
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @test-book.pdf \
  -v
```

**Expected Response (200):**
```
< HTTP/1.1 200 OK
< ETag: "abc123def456..."
< x-amz-version-id: "version-id-here"
```

**Verify in MinIO:**
```bash
# Check if file exists
curl http://localhost:9000/flexiread-dev/$BOOK_ID

# Or via MinIO console
# http://localhost:9001 (minioadmin / minioadmin)
```

### 3.3 CORS Test (Browser)

Open Browser DevTools (F12) and run in Console:

```javascript
// Test CORS preflight
fetch('http://localhost:9000/flexiread-dev/test-file', {
  method: 'OPTIONS',
  headers: {
    'Origin': 'http://localhost:5173',
    'Access-Control-Request-Method': 'PUT'
  }
})
.then(r => {
  console.log('Status:', r.status);
  console.log('CORS Headers:', {
    'Access-Control-Allow-Origin': r.headers.get('Access-Control-Allow-Origin'),
    'Access-Control-Allow-Methods': r.headers.get('Access-Control-Allow-Methods')
  });
})
.catch(e => console.error('CORS Error:', e));
```

**Expected:**
```
Status: 200
CORS Headers: {
  'Access-Control-Allow-Origin': 'http://localhost:5173',
  'Access-Control-Allow-Methods': 'GET, PUT, POST, DELETE, HEAD'
}
```

---

## STEP 4: Trigger PDF Processing Task

### 4.1 Start Celery Task

```bash
curl -X POST http://localhost:8000/api/v1/books/$BOOK_ID/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response (202 Accepted):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "task_id": "celery-task-uuid-here",
  "message": "PDF processing started"
}
```

**Save task_id:**
```bash
export TASK_ID="celery-task-uuid-here"
```

### 4.2 Verify Celery Task in Worker Logs

```bash
docker-compose logs -f worker
```

**Expected Output:**
```
worker_1  | [2024-01-15 10:30:45,123: INFO/MainProcess] Received task: app.worker.tasks.process_pdf_task[...]
worker_1  | [2024-01-15 10:30:46,234: DEBUG/MainProcess] Task started: processing PDF...
worker_1  | [2024-01-15 10:30:50,345: DEBUG/MainProcess] OCR processing page 1/1...
worker_1  | [2024-01-15 10:30:55,456: INFO/MainProcess] Task completed successfully
```

---

## STEP 5: Poll Status & Check Redis Cache

### 5.1 Poll Status Endpoint (Redis-first)

```bash
# Poll every 2 seconds (10 times)
for i in {1..10}; do
  echo "=== Poll $i ==="
  curl -s http://localhost:8000/api/v1/books/$BOOK_ID/status \
    -H "Authorization: Bearer $TOKEN" | jq .
  sleep 2
done
```

**Expected Response Progression:**

**Poll 1-3 (Processing):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percentage": 25,
  "message": "Processing page 1 of 4..."
}
```

**Poll 4-6 (Still Processing):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percentage": 50,
  "message": "Processing page 2 of 4..."
}
```

**Poll 7+ (Completed):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress_percentage": 100,
  "parsed_content_url": "http://minio:9000/flexiread-dev/550e8400-e29b-41d4-a716-446655440000-parsed.json?X-Amz-Algorithm=...",
  "total_pages": 4,
  "processed_pages": 4
}
```

### 5.2 Check Redis Cache

```bash
# Connect to Redis
docker-compose exec redis redis-cli -a flexiread_redis_dev

# View all keys
> KEYS *

# Get book progress
> GET book:550e8400-e29b-41d4-a716-446655440000:progress

# Get task status
> GET celery-task-uuid-here

# Exit
> EXIT
```

---

## STEP 6: Fetch Processed Content

### 6.1 Get Content URL

```bash
curl -s http://localhost:8000/api/v1/books/$BOOK_ID/content \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected Response (200):**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "content_url": "http://minio:9000/flexiread-dev/550e8400-e29b-41d4-a716-446655440000-parsed.json?X-Amz-Algorithm=...",
  "expires_in_seconds": 3600,
  "metadata": {
    "total_pages": 4,
    "total_words": 1250,
    "processing_time_seconds": 12
  }
}
```

### 6.2 Download Parsed Content

```bash
# Get presigned URL from previous response
export CONTENT_URL="http://minio:9000/flexiread-dev/550e8400-e29b-41d4-a716-446655440000-parsed.json?X-Amz-Algorithm=..."

# Download JSON
curl -s "$CONTENT_URL" | jq . > parsed-content.json

# View structure
cat parsed-content.json | jq '.pages[0]'
```

**Expected Structure:**
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_pages": 4,
  "pages": [
    {
      "page_number": 1,
      "is_ocr": false,
      "blocks": [
        {
          "id": "block-1",
          "type": "text",
          "content": "Chapter 1: Introduction..."
        },
        {
          "id": "block-2",
          "type": "text",
          "content": "This is the first paragraph..."
        }
      ]
    }
  ]
}
```

---

## STEP 7: Frontend Reader Engine Test

### 7.1 Open Frontend

Navigate to: **http://localhost:5173**

### 7.2 Login in Browser

1. Click "Sign In" button
2. Enter credentials:
   - Email: `testuser@flexiread.com`
   - Password: `SecurePassword123!`
3. Click "Login"

### 7.3 Navigate to Documents

1. After login, you should see Dashboard
2. Click "Belgeler" (Documents) in sidebar
3. You should see the uploaded PDF in the list

### 7.4 Open Reader Engine

1. Click on the PDF in the documents list
2. Reader should load with:
   - Parsed content from JSON
   - Settings panel (font, theme, line height)
   - Table of contents
   - Progress bar

### 7.5 Test Reader Features

**Font Size:**
- Click ⚙️ button → Settings
- Drag "Font Size" slider (14-28px)
- Text should reflow smoothly

**Theme:**
- Click ⚙️ button → Settings
- Click "Dark" / "Sepia" buttons
- Background and text should change instantly

**Scroll Position:**
- Scroll down to middle of book
- Close browser (Ctrl+W)
- Reopen http://localhost:5173
- Login again
- Open same PDF
- **Expected**: Should scroll back to where you left off

**Table of Contents:**
- Click 📑 button
- Click on a section
- Should jump to that section

### 7.6 Check Browser Console (F12)

Open DevTools → Console and verify:

```javascript
// Check if Reader Engine is initialized
console.log(window.readerEngine);

// Check localStorage
console.log(localStorage.getItem('flexiread:book:550e8400-e29b-41d4-a716-446655440000:progress'));

// Check IndexedDB
indexedDB.databases().then(dbs => console.log(dbs));
```

---

## STEP 8: Error Scenarios (Negative Testing)

### 8.1 Test Rate Limiting

```bash
# Try uploading 3 times in 1 minute (free tier limit = 2)
for i in {1..3}; do
  echo "=== Upload $i ==="
  curl -X POST http://localhost:8000/api/v1/books/upload-url \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"filename": "test-'$i'.pdf", "file_size_bytes": 1048576, "content_type": "application/pdf"}'
  sleep 1
done
```

**Expected**: 3rd request returns 429 (Too Many Requests)

### 8.2 Test Invalid JWT

```bash
curl -X GET http://localhost:8000/api/v1/books/$BOOK_ID/status \
  -H "Authorization: Bearer invalid-token-here"
```

**Expected**: 401 (Unauthorized)

### 8.3 Test Missing File

```bash
export FAKE_BOOK_ID="00000000-0000-0000-0000-000000000000"

curl -X GET http://localhost:8000/api/v1/books/$FAKE_BOOK_ID/content \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: 404 (Not Found)

### 8.4 Test CORS Rejection

Browser Console:
```javascript
// Try request from different origin
fetch('http://localhost:9000/flexiread-dev/test', {
  method: 'GET',
  headers: {
    'Origin': 'http://malicious-site.com'
  }
})
.catch(e => console.error('CORS blocked (expected):', e));
```

**Expected**: CORS error in console

---

## STEP 9: Performance & Load Testing

### 9.1 Check Memory Usage

```bash
docker stats flexiread-api flexiread-worker flexiread-db
```

**Expected**: 
- API: <500MB
- Worker: <400MB
- DB: <200MB

### 9.2 Check Celery Queue

```bash
docker-compose exec api python -c "
from app.core.celery_app import app
inspect = app.control.inspect()
print('Active tasks:', inspect.active())
print('Reserved tasks:', inspect.reserved())
print('Stats:', inspect.stats())
"
```

### 9.3 Check Redis Memory

```bash
docker-compose exec redis redis-cli -a flexiread_redis_dev INFO memory
```

---

## Troubleshooting

### CORS Error on S3 Upload

**Symptom**: Browser console shows "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution**:
```bash
# Verify CORS is set
docker-compose exec minio mc cors get local/flexiread-dev

# If not set, manually apply:
docker-compose exec minio mc cors set local/flexiread-dev - <<'EOF'
[{"AllowedHeaders":["*"],"AllowedMethods":["GET","PUT","POST","DELETE","HEAD"],"AllowedOrigins":["http://localhost:5173"],"ExposeHeaders":["ETag"],"MaxAgeSeconds":3000}]
EOF
```

### JWT Token Expired

**Symptom**: 401 Unauthorized after 24 hours

**Solution**:
```bash
# Re-login to get new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@flexiread.com", "password": "SecurePassword123!"}'
```

### Celery Task Stuck

**Symptom**: Status stays "processing" forever

**Solution**:
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Check Redis queue
docker-compose exec redis redis-cli -a flexiread_redis_dev KEYS "*"
```

### MinIO Bucket Not Found

**Symptom**: 404 when uploading

**Solution**:
```bash
# Recreate bucket
docker-compose exec minio mc mb local/flexiread-dev --ignore-existing

# Verify
docker-compose exec minio mc ls local/
```

---

## Summary Checklist

- [ ] Step 1: User registered and JWT token obtained
- [ ] Step 2: Presigned URL received
- [ ] Step 3: PDF uploaded to MinIO (CORS working)
- [ ] Step 4: Celery task started
- [ ] Step 5: Status polling shows progress
- [ ] Step 6: Parsed JSON content downloaded
- [ ] Step 7: Frontend Reader Engine loaded and working
- [ ] Step 8: Error scenarios handled correctly
- [ ] Step 9: Performance metrics acceptable

**All steps passing = System Ready for Production** ✅
