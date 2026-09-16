# app/api/v1/endpoints/chat.py
import logging

from fastapi import APIRouter, Depends

from app.core.exceptions import AIServiceException, AITimeoutException
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.diagnosis import DiagnosisErrorResponse
from app.services.ai_provider import AIProvider, get_ai_provider
from app.services.pipeline.acknowledgement import get_acknowledgements

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


@router.get(
    "/acknowledgements",
    summary="Lines the client shows the moment a message is sent",
)
async def acknowledgements() -> dict:
    """The whole set, for the client to cache and pick from locally.

    These are the sentences said before an answer exists, so that a customer
    who has just described a broken appliance is not left looking at an empty
    screen. They have to appear the instant Send is pressed, which is why the
    client picks one itself instead of asking for one per turn.

    `safetyFirst` is not politeness. When the message carries a cue of live
    electricity, escaping gas, or water reaching wiring, one of those lines
    replaces the pleasantry, because the instruction in it cannot wait for the
    pipeline to finish.
    """
    return get_acknowledgements().all_lines()
