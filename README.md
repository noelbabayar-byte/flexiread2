# FlexiRead

FlexiRead, PDF dosyalarını yeniden akışlı (reflowable) metne dönüştüren modern bir SaaS uygulamasıdır. Backend tarafında FastAPI, SQLAlchemy, PostgreSQL, Redis, MinIO/S3 ve Celery kullanılır; frontend tarafında React, TypeScript, Vite ve Tailwind CSS yer alır.

## Teknoloji Yığını

| Katman | Teknolojiler |
|---|---|
| Backend API | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic v2 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Veritabanı | PostgreSQL 16, Alembic migration yönetimi |
| Cache ve Kuyruk | Redis 7, Celery |
| Dosya Depolama | MinIO / S3 uyumlu depolama |
| OCR ve PDF İşleme | Tesseract, PyMuPDF, Pillow |
| Test ve CI/CD | Pytest, pytest-cov, factory-boy, GitHub Actions |

## Hızlı Başlangıç

```bash
git clone https://github.com/noelbabayar-byte/flexiread.git
cd flexiread
cp .env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
```

API varsayılan olarak `http://localhost:8000` adresinde, frontend ise `http://localhost:5173` adresinde çalışır. API dokümantasyonu için Swagger UI `http://localhost:8000/docs`, ReDoc ise `http://localhost:8000/redoc` üzerinden erişilebilir.

## Veritabanı Migration Yönetimi

Proje artık Alembic ile sürümlenmiş migration yapısına sahiptir. İlk kurulumdan sonra migration çalıştırmak için aşağıdaki komut kullanılmalıdır.

```bash
alembic upgrade head
```

Docker içinde çalışırken eşdeğer komut şudur.

```bash
docker compose exec api alembic upgrade head
```

Yeni model değişiklikleri için önerilen akış aşağıdaki gibidir.

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Testler

Backend test altyapısı `tests/` dizini altında yapılandırılmıştır. Testler, PostgreSQL ve Redis servisleriyle izole çalışacak şekilde tasarlanmıştır.

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
pytest --cov=app --cov-report=html
```

| Test Dosyası | Kapsam |
|---|---|
| `tests/test_auth.py` | Kayıt, giriş, logout, refresh token ve JWT blacklist davranışı |
| `tests/test_users.py` | Kullanıcı profil ve quota endpoint'leri |
| `tests/test_books.py` | PDF upload URL ve kitap durum endpoint'leri |
| `tests/test_rate_limiter.py` | Redis tabanlı rate limiter davranışı |
| `tests/test_ocr.py` | PDF doğrudan metin çıkarımı ve işlem çıktısı |
| `tests/test_ocr_turkish.py` | Türkçe OCR karakter doğrulama ve config testi |
| `tests/test_s3.py` | S3/MinIO yardımcı sınıfı için mock AWS testleri |

## OCR Dil Desteği

FlexiRead, Türkçe ve İngilizce OCR desteği sunar.

### Desteklenen Diller
- Türkçe (`tesseract-ocr-tur`)
- İngilizce (Varsayılan)

### Yeni Dil Ekleme
Farklı diller eklemek için `Dockerfile` içindeki paket listesine ilgili Tesseract paketini eklemeniz yeterlidir:
```dockerfile
RUN apt-get install -y tesseract-ocr-<dil-kodu>
```

## API Versioning Stratejisi

Tüm public endpoint'ler `/api/v1` prefix'i altında yayınlanır. Geriye dönük uyumsuz değişiklikler gerektiğinde yeni endpoint seti `/api/v2` altında açılmalı, `/api/v1` ise belirlenmiş bir deprecation süresi boyunca korunmalıdır. Router agregasyonu `app/api/v1/api.py` içinde tutulur; uygulama giriş noktası da aynı endpoint setini `/api/v1` altında bağlar.

## Kimlik Doğrulama

Auth akışı JWT access token ve refresh token kullanır. Logout işlemi access token içindeki `jti` değerini Redis tabanlı blacklist'e ekler; kayıtlı blacklist anahtarları token süresi dolduğunda TTL ile otomatik silinir.

| Endpoint | Açıklama |
|---|---|
| `POST /api/v1/auth/register` | Yeni kullanıcı oluşturur |
| `POST /api/v1/auth/login` | Access ve refresh token üretir |
| `POST /api/v1/auth/logout` | Mevcut access token'ı revoke eder |
| `POST /api/v1/auth/refresh` | Refresh token ile yeni access token üretir |
| `GET /api/v1/users/me` | Aktif kullanıcı profilini döndürür |
| `GET /api/v1/users/quota` | Aktif kullanıcının OCR quota durumunu döndürür |
| `GET /api/v1/users/profile` | Detaylı kullanıcı profilini döndürür |

## CI/CD

GitHub Actions pipeline'ı `.github/workflows/ci.yml` dosyasında tanımlıdır. Her push ve pull request için PostgreSQL ve Redis servisleri ayağa kaldırılır, bağımlılıklar kurulur, Alembic migration'ları uygulanır, testler coverage raporuyla çalıştırılır, lint kontrolleri yürütülür ve Docker image build doğrulaması yapılır.

## Proje Yapısı

```text
app/
  api/v1/endpoints/    REST endpoint'leri
  core/                config, database, security, celery ve JWT blacklist
  models/              SQLAlchemy modelleri
  schemas/             Pydantic request/response modelleri
  utils/               OCR, S3 ve rate limiter yardımcıları
alembic/               Alembic migration ortamı ve sürümleri
tests/                 Unit ve integration testleri
.github/workflows/     CI/CD pipeline tanımları
frontend/              React okuyucu uygulaması
worker/                Celery task'ları
```

## Ortam Değişkenleri

`.env.example` dosyası yerel geliştirme için gerekli temel değişkenleri içerir. Production ortamında özellikle `JWT_SECRET_KEY`, veritabanı parolaları, Redis parolası ve S3 kimlik bilgileri güvenli secret yönetimiyle sağlanmalıdır.
