# app/api/v1/endpoints/chat.py
import logging

from fastapi import APIRouter, Depends

from app.core.exceptions import AIServiceException, AITimeoutException
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.diagnosis import DiagnosisErrorResponse
from app.services.ai_provider import AIProvider, get_ai_provider

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/ask",
    response_model=ChatResponse,
    response_model_by_alias=True,
    summary="Grounded advisory answer about maintenance and platform policy",
    responses={
        503: {"model": DiagnosisErrorResponse, "description": "Engine unavailable"},
        504: {"model": DiagnosisErrorResponse, "description": "Engine timeout"},
    },
)
async def ask_question(
    request: ChatRequest,
    provider: AIProvider = Depends(get_ai_provider),
) -> ChatResponse:
    """Answer a general question from retrieved passages.

    Deliberately separate from diagnosis: this surface may answer maintenance
    and policy questions, but it never recommends a service or creates booking
    intent. Answers without retrieved grounding are refused, not improvised.
    """
    try:
        return await provider.answer(request)
    except AIServiceException:
        raise
    except TimeoutError as exc:
        raise AITimeoutException(internal_detail=repr(exc)) from exc
    except Exception as exc:
        logger.exception("chat_failed", extra={"request_id": request.request_id})
        raise AIServiceException(internal_detail=repr(exc)) from exc
