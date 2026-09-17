"""Two things the customer noticed before any test did.

Asked to book, the service diagnosed. Asked a follow-up, it forgot the question
it was following up on. Both are conversation failures rather than model
failures, so both are tested without a model.
"""

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisStatus
from app.services.pipeline.conversation import Conversation
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import (
    LocalPipeline,
    _recent_dialogue,
    _standalone_question,
)
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm


class _RecordingVlm(StubVlm):
    """Keeps whatever the pipeline handed it, so a test can look."""

    def __init__(self) -> None:
        self.history_vi = None

    async def answer(self, question, passages_vi, safety_vi=None, history_vi=""):
        self.history_vi = history_vi
        return (passages_vi[0] if passages_vi else safety_vi or "", 0.6)


class _EmptyDetector:
    async def detect(self, image):
        return []


def _pipeline(vlm=None) -> LocalPipeline:
    kb = get_knowledge_base()
    return LocalPipeline(
        detector=_EmptyDetector(),
        vlm=vlm or StubVlm(),
        retriever=Retriever(kb),
        kb=kb,
    )


@pytest.mark.asyncio
async def test_asking_to_book_gets_the_service_not_a_diagnosis():
    """Nobody asked what was wrong.

    "Bây giờ anh muốn đặt lịch vệ sinh máy lạnh" came back as two suspected
    faults, a price range and a list of things to try first — a wall of text
    between the customer and the thing they came to do.
    """
    response = await _pipeline().diagnose(
        DiagnosisRequest(description="bây giờ anh muốn đặt lịch vệ sinh máy lạnh")
    )

    assert response.status == DiagnosisStatus.OK
    assert response.suspected_faults == []
    assert response.recommended_services
    assert response.recommended_services[0].service_code == "VE_SINH_DIEU_HOA_1HP"
    assert "Đặt thợ ngay" in response.message_vi


@pytest.mark.asyncio
async def test_booking_a_repair_names_the_repair_service_not_the_clean():
    """A clean and a repair are different services at different prices."""
    response = await _pipeline().diagnose(
        DiagnosisRequest(description="cho mình đặt thợ sửa tủ lạnh")
    )

    assert response.recommended_services[0].service_code == "SUA_TU_LANH"


@pytest.mark.asyncio
async def test_booking_without_naming_an_appliance_still_asks():
    """"Cho mình đặt lịch" does not say what to book."""
    response = await _pipeline().diagnose(DiagnosisRequest(description="cho mình đặt lịch"))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION


def test_a_follow_up_is_resolved_against_the_message_before_it():
    kb = get_knowledge_base()
    chat = Conversation(session_id="s")
    chat.add("customer", "chi phí thay aptomat máy giặt")
    chat.add("assistant", "...")
    chat.add("customer", "giá bao nhiêu")

    resolved = _standalone_question("giá bao nhiêu", chat, kb)

    assert "aptomat" in resolved
    assert resolved.endswith("giá bao nhiêu")


def test_a_question_that_stands_alone_is_left_alone():
    kb = get_knowledge_base()
    chat = Conversation(session_id="s")
    chat.add("customer", "chi phí thay aptomat máy giặt")
    chat.add("customer", "máy lạnh nhà em không mát nữa")

    assert (
        _standalone_question("máy lạnh nhà em không mát nữa", chat, kb)
        == "máy lạnh nhà em không mát nữa"
    )


@pytest.mark.asyncio
async def test_the_model_is_shown_what_it_already_said():
    """Without the thread the assistant answers the same question twice."""
    vlm = _RecordingVlm()
    pipeline = _pipeline(vlm=vlm)

    first = await pipeline.answer(ChatRequest(question="bảo hành bao lâu"))
    await pipeline.answer(
        ChatRequest(question="còn máy lạnh thì sao", session_id=first.session_id)
    )

    assert vlm.history_vi
    assert "bảo hành bao lâu" in vlm.history_vi
    assert "Khách:" in vlm.history_vi


def test_the_dialogue_keeps_both_sides_in_order():
    chat = Conversation(session_id="s")
    chat.add("customer", "một")
    chat.add("assistant", "hai")
    chat.add("customer", "ba")

    assert _recent_dialogue(chat).splitlines() == ["Khách: một", "Bạn: hai", "Khách: ba"]


@pytest.mark.asyncio
async def test_a_question_still_offers_something_to_book():
    """Analyse and stop is how these conversations died.

    The customer read a question, answered it, was asked again, and never
    reached a booking. Asking and offering are not exclusive.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description="hư rồi"))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.recommended_services
    assert (
        response.recommended_services[0].service_code
        == "KIEM_TRA_CHAN_DOAN_THIET_BI"
    )


@pytest.mark.asyncio
async def test_an_unsettled_appliance_is_never_offered_a_specific_repair():
    """Two words naming nothing were offered a refrigerator repair.

    The shortlist retrieved for "hư rồi" happened to be all one device, and
    that is not evidence about the customer's appliance.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description="cứu em với"))

    codes = [s.service_code for s in response.recommended_services]
    assert codes == ["KIEM_TRA_CHAN_DOAN_THIET_BI"]


@pytest.mark.asyncio
async def test_a_chat_answer_about_an_appliance_can_be_booked():
    """The button lives in the chat frame, and the chat frame had no service."""
    response = await _pipeline().answer(
        ChatRequest(question="máy giặt kêu to khi vắt")
    )

    assert response.recommended_services
    assert response.recommended_services[0].service_code == "SUA_MAY_GIAT"


@pytest.mark.asyncio
async def test_a_policy_question_is_not_turned_into_a_sales_pitch():
    """Nobody books a technician after asking how long the warranty lasts."""
    response = await _pipeline().answer(ChatRequest(question="bảo hành bao lâu"))

    assert response.recommended_services == []


def test_the_grounded_answer_speaks_the_same_way_as_every_other():
    """The surface customers actually type into skipped the voice rules.

    "Bạn nên khoá van nước trước, sau đó tôi sẽ trả lời chi tiết hơn" — wrong
    pronoun on both sides of the sentence, from the one path that never ran
    them.
    """
    from app.services.pipeline.qwen_client import (
        _fix_pronouns,
        _fix_spelling,
        _sends_the_customer_away,
        _strip_apology,
    )

    raw = (
        "Xin lỗi, đây là chi phí thay Aptomat máy giặt. "
        "Bạn nên khoá van nước trước, sau đó tôi sẽ trả lời chi tiết hơn."
    )
    cleaned = _fix_spelling(_fix_pronouns(_strip_apology(raw)))

    assert not cleaned.startswith("Xin lỗi")
    assert "Bạn" not in cleaned
    assert "tôi" not in cleaned
    assert "Anh/chị" in cleaned
    assert _sends_the_customer_away("Bạn nên liên hệ với một chuyên gia về điện tử.")
