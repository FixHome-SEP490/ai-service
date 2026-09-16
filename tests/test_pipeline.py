"""Pipeline behavior tests.

These cover the guarantees the business rules depend on: grounded output only,
no guessing under low confidence, and no free-text invention.
"""

import base64
import io

import pytest
from PIL import Image

from app.schemas.chat import AnswerStatus, ChatRequest
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisStatus, UrgencyLevel
from app.services.pipeline.detector import Detection, StubDetector
from app.services.pipeline.images import ImagePayload
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm, VlmVerdict


class _FixedVlm:
    def __init__(self, verdict: VlmVerdict) -> None:
        self._verdict = verdict

    async def assess(self, *args, **kwargs) -> VlmVerdict:
        self.last_kwargs = kwargs
        return self._verdict

    async def answer(self, question: str, passages_vi: list[str]):
        return (passages_vi[0], 0.8) if passages_vi else ("", 0.0)


class _EmptyDetector:
    async def detect(self, image: ImagePayload) -> list[Detection]:
        return []


def _png(width: int = 64, height: int = 48) -> str:
    """A real in-memory PNG, base64 encoded the way a client would send one."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 120, 120)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _pipeline(detector=None, vlm=None) -> LocalPipeline:
    kb = get_knowledge_base()
    return LocalPipeline(
        detector=detector or StubDetector(kb=kb, device_type="electric_fan"),
        vlm=vlm or StubVlm(),
        retriever=Retriever(kb),
        kb=kb,
    )


async def _after_the_either_or(pipeline, description, images=None):
    """Run the turn that asks which appliance it is, then answer it.

    A fan photograph is one of the pairs the detector cannot separate — a
    ceiling fan and a standing fan have different faults and different labour
    prices — so the first turn asks where it is mounted. These tests are about
    what happens once that is settled.
    """
    first = await pipeline.diagnose(
        DiagnosisRequest(description=description, images=images or [])
    )
    assert first.status == DiagnosisStatus.NEEDS_CLARIFICATION
    return await pipeline.diagnose(
        DiagnosisRequest(
            description="quạt đứng dưới sàn ạ", session_id=first.session_id
        )
    )


@pytest.mark.asyncio
async def test_detected_device_narrows_faults_to_that_device():
    pipeline = _pipeline()
    response = await _after_the_either_or(
        pipeline, "Quạt kêu cộc cộc và quay chậm", [_png()]
    )

    assert response.status == DiagnosisStatus.OK
    assert response.device is not None
    assert response.device.device_type == "electric_fan"
    assert all(f.fault_code.startswith("FAN_") for f in response.suspected_faults)


@pytest.mark.asyncio
async def test_vietnamese_content_comes_from_knowledge_base():
    kb = get_knowledge_base()
    pipeline = _pipeline(
        vlm=_FixedVlm(VlmVerdict(fault_codes=["FAN_WORN_BEARING"], confidence=0.9))
    )
    response = await _after_the_either_or(pipeline, "Quạt kêu cộc cộc", [_png()])

    fault = kb.fault("FAN_WORN_BEARING")
    assert response.suspected_faults[0].name_vi == fault.name_vi
    assert response.price_estimate.min == fault.price_min
    if fault.requires_assessment:
        # No labour row covers re-oiling a fan bearing and no part stands in for
        # it, so the tables can offer a floor and nothing above it. Quoting the
        # inspection fee as the whole job would be the wrong kind of precise.
        assert response.price_estimate.max is None
        assert response.price_estimate.requires_assessment
    else:
        assert response.price_estimate.max == fault.price_max
    assert response.urgency == UrgencyLevel(fault.urgency)


@pytest.mark.asyncio
async def test_services_stay_empty_until_backend_supplies_a_mapping():
    """Service codes are Backend's to define; an empty mapping is not an error."""
    pipeline = _pipeline(
        vlm=_FixedVlm(VlmVerdict(fault_codes=["FAN_WORN_BEARING"], confidence=0.9))
    )
    response = await _after_the_either_or(pipeline, "Quạt kêu cộc cộc", [_png()])

    assert response.suspected_faults
    assert response.recommended_services == []


@pytest.mark.asyncio
async def test_fault_code_outside_catalog_is_dropped():
    """A model naming an unknown code must not reach the customer."""
    pipeline = _pipeline(
        vlm=_FixedVlm(VlmVerdict(fault_codes=["MADE_UP_CODE"], confidence=0.95))
    )
    response = await pipeline.diagnose(
        DiagnosisRequest(description="Quạt kêu cộc cộc", images=[_png()])
    )

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.suspected_faults == []


@pytest.mark.asyncio
async def test_low_confidence_asks_instead_of_guessing():
    pipeline = _pipeline(vlm=_FixedVlm(VlmVerdict(fault_codes=[], confidence=0.1)))
    response = await pipeline.diagnose(DiagnosisRequest(description="hư rồi"))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.is_low_confidence is True
    assert response.clarification is not None
    assert response.clarification.questions_vi
    assert response.clarification.service_group_codes


@pytest.mark.asyncio
async def test_text_only_request_still_works_without_detector_signal():
    pipeline = _pipeline(
        detector=_EmptyDetector(),
        vlm=_FixedVlm(VlmVerdict(fault_codes=["AC_LOW_REFRIGERANT"], confidence=0.85)),
    )
    response = await pipeline.diagnose(
        DiagnosisRequest(description="Máy lạnh không mát dù mới vệ sinh")
    )

    assert response.status == DiagnosisStatus.OK
    assert response.device is None
    assert response.suspected_faults[0].fault_code == "AC_LOW_REFRIGERANT"


@pytest.mark.asyncio
async def test_urgency_takes_the_highest_matched_fault():
    pipeline = _pipeline(
        detector=_EmptyDetector(),
        vlm=_FixedVlm(
            VlmVerdict(
                fault_codes=["AC_DIRTY_COIL", "OUTLET_SHORT_CIRCUIT"], confidence=0.9
            )
        ),
    )
    response = await pipeline.diagnose(DiagnosisRequest(description="cháy khét"))

    assert response.urgency == UrgencyLevel.HIGH


@pytest.mark.asyncio
async def test_chat_answer_is_cited():
    pipeline = _pipeline(vlm=_FixedVlm(VlmVerdict()))
    response = await pipeline.answer(
        ChatRequest(question="Bao lâu nên vệ sinh máy lạnh một lần?")
    )

    assert response.status == AnswerStatus.OK
    assert response.citations
    assert response.citations[0].doc_id


@pytest.mark.asyncio
async def test_chat_refuses_when_nothing_retrieved():
    pipeline = _pipeline(vlm=_FixedVlm(VlmVerdict()))
    response = await pipeline.answer(ChatRequest(question="zzzz qqqq"))

    assert response.status == AnswerStatus.NO_GROUNDING
    assert response.citations == []


@pytest.mark.asyncio
async def test_vague_description_does_not_produce_a_confident_guess():
    """A detected device plus an uninformative description must still ask."""
    pipeline = _pipeline()
    response = await pipeline.diagnose(
        DiagnosisRequest(description="hư rồi", images=[_png()])
    )

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.suspected_faults == []


@pytest.mark.asyncio
async def test_out_of_scope_question_is_refused_by_retrieval_alone():
    """The floor, not the model, is what stops an invented answer.

    Lexical overlap scores every question against every passage, so a question
    about the weather still matches the air-conditioner policy on a shared
    word. Without the floor the model would be the only thing standing between
    a customer and a confident fabrication.
    """
    pipeline = _pipeline(vlm=_FixedVlm(VlmVerdict()))
    response = await pipeline.answer(ChatRequest(question="Thời tiết Sài Gòn ngày mai thế nào?"))

    assert response.status == AnswerStatus.NO_GROUNDING
    assert response.citations == []
