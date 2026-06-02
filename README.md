# 📖 FlexiRead - PDF to Reflowable Text SaaS

**Convert PDFs into beautifully reflowable text with OCR-powered processing, optimized for iPad and mobile reading experiences.**

---

## 🎯 Features

- **🔄 PDF to Reflowable Text**: Convert static PDFs into responsive, reflow-friendly text using hybrid OCR (PyMuPDF + Tesseract)
- **📱 iPad & Mobile Optimized**: Responsive design with custom fonts, themes, and virtual scrolling for smooth 60fps reading
- **🔐 JWT Authentication**: Secure user authentication with OAuth integration
- **💳 Freemium Model**: Subscription-based feature gating with monthly quotas
- **⚡ Asynchronous Processing**: Celery-based background tasks for heavy PDF operations
- **☁️ Cloud-Ready**: GitHub Codespaces support with Docker Compose for seamless deployment
- **🗄️ PostgreSQL & Redis**: Robust data persistence and real-time progress tracking
- **📦 S3/MinIO Storage**: Secure file storage with presigned URLs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + TS)                    │
│  - Reader Engine: Vanilla TS for 60fps scrolling            │
│  - Virtual Scrolling: Efficient rendering of large texts    │
│  - Theme/Font Customization: Dark mode, multiple fonts      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Backend (FastAPI + SQLAlchemy)                 │
│  - JWT Auth: Secure user sessions                           │
│  - tRPC Procedures: Type-safe API contracts                 │
│  - Rate Limiting: Redis-based request throttling            │
│  - Subscription Gating: Plan-based feature access           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Worker (Celery + Redis + Tesseract)               │
│  - Hybrid OCR: PyMuPDF + Tesseract for accuracy             │
│  - Memory-Efficient: Streaming page processing              │
│  - Progress Tracking: Real-time Redis updates               │
│  - S3 Storage: Processed content persistence                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│    Infrastructure (PostgreSQL, Redis, MinIO, Docker)        │
│  - PostgreSQL: User data, subscriptions, documents          │
│  - Redis: Caching, rate limiting, progress tracking         │
│  - MinIO: S3-compatible object storage                      │
│  - Docker Compose: Orchestration for all services           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: GitHub Codespaces (Recommended)

1. **Open in Codespaces:**
   ```bash
   # Click "Code" → "Codespaces" → "Create codespace on main"
   ```

2. **Wait for setup** (automatic via `.devcontainer/setup.sh`)

3. **Start services:**
   ```bash
   # Terminal 1: Backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # Terminal 2: Worker
   celery -A worker.tasks worker --loglevel=info

   # Terminal 3: Frontend
   cd frontend && npm run dev
   ```

4. **Access the app:**
   - Frontend: http://localhost:3000
   - Backend Docs: http://localhost:8000/docs
   - MinIO Console: http://localhost:9000

### Option 2: Local Development

**Prerequisites:**
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Tesseract OCR

**Setup:**

```bash
# Clone repository
git clone https://github.com/noelbabayar-byte/flexiread.git
cd flexiread

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Start Docker services
docker-compose up -d

# Run migrations
python -m alembic upgrade head

# Start backend
python -m uvicorn app.main:app --reload

# In another terminal: Start worker
celery -A worker.tasks worker --loglevel=info

# In another terminal: Start frontend
cd frontend && npm run dev
```

---

## 📁 Project Structure

```
flexiread/
├── .devcontainer/              # GitHub Codespaces configuration
│   ├── devcontainer.json       # Container setup
│   └── setup.sh                # Initialization script
├── app/                        # FastAPI backend
│   ├── core/                   # Config, database, security
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/
│   │   └── v1/endpoints/       # API routes (auth, books, users)
│   └── utils/                  # Helpers (S3, rate limiting)
├── worker/                     # Celery tasks
│   └── tasks.py                # PDF processing, OCR pipeline
├── frontend/                   # React + TypeScript
│   ├── src/
│   │   ├── reader/             # Reader Engine (Vanilla TS)
│   │   ├── components/         # React UI components
│   │   ├── pages/              # Page layouts
│   │   └── App.tsx             # Main app component
│   └── package.json
├── migrations/                 # Alembic database migrations
├── tests/                      # Unit & integration tests
├── docker-compose.yml          # Local development
├── docker-compose.codespaces.yml # Codespaces-optimized
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/flexiread

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3 / MinIO
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET_NAME=flexiread-dev
AWS_S3_REGION=us-east-1
AWS_S3_INTERNAL_ENDPOINT_URL=http://minio:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Tesseract
TESSERACT_CMD=/usr/bin/tesseract
```

---

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login with credentials
- `POST /api/v1/auth/logout` - Logout current user

### Books (PDF Management)
- `POST /api/v1/books/upload-url` - Get presigned S3 upload URL
- `POST /api/v1/books/process/{book_id}` - Trigger PDF processing
- `GET /api/v1/books/{book_id}/status` - Get processing status
- `GET /api/v1/books/{book_id}/content` - Get processed content

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/quota` - Get OCR quota info

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run Integration Tests
```bash
pytest tests/integration/ -v --tb=short
```

### Test E2E Flow
```bash
# See E2E_TEST_PROTOCOL.md for detailed instructions
bash tests/e2e_test.sh
```

---

## 🐳 Docker Services

### Start All Services
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f [service_name]
# Services: postgres, redis, minio, backend, worker, frontend
```

### Stop Services
```bash
docker-compose down
```

### Reset Database
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d
```

---

## 📚 Documentation

- **[Codespaces Quick Start](./CODESPACES_QUICKSTART.md)** - Get running in Codespaces in 5 minutes
- **[Docker Dev Guide](./DOCKER_DEV_GUIDE.md)** - Local development with Docker Compose
- **[E2E Test Protocol](./E2E_TEST_PROTOCOL.md)** - Complete testing workflow
- **[Architecture Explanation](./ADIM_2_EXPLANATION.md)** - Deep dive into system design
- **[Implementation Details](./ADIM_3_EXPLANATION.md)** - Technical implementation guide

---

## 🔐 Security

- **JWT Authentication**: Secure token-based auth with expiration
- **Rate Limiting**: Redis-based request throttling per user
- **Input Validation**: Pydantic schemas for all API inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Restricted to trusted origins
- **File Upload Validation**: File type and size restrictions

---

## 🚀 Deployment

### Deploy to Heroku
```bash
heroku create flexiread-app
git push heroku main
heroku run python -m alembic upgrade head
```

### Deploy to Railway
```bash
railway link
railway up
```

### Deploy to AWS
See [AWS Deployment Guide](./docs/AWS_DEPLOYMENT.md)

---

## 📈 Performance Optimizations

- **Virtual Scrolling**: Render only visible items in reader
- **Redis Caching**: Cache user data and processing status
- **Presigned URLs**: Direct S3 uploads without backend overhead
- **Streaming OCR**: Process PDFs page-by-page to reduce memory
- **Connection Pooling**: Reuse database connections
- **CDN Integration**: Serve static assets from CDN

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

---

## 💬 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@flexiread.app

---

## 🎉 Acknowledgments

- PyMuPDF for PDF processing
- Tesseract for OCR
- FastAPI for the backend framework
- React for the frontend
- Docker for containerization

---

**Built with ❤️ for better reading experiences**
