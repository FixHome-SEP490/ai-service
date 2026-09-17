# FixHome AI Service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import AIServiceException, ai_exception_handler
from app.api.v1.router import api_router
from app.web.routes import router as web_router
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
# The page the service serves about itself, at /chat on the same port the API
# answers on. A rented box publishes one port, and "send the team a link" only
# works if the link is that one.
app.include_router(web_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Whether the two models are actually loaded, not merely whether it replies.

    "Is Qwen running, is YOLO running" took reading vLLM's throughput log and
    then sending photographs of five appliances to prove the detector was not a
    stub, because a service answering with a stub detector and a stub model
    looks exactly like a healthy one from here: 200, engine "local", no clue.

    Neither field asserts the model is any good. They say a real one is
    attached, which is the question that could not be answered from outside.
    """
    return {
        "status": "ok",
        "service": "fixhome-ai-service",
        "engine": settings.AI_ENGINE,
        "version": "0.1.0",
        "vlm": {
            "attached": bool(settings.VLM_BASE_URL),
            "model": settings.VLM_MODEL_NAME if settings.VLM_BASE_URL else None,
        },
        # Whether, not which. An older test forbids the word "weights" in this
        # response and it is right to: the endpoint is public on a rented box,
        # and a filename is a fact about the filesystem that a health check has
        # no reason to publish.
        "detector": {"attached": bool(settings.YOLO_WEIGHTS_PATH)},
        "knowledge": {"chunks": len(get_corpus())},
    }
