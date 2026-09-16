# app/schemas/diagnosis.py
"""Backend-facing diagnosis contract.

Field names are snake_case in Python and camelCase on the wire via aliases.
Any change here is a cross-repository API change (Backend, Mobile, Docs).

Images are sent inline by the caller, base64 in JSON or multipart upload. The
service never dereferences a URL, which keeps it free of SSRF exposure.
"""

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DiagnosisStatus(str, Enum):
    OK = "ok"
    NEEDS_CLARIFICATION = "needs_clarification"


class EvidenceSource(str, Enum):
    """Which stage produced a conclusion, so clients can weight it honestly."""

    IMAGE = "image"
    DESCRIPTION = "description"
    KNOWLEDGE_BASE = "knowledge_base"


class Engine(str, Enum):
    LOCAL_PIPELINE = "local_pipeline"
    KEYWORD_FALLBACK = "keyword_fallback"
    MOCK = "mock"


class AIErrorCode(str, Enum):
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AI_TIMEOUT = "AI_TIMEOUT"
    INVALID_IMAGE = "INVALID_IMAGE"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    IMAGE_FETCH_FAILED = "IMAGE_FETCH_FAILED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    DETECTOR_ERROR = "DETECTOR_ERROR"
    VLM_ERROR = "VLM_ERROR"
    KNOWLEDGE_BASE_ERROR = "KNOWLEDGE_BASE_ERROR"


class BoundingBox(BaseModel):
    """Detector crop in absolute pixels of the source image."""

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class DetectedDevice(BaseModel):
    device_type: str
    name_vi: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: EvidenceSource = EvidenceSource.IMAGE
    bounding_box: Optional[BoundingBox] = Field(default=None)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class VisibleCondition(BaseModel):
    """Surface damage the VLM reads off the cropped device region."""

    code: str
    name_vi: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: EvidenceSource = EvidenceSource.IMAGE

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SuspectedFault(BaseModel):
    fault_code: str
    name_vi: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: EvidenceSource = EvidenceSource.DESCRIPTION

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RecommendedService(BaseModel):
    service_code: str
    name_vi: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PriceEstimate(BaseModel):
    """Indicative only. Never a quotation and never a customer approval."""

    min: int = Field(ge=0)

    max: Optional[int] = Field(default=None, ge=0)
    """Absent when no ceiling can be put on the job.

    Either the cost is open-ended — a cracked TV panel, a holed water heater —
    or the price tables cover no labour for the work and no part stands in for
    it. Zero was the obvious sentinel and the wrong one: it cannot be told apart
    from a job that costs nothing, and it breaks the ordering rule below.
    Callers should show `requires_assessment` wording rather than a number."""

    currency: str = "VND"

    requires_assessment: bool = False
    """A technician has to look before this can be priced at all."""

    @model_validator(mode="after")
    def check_order(self) -> "PriceEstimate":
        if self.max is not None and self.min > self.max:
            raise ValueError("price_estimate.min must not exceed price_estimate.max")
        if self.max is None and not self.requires_assessment:
            raise ValueError(
                "price_estimate.max may only be omitted when requires_assessment is set"
            )
        return self

    # Every other model carries this; PriceEstimate did not need it while all
    # three of its fields were single words. The new one is two, and without the
    # generator it went out as requires_assessment among camelCase neighbours,
    # which a caller reads as absent rather than as a naming slip.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Clarification(BaseModel):
    """Returned instead of a guess when confidence is too low."""

    questions_vi: List[str] = Field(default_factory=list)
    service_group_codes: List[str] = Field(default_factory=list)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiagnosisRequest(BaseModel):
    request_id: Annotated[Optional[str], Field(max_length=64)] = None
    session_id: Annotated[Optional[str], Field(max_length=64)] = None
    """Ties this message to the ones before it.

    Omitted, every message is a stranger: the device identified from an earlier
    photograph is forgotten, and the answer to a question we just asked arrives
    with nothing to attach it to. The response returns the id to use next."""

    description: Annotated[str, Field(min_length=1, max_length=2000)]
    images: Annotated[
        List[str],
        Field(max_length=3, description="Inline images, base64 or data URI."),
    ] = []
    category_hint: Annotated[Optional[str], Field(max_length=64)] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class DiagnosisResponse(BaseModel):
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    """Send this back on the next message to continue the same conversation."""

    status: DiagnosisStatus = DiagnosisStatus.OK
    engine: Engine = Engine.LOCAL_PIPELINE
    device: Optional[DetectedDevice] = None
    visible_conditions: List[VisibleCondition] = Field(default_factory=list)
    suspected_faults: List[SuspectedFault] = Field(default_factory=list)
    recommended_services: List[RecommendedService] = Field(default_factory=list)
    suggested_actions_vi: List[str] = Field(default_factory=list)
    price_estimate: Optional[PriceEstimate] = None
    urgency: UrgencyLevel = UrgencyLevel.LOW
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_low_confidence: bool = Field(default=False)
    clarification: Optional[Clarification] = None
    disclaimer_vi: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiagnosisErrorResponse(BaseModel):
    """Every failure still tells Backend that manual booking may proceed."""

    code: AIErrorCode
    message: str
    fallback_allowed: bool = Field(default=True)
    suggested_action_vi: str = Field(default="Vui lòng chọn dịch vụ thủ công để tiếp tục đặt lịch.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
