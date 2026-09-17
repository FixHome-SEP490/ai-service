# FixHome AI Service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import AIServiceException, ai_exception_handler
from app.api.v1.router import api_router
from app.services.pipeline.corpus import get_corpus


def _assert_the_corpus_shipped() -> None:
    """Refuse to start rather than answer from an empty corpus.

    The corpus reaches the rented box as files inside the image, and a build
    that leaves them out is invisible at runtime: retrieval returns nothing,
    every answer degrades into a clarifying question, the health check is green
    and the service looks like it is working. The same reasoning as the
    entrypoint refusing to start on a stub detector, which would have answered
    every photograph with the same appliance.

    Cheap to check and it only runs once, so it runs at startup rather than
    being something somebody remembers to verify after a deploy.
    """
    chunks = get_corpus()
    if len(chunks) < 1000:
        raise RuntimeError(
            f"Kho tri thức chỉ có {len(chunks)} đoạn, phải có vài nghìn. "
            "app/data/knowledge/ không vào được image — kiểm tra .dockerignore."
        )


_assert_the_corpus_shipped()

app = FastAPI(
    title="FixHome AI Service",
    description="AI-powered diagnosis service for home repair & maintenance",
    version="0.1.0",
)

# Exception handlers
app.add_exception_handler(AIServiceException, ai_exception_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint - returns basic operational status and provider without sensitive info"""
    return {
        "status": "ok",
        "service": "fixhome-ai-service",
        "engine": settings.AI_ENGINE,
        "version": "0.1.0",
    }
