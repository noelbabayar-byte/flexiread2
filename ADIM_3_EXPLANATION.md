# ADIM 3: REST API Endpoint'leri ve JWT Koruması - Detaylı Açıklama

## Genel API Mimarisi

```
Frontend
  ↓
[JWT Bearer Token]
  ↓
FastAPI Endpoints (Protected with get_current_user)
  ├─ POST /api/v1/auth/register
  ├─ POST /api/v1/auth/login
  ├─ POST /api/v1/books/upload-url (Presigned URL)
  ├─ POST /api/v1/books/process/{book_id} (Rate Limited)
  ├─ GET /api/v1/books/{book_id}/status (Redis-first)
  └─ GET /api/v1/books/{book_id}/content
  ↓
[Database / S3 / Redis / Celery]
```

## Dosya Yapısı

```
app/
├── core/
│   ├── security.py              # JWT + Password hashing
│   ├── celery_app.py            # Celery config (worker_concurrency=1)
│   └── database.py              # Connection pool (5/5)
├── api/
│   ├── dependencies.py          # get_current_user dependency
│   └── v1/
│       └── endpoints/
│           ├── auth.py          # Login/Register
│           └── books.py         # Upload/Status/Content
├── schemas/
│   ├── auth.py                  # Auth Pydantic models
│   └── books.py                 # Book Pydantic models
├── utils/
│   ├── s3_storage.py
│   ├── ocr_processor.py
│   └── rate_limiter.py          # Redis-based rate limiting
└── main.py                      # FastAPI app entry point
```

## Endpoint Detaylı Açıklaması

### 1. POST /api/v1/auth/register

**Amaç**: Yeni kullanıcı kaydı

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "plan_type": "free",
  "ocr_quota_remaining": 50,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Validations**:
- Email format doğru mu?
- Email zaten kayıtlı mı? → 400 Bad Request
- Password minimum 8 karakter?

**İş Mantığı**:
```python
# 1. Email uniqueness check
existing_user = db.query(User).filter(User.email == request.email).first()
if existing_user:
    raise HTTPException(400, "Email already registered")

# 2. Password hashing with bcrypt
password_hash = security_manager.hash_password(request.password)

# 3. Calculate next month for quota reset
reset_date = datetime(now.year, now.month + 1, 1)

# 4. Create user with FREE tier and 50-page quota
user = User(
    email=request.email,
    password_hash=password_hash,
    plan_type=SubscriptionTier.FREE,
    ocr_quota_remaining=50,
    ocr_quota_reset_date=reset_date,
)
```

---

### 2. POST /api/v1/auth/login

**Amaç**: Kullanıcı girişi ve JWT token üretimi

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Validations**:
- Email var mı?
- Password doğru mu?
- Kullanıcı aktif mi?

**İş Mantığı**:
```python
# 1. Find user by email
user = db.query(User).filter(User.email == request.email).first()

# 2. Verify password with bcrypt
if not security_manager.verify_password(request.password, user.password_hash):
    raise HTTPException(401, "Invalid credentials")

# 3. Create JWT tokens
access_token = security_manager.create_access_token(
    data={"sub": str(user.id)},
    expires_delta=timedelta(minutes=15)
)
refresh_token = security_manager.create_refresh_token(
    data={"sub": str(user.id)}
)

# 4. Update last_login timestamp
user.last_login = datetime.utcnow()
```

---

### 3. POST /api/v1/books/upload-url

**Amaç**: Presigned URL üretimi (Frontend doğrudan S3'e yükler)

**Request**:
```json
{
  "filename": "my-book.pdf",
  "file_size": 25000000,
  "title": "My Awesome Book"
}
```

**Response (200 OK)**:
```json
{
  "book_id": "uuid-here",
  "presigned_url": "https://s3.amazonaws.com/bucket/uploads/...?X-Amz-Signature=...",
  "s3_key": "uploads/user-uuid/book-uuid/my-book.pdf",
  "expires_in": 3600
}
```

**Validations**:
1. **File Extension**: `.pdf` değilse → 400 Bad Request
2. **File Size**:
   - Free: 50 MB'dan büyükse → 413 Payload Too Large
   - Pro: 200 MB'dan büyükse → 413 Payload Too Large
3. **OCR Quota**: 0 veya negatifse → 403 Forbidden

**İş Mantığı**:
```python
# 1. Validate extension
if not request.filename.lower().endswith(".pdf"):
    raise HTTPException(400, "Only PDF files allowed")

# 2. Validate size based on tier
if current_user.plan_type == "free" and file_size > 50MB:
    raise HTTPException(413, "Free tier max 50 MB")

# 3. Check quota
if current_user.ocr_quota_remaining <= 0:
    raise HTTPException(403, "Insufficient quota")

# 4. Create Book record with status=pending
book = Book(
    id=uuid.uuid4(),
    user_id=current_user.id,
    title=title,
    status=BookStatus.PENDING,
)
db.add(book)
db.commit()

# 5. Generate presigned URL
presigned_url = s3_storage.generate_presigned_url(
    s3_key="uploads/user-id/book-id/filename.pdf",
    expiration=3600
)
```

**Frontend Workflow**:
```javascript
// 1. Get presigned URL
const response = await fetch('/api/v1/books/upload-url', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer TOKEN' },
  body: JSON.stringify({ filename, file_size, title })
});
const { presigned_url, book_id } = await response.json();

// 2. Upload directly to S3 (bypasses our server)
await fetch(presigned_url, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': 'application/pdf' }
});

// 3. Trigger processing
await fetch(`/api/v1/books/process/${book_id}`, {
  method: 'POST',
  headers: { 'Authorization': 'Bearer TOKEN' }
});
```

---

### 4. POST /api/v1/books/process/{book_id}

**Amaç**: PDF işlemeyi tetikle (Celery task'ı başlat)

**Rate Limiting**: Dakikada maksimum 2 istek

**Request**: (Body yok)

**Response (200 OK)**:
```json
{
  "book_id": "uuid-here",
  "status": "processing",
  "task_id": "celery-task-uuid",
  "message": "PDF processing started"
}
```

**Validations**:
1. **Rate Limit**: Dakikada 2'den fazla → 429 Too Many Requests
2. **Book Exists**: Kitap var mı? → 404 Not Found
3. **Ownership**: Kullanıcı sahibi mi? → 403 Forbidden
4. **Status**: Zaten işleniyor mu? → 409 Conflict

**İş Mantığı**:
```python
# 1. Rate limiting (Redis)
rate_limit_key = f"user:{user.id}:process_pdf"
if not rate_limiter.is_allowed(rate_limit_key, max_requests=2, window_seconds=60):
    raise HTTPException(429, "Too many requests")

# 2. Fetch book
book = db.query(Book).filter(Book.id == book_id).first()
if not book:
    raise HTTPException(404, "Book not found")

# 3. Verify ownership
if book.user_id != current_user.id:
    raise HTTPException(403, "Not authorized")

# 4. Check status
if book.status in [BookStatus.PROCESSING, BookStatus.COMPLETED]:
    raise HTTPException(409, "Book already processing/completed")

# 5. Trigger Celery task
task = process_pdf_task.delay(
    book_id=book_id,
    s3_pdf_key=f"uploads/{user_id}/{book_id}/{filename}",
    user_id=str(user.id)
)
```

---

### 5. GET /api/v1/books/{book_id}/status

**Amaç**: İşleme durumunu ve ilerleme yüzdesini al

**KRITIK OPTIMIZASYON**: Redis'ten oku, DB'ye gitme!

**Response (200 OK)**:
```json
{
  "id": "uuid-here",
  "title": "My Book",
  "status": "processing",
  "progress_percentage": 45,
  "total_pages": 500,
  "processed_pages": 225,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**İş Mantığı**:
```python
# 1. Fetch book from DB (required once)
book = db.query(Book).filter(Book.id == book_id).first()

# 2. CRITICAL: Try Redis first (fast, non-blocking)
redis_progress = redis_client.get(f"book_progress:{book_id}")
if redis_progress:
    progress_data = json.loads(redis_progress)
    # Update progress from Redis
    book.progress_percentage = progress_data["progress_percentage"]
    book.processed_pages = progress_data["current_page"]
    # Return immediately (no DB write)
    return book

# 3. If Redis expired, use DB values (fallback)
return book
```

**Frontend Polling**:
```javascript
// Poll every 3 seconds
const pollStatus = async () => {
  const response = await fetch(`/api/v1/books/${bookId}/status`, {
    headers: { 'Authorization': 'Bearer TOKEN' }
  });
  const status = await response.json();
  
  console.log(`Progress: ${status.progress_percentage}%`);
  
  if (status.status === 'completed') {
    // Fetch content
    fetchContent();
  } else {
    // Poll again in 3 seconds
    setTimeout(pollStatus, 3000);
  }
};
```

---

### 6. GET /api/v1/books/{book_id}/content

**Amaç**: İşlenmiş kitap içeriğini al

**Ön Koşul**: `status == "completed"`

**Response (200 OK)**:
```json
{
  "id": "uuid-here",
  "title": "My Book",
  "status": "completed",
  "total_pages": 500,
  "pages": [
    {
      "page_number": 1,
      "text": "Chapter 1: Introduction...",
      "method": "direct",
      "confidence": 1.0
    },
    {
      "page_number": 2,
      "text": "OCR'd text from scanned page...",
      "method": "ocr",
      "confidence": 0.85
    }
  ],
  "summary": {
    "content_url": "s3://bucket/processed/user-id/book-id/content.json",
    "total_pages": 500,
    "processed_pages": 500
  }
}
```

**Validations**:
- Book exists?
- User owns it?
- Processing completed?

---

## Güvenlik Mekanizmaları

### 1. JWT Token Flow

```
Login
  ↓
JWT Token Created (15 min expiry)
  ↓
Frontend stores token in localStorage/sessionStorage
  ↓
Every request includes: Authorization: Bearer TOKEN
  ↓
get_current_user dependency verifies token
  ↓
If valid: Return User object
If invalid/expired: 401 Unauthorized
```

### 2. Password Hashing

```
Plain Password: "MyPassword123"
  ↓
bcrypt.hash() with salt rounds=12
  ↓
Hashed: "$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcg7b3XeKeUxWdeS86E36P4/KFm"
  ↓
Stored in DB (never store plain password!)
  ↓
On login: bcrypt.verify(plain, hashed) → True/False
```

### 3. Rate Limiting

```
User attempts to process PDF
  ↓
Redis key: "user:uuid:process_pdf"
  ↓
Increment counter (INCR)
  ↓
If counter > 2 in 60 seconds → 429 Too Many Requests
  ↓
After 60 seconds: Key expires, counter resets
```

## Celery Worker Concurrency Optimization

**Problem**: Tesseract OCR CPU'yu sömürür, 4 concurrent task = sistem çöker

**Çözüm**: `worker_concurrency=1`

```python
# app/core/celery_app.py
celery_app.conf.update(
    worker_concurrency=1,  # CRITICAL: Only 1 task at a time
    worker_max_tasks_per_child=1000,  # Restart after 1000 tasks
)
```

**Worker Başlatma**:
```bash
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency=1 \
  --max-tasks-per-child=1000
```

## Konfigürasyon Parametreleri

| Parameter | Değer | Açıklama |
|-----------|-------|----------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | JWT token geçerlilik süresi |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token geçerlilik süresi |
| `FREE_TIER_MAX_SIZE` | 50 MB | Ücretsiz kullanıcı max dosya boyutu |
| `PRO_TIER_MAX_SIZE` | 200 MB | Pro kullanıcı max dosya boyutu |
| `FREE_TIER_MONTHLY_QUOTA` | 50 | Ücretsiz kullanıcı aylık sayfa limiti |
| `RATE_LIMIT_PROCESS` | 2/min | İşlem tetikleme rate limit |

## Hata Kodları

| Kod | Açıklama |
|-----|----------|
| 400 | Invalid file extension, bad request |
| 401 | Invalid/expired JWT token |
| 403 | Insufficient quota, not authorized |
| 404 | Book/User not found |
| 409 | Book already processing/completed |
| 413 | File too large |
| 429 | Rate limit exceeded |
| 500 | Server error |

## Sonraki Adım: ADIM 4

Docker containerization ve production deployment configuration.
