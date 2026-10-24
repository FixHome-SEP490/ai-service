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


class PastJob(BaseModel):
    """One earlier booking of the same customer. See `past_jobs`."""

    service_vi: Annotated[str, Field(min_length=1, max_length=120)]
    device_vi: Annotated[Optional[str], Field(max_length=80)] = None
    fault_vi: Annotated[Optional[str], Field(max_length=120)] = None
    """What the assistant suspected then, if the booking came from it. A guess
    at the time, so it goes to the technician as one and never to the customer."""
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    """The booked day in Vietnam, YYYY-MM-DD."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RecommendedService(BaseModel):
    service_code: str
    name_vi: str

    device_type: Optional[str] = None
    """The appliance it is for. Set when the reply covers more than one
    appliance, so a client booking them together knows which is which."""

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


class DeviceSuggestion(BaseModel):
    """One appliance of a reply that covers several (up to three).

    A customer can photograph three appliances, or name them in one message,
    and book them as one visit (Backend visit groups, at most three devices).
    Each gets the service to book it under and what is known about it so far.
    The appliance being talked through in the conversation is `is_primary`;
    the others carry what retrieval alone found in what was said about them,
    which is less than the primary's model-checked answer and labelled so."""

    device_type: str
    name_vi: str
    source: EvidenceSource = EvidenceSource.DESCRIPTION
    image_index: Optional[int] = Field(default=None, ge=0, le=2)
    """Which of the request's images it was seen in, from 0."""

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    """The detector's confidence when seen in a photograph, else 0."""

    is_primary: bool = False

    suspected_faults: List[SuspectedFault] = Field(default_factory=list)
    service: Optional[RecommendedService] = None
    """None when Backend does not sell a repair for it yet; `note_vi` says so."""

    variant_code: Optional[str] = None
    """Backend's fixed-price variant, when what was said settles it."""

    questions_vi: List[str] = Field(default_factory=list)
    """What to ask to settle the variant (mounting, horsepower, load...)."""

    price_estimate: Optional[PriceEstimate] = None
    description_vi: Optional[str] = None
    """What the customer said about this appliance, to prefill its booking."""

    note_vi: Optional[str] = None

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

    history: Annotated[
        List[Annotated[str, Field(min_length=1, max_length=2000)]],
        Field(max_length=20),
    ] = []
    """What the customer said earlier in this conversation, oldest first.

    Used only when `session_id` names a conversation this service no longer
    holds - it restarted, the session sat idle past the hour, or the store was
    full - so the customer's "mới vệ sinh rồi" from three messages ago is not
    lost with it. Ignored whenever the session is still held: the service's own
    memory is the record, and a client cannot rewrite it.

    Customer turns only, on purpose. The assistant's earlier answers are not
    accepted from the client, because whatever is replayed here is read as
    fact, and a reply the service never gave is not one."""

    past_jobs: Annotated[List[PastJob], Field(max_length=5)] = []
    """The customer's own earlier bookings, newest first, from the backend.

    Only for a signed-in customer, and only what tells a technician something:
    the service, the appliance, the day. No address, no technician, no money.
    When the appliance in this conversation is one they had repaired, the
    assistant says so once and the note reaches the technician; nothing else
    is done with it, and it is not kept beyond the conversation."""

    include_trace: bool = False
    """Ask for the stage-by-stage trace. For the admin dashboard, not customers."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ModelInfo(BaseModel):
    """What produced this answer, for the audit trail section 8.4 requires.

    Backend stores provider, model and version against every diagnosis so a
    complaint months later can be traced to the thing that made the claim.
    Without it a stored result says only "the AI said so", and the model it
    names will have been replaced by then.
    """

    detector: Optional[str] = None
    """Detector weights in use, or absent when running on the stub."""

    vlm: Optional[str] = None
    knowledge_base_version: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TraceStage(BaseModel):
    """What one stage did, for the operator watching rather than the customer.

    The pipeline is four stages and a failure in any of them shows up as the
    same thing from outside: a clarification request. Without a trace, "the AI
    asked a question again" could be the detector finding nothing, retrieval
    returning an empty shortlist, the model naming codes outside it, or the
    model server being unreachable. Those need four different fixes.
    """

    name: str
    """detector, retrieval, vlm or knowledge_base."""

    ms: int
    ok: bool
    summary_vi: str
    detail: dict = Field(default_factory=dict)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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
    message_vi: Optional[str] = None
    """The whole answer as one message, for a chat surface to send as-is.

    The structured fields stay exactly as they were and remain the record. This
    is the same content phrased as something a person would actually type,
    because a reply assembled from a template reads like one: the same shape,
    the same order and the same stock sentences for every customer.

    Absent when the model was unavailable or when it altered a figure, and the
    caller then formats the structured fields itself."""

    model_info: Optional[ModelInfo] = None

    trace: List[TraceStage] = Field(default_factory=list)
    """Empty unless the caller asked for it.

    Customer traffic should not pay to assemble it, and it carries the
    customer's own words, so it is opt-in per request rather than a setting
    somebody forgets is on."""

    notes_vi: List[str] = Field(default_factory=list)
    """What the conversation has established, in plain words: what the customer
    already tried or ruled out, what they suspect. For the booking summary the
    technician reads, so nobody asks the customer to tell it all again."""

    devices: List[DeviceSuggestion] = Field(default_factory=list, max_length=3)
    """Every appliance of this conversation when there is more than one, the
    primary first, at most three (a visit's limit). Empty for one appliance:
    the top-level fields already describe it. `recommended_services` then holds
    one service per appliance, in the same order."""

    disclaimer_vi: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiagnosisErrorResponse(BaseModel):
    """Every failure still tells Backend that manual booking may proceed."""

    code: AIErrorCode
    message: str
    fallback_allowed: bool = Field(default=True)
    suggested_action_vi: str = Field(default="Vui lòng chọn dịch vụ thủ công để tiếp tục đặt lịch.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
