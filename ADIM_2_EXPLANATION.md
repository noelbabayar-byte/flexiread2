# ADIM 2: Asenkron OCR ve Celery Task Kuyruğu - Detaylı Açıklama

## Genel Mimari

```
User Upload → FastAPI Endpoint → S3 Upload → Celery Task Queued → Worker Processes → S3 Result → DB Update
```

## Çözülen Teknik Zorluklar

### 1. Bellek Yönetimi (OOM Killer'dan Kaçış)

**Problem**: 500 sayfalık, 150 MB PDF'i RAM'e yüklemek sistem çökmesine neden olur.

**Çözüm**:
- PDF dosyası S3'ten **diske indirilir** (tempfile kullanarak)
- PyMuPDF (fitz) sayfa sayfa işlenir (tüm PDF açılmaz)
- Her sayfa işlendikten sonra bellek serbest bırakılır

```python
# app/utils/ocr_processor.py - Sayfa sayfa işleme
with PDFProcessor(pdf_path) as processor:
    for page_num in range(self.total_pages):
        page_data = self.process_page(page_num)  # Tek sayfa işlenir
        
        # Periyodik garbage collection
        if (page_num + 1) % 10 == 0:
            gc.collect()
```

### 2. Akıllı OCR Kararı Mekanizması

**Problem**: Tüm sayfaları OCR'a sokmak çok yavaş ve maliyetli.

**Çözüm**: Hybrid approach
1. Önce PyMuPDF ile direkt metin çıkarmaya çalış
2. Eğer metin yoksa (veya 50 karakterden az) → Tesseract OCR
3. Metin varsa → OCR'ı atla

```python
# app/utils/ocr_processor.py - process_page()
text = self.extract_text_from_page(page_num)

if len(text) >= self.MIN_TEXT_LENGTH:
    # Direkt metin var, OCR'a gerek yok
    page_data["method"] = "direct"
else:
    # Sayfada metin yok, OCR yap
    ocr_text = self.ocr_page(page_num)
    page_data["method"] = "ocr"
```

### 3. Hafıza Sızıntısı (Memory Leak)

**Problem**: Tesseract ve PIL uzun döngülerde belleği şişirir.

**Çözüm**:
- Context manager (`__enter__`, `__exit__`) ile otomatik cleanup
- Explicit `gc.collect()` çağrıları
- PIL Image nesneleri işlendikten sonra `del` ile silinir

```python
# app/utils/ocr_processor.py - Context Manager
def __exit__(self, exc_type, exc_val, exc_tb):
    if self.document:
        self.document.close()
    gc.collect()  # Force garbage collection

# OCR sırasında
img = Image.open(io.BytesIO(img_data))
text = pytesseract.image_to_string(img, ...)
del img  # Explicit deletion
gc.collect()
```

### 4. Hata Yönetimi (Resilience)

**Problem**: Bozuk PDF, şifreli dosya, veya Tesseract hatası sistem çökertebilir.

**Çözüm**: Comprehensive try/except ve graceful degradation

```python
# worker/tasks.py - process_pdf_task()
try:
    # PDF işle
    result, error = process_pdf_file(local_pdf_path, progress_callback)
    
    if error:
        raise RuntimeError(f"PDF processing failed: {error}")
    
    # Başarılı
    book.mark_completed(parsed_content_url)
    db.commit()

except Exception as e:
    # Hata durumunda
    book.mark_failed(str(e))
    db.commit()
    raise  # Celery retry logic'e devret
finally:
    # Her durumda cleanup
    if local_pdf_path and os.path.exists(local_pdf_path):
        os.unlink(local_pdf_path)
    db.close()
```

### 5. Sonuçların S3'e Taşınması

**Problem**: Devasa JSON verisini veritabanına gömmek = slow queries + storage waste

**Çözüm**: 
- Tüm işlenmiş içerik JSON olarak S3'e yüklenir
- Veritabanında sadece URL tutulur
- Kullanıcı ihtiyaç duyduğunda S3'ten presigned URL ile indirir

```python
# worker/tasks.py - process_pdf_task()
content_s3_key = f"processed/{user_id}/{book_id}/content.json"
parsed_content_url = s3_storage.upload_json(result, content_s3_key)

# DB'ye sadece URL yazılır
book.parsed_content_url = parsed_content_url
```

## İlerleme Yüzdesini Veritabanı Felci Olmadan Takip Etme

**Problem**: 500 sayfalık kitap → 500 DB UPDATE sorgusu = veritabanı I/O limiti aşılır

**Çözüm**: Batching + Redis caching

```
Sayfa 1-19:   Redis'te güncelle (hızlı, non-blocking)
Sayfa 20:     Redis + DATABASE'e güncelle (batch)
Sayfa 21-39:  Redis'te güncelle
Sayfa 40:     Redis + DATABASE'e güncelle (batch)
...
Sayfa 500:    Redis + DATABASE'e güncelle (final)
```

**Kod**:
```python
# worker/tasks.py - progress_callback_factory()
PROGRESS_BATCH_SIZE = 20

def callback(current_page: int, total_pages: int) -> None:
    # Her zaman Redis'e yaz (hızlı)
    update_progress_redis(book_id, current_page, total_pages)
    
    # Her 20 sayfada bir DB'ye yaz (batching)
    if current_page % PROGRESS_BATCH_SIZE == 0 or current_page == total_pages:
        batch_update_db_progress(db, book_id, current_page, total_pages)
```

**Sonuç**:
- 500 sayfalık kitap → 25 DB UPDATE (500 yerine)
- Frontend Redis'ten gerçek zamanlı ilerleme okur
- Veritabanı yükü 95% azalır

## Dosya Yapısı

```
flexiread-backend/
├── app/
│   ├── core/
│   │   ├── database.py          # PostgreSQL connection pooling
│   │   ├── config.py            # Pydantic Settings
│   │   └── celery_app.py        # Celery initialization
│   ├── models/
│   │   ├── base.py              # Base model
│   │   ├── user.py              # User model
│   │   └── book.py              # Book model
│   ├── schemas/
│   │   ├── user.py              # User Pydantic schemas
│   │   └── book.py              # Book Pydantic schemas
│   └── utils/
│       ├── s3_storage.py        # S3 file operations
│       └── ocr_processor.py     # PDF + OCR processing
├── worker/
│   ├── tasks.py                 # Celery tasks (process_pdf_task)
│   └── config.py                # Worker configuration
├── requirements.txt
└── .env.example
```

## Celery Task Lifecycle

```
1. FastAPI endpoint receives PDF upload
   ↓
2. PDF uploaded to S3
   ↓
3. Book record created with status="pending"
   ↓
4. Celery task queued: process_pdf_task(book_id, s3_key, user_id)
   ↓
5. Worker picks up task
   ├─ Download PDF from S3 to temp file
   ├─ Process pages (direct text or OCR)
   ├─ Update progress in Redis (fast)
   ├─ Batch update progress in DB (every 20 pages)
   ├─ Upload result JSON to S3
   ├─ Update Book record with status="completed"
   ├─ Consume user quota
   └─ Cleanup temp files
   ↓
6. Frontend polls GET /books/{book_id}/status
   ├─ Reads progress from Redis (real-time)
   └─ Or reads from DB (if Redis expired)
```

## Konfigürasyon Parametreleri

| Parameter | Değer | Açıklama |
|-----------|-------|----------|
| `pool_size` | 5 | MVP için yeterli connection pool |
| `max_overflow` | 5 | Acil durumlarda 5 ek connection |
| `PROGRESS_BATCH_SIZE` | 20 | Her 20 sayfada DB'ye yaz |
| `task_time_limit` | 3600s | Hard limit: 1 saat |
| `task_soft_time_limit` | 3300s | Soft limit: 55 dakika |
| `worker_prefetch_multiplier` | 1 | Bir seferde 1 task işle |
| `worker_max_tasks_per_child` | 1000 | 1000 task sonra worker restart |

## Monitoring ve Debugging

**Redis'ten ilerleme kontrol**:
```bash
redis-cli GET book_progress:book-uuid-here
# Output: {"current_page": 150, "total_pages": 500, "progress_percentage": 30}
```

**Celery task durumu**:
```bash
celery -A app.core.celery_app inspect active
celery -A app.core.celery_app inspect stats
```

**Worker log'ları**:
```bash
celery -A app.core.celery_app worker --loglevel=debug
```

## Sonraki Adım: ADIM 3

FastAPI endpoint'leri yazacağız:
- `POST /upload` - PDF yükleme
- `GET /books/{book_id}/status` - İşleme durumu
- `GET /books/{book_id}/content` - İşlenmiş içerik
