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
    def __init__(self, verdict: VlmVerdict, general: str = "") -> None:
        self._verdict = verdict
        self._general = general

    async def assess(self, *args, **kwargs) -> VlmVerdict:
        self.last_kwargs = kwargs
        return self._verdict

    async def assess_context(self, *args, **kwargs) -> VlmVerdict:
        self.last_kwargs = kwargs
        return self._verdict

    async def narrate(self, facts_vi: str, allowed_numbers: list[str]) -> str:
        return ""

    async def answer(
        self, question: str, passages_vi: list[str], safety_vi=None, history_vi=""
    ):
        if safety_vi:
            return (safety_vi, 0.8)
        return (passages_vi[0], 0.8) if passages_vi else ("", 0.0)

    async def answer_generally(self, question: str, history_vi: str = "") -> str:
        return self._general


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

    # Every reported name comes from the catalogue, whichever fault leads. This
    # used to name FAN_WORN_BEARING and read the first entry, which stopped
    # holding when retrieval rather than the model began deciding the order —
    # and what the test is really for is that no Vietnamese is invented here.
    assert response.suspected_faults
    for suspected in response.suspected_faults:
        assert suspected.name_vi == kb.fault(suspected.fault_code).name_vi

    fault = kb.fault(response.suspected_faults[0].fault_code)
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
async def test_the_service_to_book_comes_from_the_labour_table_meanwhile():
    """Backend owns the service codes. It does not own the answer.

    Waiting for that catalogue meant answering "giờ tôi nên thuê dịch vụ nào"
    with nothing, in a conversation that had already named the fault. Every
    fault records the labour row its floor price came from, so the service is
    known; only Backend's code for it is not.
    """
    pipeline = _pipeline(
        vlm=_FixedVlm(VlmVerdict(fault_codes=["FAN_WORN_BEARING"], confidence=0.9))
    )
    response = await _after_the_either_or(pipeline, "Quạt kêu cộc cộc", [_png()])

    assert response.suspected_faults
    assert response.recommended_services
    assert response.recommended_services[0].name_vi


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
    # Present, but no longer first, and this case is why that trade-off is
    # written down rather than assumed away. "Dù mới vệ sinh" rules out a dirty
    # filter in so many words, and the lexical scorer ranks a dirty filter first
    # *because* "vệ sinh" is in the sentence — 0.75 against 0.58. The model reads
    # the exclusion and retrieval cannot, so here the model is right; across the
    # 464 diagnosis cases of the suite it was nineteen points worse than taking
    # the first retrieved fault. Both are reported, and retrieval leads.
    codes = [f.fault_code for f in response.suspected_faults]
    assert "AC_LOW_REFRIGERANT" in codes, codes


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
async def test_a_question_outside_the_trade_is_refused_without_asking_the_model():
    """The model answers questions about anything if you let it.

    Asked "bitcoin giá bao nhiêu" it explained cryptocurrency exchanges, in the
    voice of a repair company. The gate is ours, and it fails closed.
    """
    pipeline = _pipeline(vlm=_FixedVlm(VlmVerdict(), general=""))
    response = await pipeline.answer(ChatRequest(question="zzzz qqqq"))

    assert response.status == AnswerStatus.NO_GROUNDING
    assert response.citations == []


@pytest.mark.asyncio
async def test_a_question_the_tables_miss_is_still_answered():
    """Refusing everything ungrounded made every customer get one sentence.

    General repair knowledge is not a fact anybody owns. It comes back marked
    as uncited, because an answer with citations and one without are not the
    same thing to a caller.
    """
    pipeline = _pipeline(
        vlm=_FixedVlm(
            VlmVerdict(),
            general="Dàn lạnh bám tuyết thường do thiếu gas hoặc lọc gió quá bẩn.",
        )
    )
    # In the trade, so the model is asked; no policy passage covers it.
    response = await pipeline.answer(
        ChatRequest(question="thiết bị zzzz qqqq wwww bị làm sao")
    )

    assert response.status == AnswerStatus.GENERAL_KNOWLEDGE
    assert response.citations == []
    assert "bám tuyết" in response.answer_vi


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
