# app/api/v1/endpoints/diagnosis.py
import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.exceptions import AIServiceException, AITimeoutException
from app.schemas.diagnosis import (
    DiagnosisErrorResponse,
    DiagnosisRequest,
    DiagnosisResponse,
)
from app.services.ai_provider import AIProvider, get_ai_provider

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
