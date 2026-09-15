"""Pipeline behavior tests.

These cover the guarantees the business rules depend on: grounded output only,
no guessing under low confidence, and no free-text invention.
"""

import pytest

from app.schemas.chat import AnswerStatus, ChatRequest
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisStatus, UrgencyLevel
from app.services.pipeline.detector import Detection, StubDetector
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm, VlmVerdict


class _FixedVlm:
    def __init__(self, verdict: VlmVerdict) -> None:
        self._verdict = verdict

    async def assess(self, *args, **kwargs) -> VlmVerdict:
        return self._verdict

    async def answer(self, question: str, passages_vi: list[str]):
        return (passages_vi[0], 0.8) if passages_vi else ("", 0.0)


class _EmptyDetector:
    async def detect(self, image_ref: str) -> list[Detection]:
        return []


def _pipeline(detector=None, vlm=None) -> LocalPipeline:
    kb = get_knowledge_base()
    return LocalPipeline(
        detector=detector or StubDetector(kb=kb, device_type="electric_fan"),
        vlm=vlm or StubVlm(),
        retriever=Retriever(kb),
        kb=kb,
    )


@pytest.mark.asyncio
async def test_detected_device_narrows_faults_to_that_device():
    pipeline = _pipeline()
    response = await pipeline.diagnose(
        DiagnosisRequest(
            description="Quạt kêu cộc cộc và quay chậm",
            image_urls=["https://example.test/fan.jpg"],
        )
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
    response = await pipeline.diagnose(
        DiagnosisRequest(description="Quạt kêu cộc cộc", image_urls=["https://e.test/a.jpg"])
    )

    fault = kb.fault("FAN_WORN_BEARING")
    assert response.suspected_faults[0].name_vi == fault.name_vi
    assert response.recommended_services[0].service_code == fault.service_code
    assert response.price_estimate.min == fault.price_min


@pytest.mark.asyncio
async def test_fault_code_outside_catalog_is_dropped():
    """A model naming an unknown code must not reach the customer."""
    pipeline = _pipeline(
        vlm=_FixedVlm(VlmVerdict(fault_codes=["MADE_UP_CODE"], confidence=0.95))
    )
    response = await pipeline.diagnose(
        DiagnosisRequest(description="Quạt kêu cộc cộc", image_urls=["https://e.test/a.jpg"])
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
        DiagnosisRequest(description="hư rồi", image_urls=["https://e.test/a.jpg"])
    )

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.suspected_faults == []
