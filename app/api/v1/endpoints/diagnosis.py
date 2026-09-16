# app/api/v1/endpoints/diagnosis.py
import logging

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.config import settings
from app.core.exceptions import (
    AIServiceException,
    AITimeoutException,
    InvalidImageException,
)
from app.schemas.diagnosis import (
    DiagnosisErrorResponse,
    DiagnosisRequest,
    DiagnosisResponse,
)
from app.services.ai_provider import AIProvider, get_ai_provider
from app.services.pipeline.images import load_image

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analyze",
    response_model=DiagnosisResponse,
    response_model_by_alias=True,
    summary="Preliminary diagnosis from photo and description",
    responses={
        422: {"model": DiagnosisErrorResponse, "description": "Unusable input"},
        503: {"model": DiagnosisErrorResponse, "description": "Engine unavailable"},
        504: {"model": DiagnosisErrorResponse, "description": "Engine timeout"},
    },
)
async def analyze_issue(
    request: DiagnosisRequest,
    provider: AIProvider = Depends(get_ai_provider),
) -> DiagnosisResponse:
    """Run the diagnosis pipeline.

    Known failures are raised as typed exceptions and rendered by the global
    handler with a stable code. Unexpected failures are logged without request
    content and mapped to the same generic shape, so Backend always receives a
    response it can fall back from.
    """
    try:
        response = await provider.diagnose(request)
    except AIServiceException:
        raise
    except TimeoutError as exc:
        raise AITimeoutException(internal_detail=repr(exc)) from exc
    except Exception as exc:
        logger.exception("diagnosis_failed", extra={"request_id": request.request_id})
        raise AIServiceException(internal_detail=repr(exc)) from exc

    response.is_low_confidence = response.confidence < settings.AI_CONFIDENCE_THRESHOLD
    return response


@router.post(
    "/analyze-upload",
    response_model=DiagnosisResponse,
    response_model_by_alias=True,
    summary="Same diagnosis, multipart upload instead of base64",
    responses={
        422: {"model": DiagnosisErrorResponse, "description": "Unusable input"},
        503: {"model": DiagnosisErrorResponse, "description": "Engine unavailable"},
        504: {"model": DiagnosisErrorResponse, "description": "Engine timeout"},
    },
)
async def analyze_upload(
    description: str = Form(..., min_length=1, max_length=2000),
    # Field names are camelCase here as everywhere else on the wire. They were
    # snake_case, alone in the API, so a client that had read the JSON contract
    # sent sessionId and had it silently dropped: a form field that is not a
    # parameter is not an error, it is simply absent, and every message then
    # opened a new conversation with no sign of why.
    request_id: Optional[str] = Form(default=None, max_length=64, alias="requestId"),
    session_id: Optional[str] = Form(default=None, max_length=64, alias="sessionId"),
    category_hint: Optional[str] = Form(default=None, max_length=64, alias="categoryHint"),
    include_trace: bool = Form(default=False, alias="includeTrace"),
    files: Optional[List[UploadFile]] = File(default=None),
    provider: AIProvider = Depends(get_ai_provider),
) -> DiagnosisResponse:
    """Accept raw files rather than base64.

    Same pipeline and same response as `/analyze`; this form exists because
    base64 inflates a payload by a third, which matters for phone photos.
    Uploads are re-encoded here so both entry points converge on one request
    shape and one set of validation rules.
    """
    uploads = files or []
    if len(uploads) > settings.MAX_IMAGES_PER_REQUEST:
        raise InvalidImageException(
            internal_detail=f"{len(uploads)} files exceeds per-request limit"
        )

    images: List[str] = []
    for upload in uploads:
        raw = await upload.read()
        images.append(load_image(raw).to_base64())

    return await analyze_issue(
        request=DiagnosisRequest(
            request_id=request_id,
            session_id=session_id,
            include_trace=include_trace,
            description=description,
            images=images,
            category_hint=category_hint,
        ),
        provider=provider,
    )
