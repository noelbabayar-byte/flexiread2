"""
Main FastAPI application entry point.
Registers all routers and configures middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import auth, books, users
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FlexiRead API",
    description="PDF-to-Reflowable-Text SaaS Backend",
    version="1.0.0",
)

# Validate CORS security configuration at import/boot time
allowed_origins = settings.get_allowed_origins_list()
if settings.is_production():
    if not allowed_origins:
        logger.critical(
            "CORS Security Failure: ALLOWED_ORIGINS must be set in production."
        )
        raise RuntimeError("ALLOWED_ORIGINS must be set in production")
    if "*" in allowed_origins:
        logger.critical(
            "CORS Security Failure: Wildcard '*' origins are strictly prohibited in production."
        )
        raise RuntimeError("Wildcard CORS origins are not allowed in production")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Register routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(books.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "flexiread-api"}


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "FlexiRead API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=4 if not settings.DEBUG else 1,
    )
