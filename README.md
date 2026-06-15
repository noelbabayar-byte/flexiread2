# FlexiRead

FlexiRead, PDF dosyalarını yeniden akışlı (reflowable) metne dönüştüren bir okuma uygulamasıdır. PDF'i yüklersin, sistem metni (gerekirse OCR ile) çıkarır ve telefonda/bilgisayarda rahat okunabilen, yazı tipi ve boyutu ayarlanabilen bir okuyucuda gösterir.

---

## 🟢 En Kolay Yol: Kopyala-Yapıştır ile Çalıştır (5 dakika)

Kod bilmene gerek yok. Tek ihtiyacın **Docker Desktop**. Aşağıdaki adımları sırayla uygula.

### Adım 1 — Docker Desktop'ı kur

- Windows / Mac: https://www.docker.com/products/docker-desktop/ adresinden indir, kur ve **aç**.
- Linux: `sudo apt install docker.io docker-compose-plugin` (veya dağıtımının paket yöneticisi).

Kurduktan sonra Docker Desktop'ın açık ve "Running" durumunda olduğundan emin ol.

### Adım 2 — Projeyi indir

Bir terminal (Windows'ta PowerShell, Mac'te Terminal) aç ve şunu yapıştır:

```bash
git clone https://github.com/noelbabayar-byte/flexiread2.git
cd flexiread2
```

> Git yoksa: GitHub sayfasındaki yeşil **Code** düğmesi → **Download ZIP** ile indir, klasörü aç, içinde bir terminal aç.

### Adım 3 — Her şeyi tek komutla başlat

```bash
docker compose up -d --build
```

İlk seferde imajlar indirilip kurulduğu için **5-10 dakika** sürebilir. Sabret, normal bu.

### Adım 4 — Veritabanını hazırla (sadece ilk kurulumda bir kez)

Servislerin ayağa kalkması için ~30 saniye bekle, sonra:

```bash
docker compose exec api alembic upgrade head
```

### Adım 5 — Uygulamayı aç

Tarayıcında şu adrese git:

```
http://localhost:5173
```

Bitti. 🎉 "Kayıt ol" ile bir hesap oluştur, giriş yap, bir PDF yükle ve oku.

### Nasıl kullanılır?

1. **Kayıt ol** — e-posta + en az 8 karakter parola.
2. **PDF yükle** — kütüphane ekranındaki yükleme alanına tıkla, bir PDF seç.
3. **Bekle** — durum "İşleniyor" → "Hazır" olana kadar bekle (dosya boyutuna göre değişir).
4. **Oku** — "Oku" düğmesine bas. Sağ alttaki ⚙️ ile yazı tipi, boyut ve tema değiştir.

### Durdurmak / yeniden başlatmak

```bash
docker compose stop      # durdur (veriler kalır)
docker compose up -d     # tekrar başlat
```

### Sorun mu çıktı? (Sık karşılaşılanlar)

| Belirti | Çözüm |
|---|---|
| `port is already allocated` / port dolu | Aynı portu (5432, 6379, 5173, 8000, 9000) kullanan başka bir program/konteyner var. Onu kapat ya da `docker ps` ile çakışan konteyneri `docker stop <isim>` ile durdur. |
| Sayfa açılmıyor | Servisler henüz hazır değil. `docker compose ps` ile hepsinin `Up` olduğunu kontrol et, 1 dakika bekle. |
| Giriş/yükleme hata veriyor | Migration'ı çalıştırmayı unutmuş olabilirsin: `docker compose exec api alembic upgrade head`. |
| Tamamen sıfırla | `docker compose down -v` (TÜM verileri siler) sonra Adım 3'ten devam et. |
| Logları gör | `docker compose logs -f api` veya `docker compose logs -f worker`. |

---

## Teknoloji Yığını

| Katman | Teknolojiler |
|---|---|
| Backend API | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic v2 |
| Frontend | React 18, TypeScript, Vite |
| Veritabanı | PostgreSQL, Alembic migration yönetimi |
| Cache ve Kuyruk | Redis 7, Celery |
| Dosya Depolama | MinIO / S3 uyumlu depolama |
| OCR ve PDF İşleme | Tesseract, PyMuPDF, Pillow |
| Test ve CI/CD | Pytest, Vitest, GitHub Actions |

Varsayılan adresler:

| Servis | Adres |
|---|---|
| Frontend (okuyucu) | http://localhost:5173 |
| API | http://localhost:8000 |
| API dokümanı (Swagger) | http://localhost:8000/docs |
| MinIO konsolu | http://localhost:9001 (kullanıcı/parola: `minioadmin` / `minioadmin`) |

---

## GitHub Codespaces ile Çalıştırma

Bilgisayarına hiçbir şey kurmadan tarayıcıda çalıştırmak istersen `CODESPACES_QUICKSTART.md` dosyasını izle. Kısaca:

```bash
docker compose -f docker-compose.codespaces.yml up --build -d
docker compose -f docker-compose.codespaces.yml exec api alembic upgrade head
```

Codespaces, portları otomatik olarak `https://<codespace-adı>-5173.app.github.dev` gibi public URL'lere yönlendirir; backend bu URL'leri kendisi üretir.

---

## Geliştiriciler İçin

### Mimarinin özeti

- `docker compose up` komutu `docker-compose.yml` ve `docker-compose.override.yml` dosyalarını birleştirir; override geliştirme moduna (hot-reload, dev sunucusu) geçirir.
- Frontend tarayıcıdan doğrudan `http://localhost:8000` API'sine istek atar (CORS izinli).
- PDF yüklemesi presigned URL ile doğrudan MinIO'ya yapılır; işleme Celery worker'ında arka planda yürür ve ilerleme Redis üzerinden takip edilir.

### Backend testleri

Testler PostgreSQL ve Redis ile izole çalışır. En kolayı CI ile aynı ortamda (Docker) çalıştırmaktır:

```bash
docker compose exec api pytest -v
```

Yerelde (Python 3.12 önerilir):

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
pytest --cov=app --cov-report=html
```

### Frontend testleri

```bash
cd frontend
pnpm install
pnpm test       # Vitest birim testleri
pnpm build      # tip kontrolü + production build
```

### Migration üretme

```bash
alembic revision --autogenerate -m "değişikliği açıkla"
alembic upgrade head
```

---

## Kimlik Doğrulama API'si

JWT access + refresh token kullanılır. Logout, access token'ın `jti` değerini Redis tabanlı blacklist'e ekler; süresi dolan anahtarlar TTL ile otomatik silinir.

| Endpoint | Açıklama |
|---|---|
| `POST /api/v1/auth/register` | Yeni kullanıcı oluşturur |
| `POST /api/v1/auth/login` | Access ve refresh token üretir |
| `POST /api/v1/auth/logout` | Mevcut access token'ı revoke eder |
| `POST /api/v1/auth/refresh` | Refresh token ile yeni access token üretir |
| `GET /api/v1/users/me` | Aktif kullanıcı profilini döndürür |
| `GET /api/v1/users/quota` | OCR quota durumunu döndürür |
| `GET /api/v1/books/` | Kullanıcının kitaplarını listeler |
| `POST /api/v1/books/upload-url` | PDF için presigned upload URL üretir |
| `POST /api/v1/books/process/{id}` | Yüklenen PDF'in işlenmesini başlatır |
| `GET /api/v1/books/{id}/status` | İşleme durumunu döndürür |
| `GET /api/v1/books/{id}/content` | İşlenmiş içeriği döndürür |

---

## Proje Yapısı

```text
app/
  api/v1/endpoints/    REST endpoint'leri
  core/                config, database, security, celery, JWT blacklist
  models/              SQLAlchemy modelleri
  schemas/             Pydantic request/response modelleri
  utils/               OCR, S3 ve rate limiter yardımcıları
alembic/               Alembic migration ortamı ve sürümleri
tests/                 Unit ve integration testleri
frontend/              React okuyucu uygulaması
worker/                Celery task'ları
.github/workflows/     CI/CD pipeline tanımları
```

## Ortam Değişkenleri

Docker ile çalıştırırken tüm varsayılanlar `docker-compose.yml` içinde gömülüdür; `.env` zorunlu değildir. Özelleştirmek istersen `.env.example` dosyasını `.env` olarak kopyala. Production'da `JWT_SECRET_KEY`, veritabanı/Redis parolaları ve S3 kimlik bilgileri mutlaka güvenli secret yönetimiyle sağlanmalıdır.
