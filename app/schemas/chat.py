# app/schemas/chat.py
"""Advisory Q&A contract.

Separate surface from diagnosis on purpose: this one may answer general
maintenance and platform-policy questions, but it never produces a booking
recommendation and its answers must be grounded in retrieved passages.
"""

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.diagnosis import RecommendedService


class AnswerStatus(str, Enum):
    OK = "ok"
    OUT_OF_SCOPE = "out_of_scope"
    GENERAL_KNOWLEDGE = "general_knowledge"
    """Answered from the model's trade knowledge, with nothing cited.

    Distinct from `ok` on purpose. An answer with citations traces to a
    document somebody owns; this one traces to a model, and a client showing
    them identically has thrown away the difference."""

    NO_GROUNDING = "no_grounding"


class Citation(BaseModel):
    doc_id: str
    title_vi: str
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChatRequest(BaseModel):
    request_id: Annotated[Optional[str], Field(max_length=64)] = None
    session_id: Annotated[Optional[str], Field(max_length=64)] = None
    """Ties this message to the ones before it.

    Omitted, every message is a stranger: the device identified from an earlier
    photograph is forgotten, and the answer to a question we just asked arrives
    with nothing to attach it to. The response returns the id to use next."""

    question: Annotated[str, Field(min_length=1, max_length=1000)]
    device_type: Annotated[Optional[str], Field(max_length=64)] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ChatResponse(BaseModel):
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    """Send this back on the next message to continue the same conversation."""

    status: AnswerStatus = AnswerStatus.OK
    answer_vi: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    recommended_services: List[RecommendedService] = Field(default_factory=list)
    """What the customer could book, if anything fits what they asked.

    The diagnosis surface has carried this from the start and this one did not,
    which put the "Đặt thợ ngay" button on the wrong half of the conversation:
    the button lives in the chat frame, and the chat frame was the one surface
    that never said which service to book. Empty is a real answer — nobody
    books a technician after asking how long the warranty lasts.
    """

    disclaimer_vi: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
