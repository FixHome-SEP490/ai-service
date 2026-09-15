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


class AnswerStatus(str, Enum):
    OK = "ok"
    OUT_OF_SCOPE = "out_of_scope"
    NO_GROUNDING = "no_grounding"


class Citation(BaseModel):
    doc_id: str
    title_vi: str
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChatRequest(BaseModel):
    request_id: Annotated[Optional[str], Field(max_length=64)] = None
    question: Annotated[str, Field(min_length=1, max_length=1000)]
    device_type: Annotated[Optional[str], Field(max_length=64)] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ChatResponse(BaseModel):
    request_id: Optional[str] = None
    status: AnswerStatus = AnswerStatus.OK
    answer_vi: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    disclaimer_vi: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
