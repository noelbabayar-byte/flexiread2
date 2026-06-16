"""
Main FastAPI application entry point.
Registers all routers and configures middleware.
"""

from fastapi import FastAPI
from starlette.requests import Request

# PATCH: Increase body size limit for PDF uploads (default 1MB too small)
Request.max_body_size = 100 * 1024 * 1024  # 100MB




from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlexiRead API",
    description="PDF-to-Reflowable-Text SaaS Backend",
    version="1.0.0",
)

allowed_origins = settings.get_allowed_origins_list()

if settings.is_production():
    if not allowed_origins:
        logger.critical(
            "CORS Security Failure: ALLOWED_ORIGINS must be set in production."
        )
        raise RuntimeError("ALLOWED_ORIGINS must be set in production")
    if "*" in allowed_origins:
        logger.critical(
            "CORS Security Failure: Wildcard '*' origins are prohibited in production."
        )
        raise RuntimeError("Wildcard CORS origins are not allowed in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "flexiread-api"}


@app.get("/")
def root():
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
