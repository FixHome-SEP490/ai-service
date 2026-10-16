"""Found on the served model on 16/10 evening, and in the address check that came with them.

1. "hôi mùi gas" on its own: urgency was HIGH, but the reply was a question
   about the stove and no step to take. Safety steps now lead any urgent reply
   that had none.
2. "em đang đứng ngoài cửa không vào nhà được" was refused as off-topic though
   it is a smart-lock symptom word for word. A knowledge-base symptom is in
   the trade, and one that fits a single appliance names it.
3. "chỗ rửa bát bị rò nước" went to the dishwasher; it is the sink.
4. "nhà có mùi gas" called the customer "cô": folded, "có" and "cô" are the
   same word. With accents typed, the accents decide.
"""

from __future__ import annotations

import asyncio

import pytest

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import dialogue_state as ds
from app.services.pipeline.conversation import ConversationStore
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


class _NoDetector:
    async def detect(self, image):
        return []


def _diagnose(kb, text):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    pipeline._conversations = ConversationStore()

    async def run():
        reply = await pipeline.diagnose(DiagnosisRequest(description=text))
        return reply, pipeline._conversations.get_or_create(reply.session_id)

    return asyncio.run(run())


@pytest.mark.parametrize("text", ["hôi mùi gas", "nhà có mùi gas", "ngửi thấy mùi gas", "hoi mui gas"])
def test_a_gas_smell_gets_the_safety_steps_first(kb, text):
    reply, _ = _diagnose(kb, text)
    assert reply.urgency.value == "HIGH"
    assert any("khoá van" in a.lower() or "khóa van" in a.lower() for a in reply.suggested_actions_vi)


@pytest.mark.parametrize("text", ["hôi mùi gas", "nhà có mùi gas"])
def test_a_question_back_does_not_come_before_the_steps(kb, text):
    reply, _ = _diagnose(kb, text)
    steps = " ".join(reply.suggested_actions_vi).lower()
    assert "van bình gas" in steps
    if reply.clarification is not None:
        # Asking back is allowed only after the steps have been said.
        assert reply.message_vi and reply.message_vi.startswith("Dạ đây là dấu hiệu nguy hiểm")


def test_an_urgent_reply_that_already_had_steps_is_not_doubled(kb):
    reply, _ = _diagnose(kb, "bếp gas nhà em có mùi gas")
    assert not (reply.message_vi or "").startswith("Dạ đây là dấu hiệu nguy hiểm")
    assert reply.suggested_actions_vi


def test_a_lockout_is_in_the_trade_and_names_the_smart_lock(kb):
    reply, chat = _diagnose(kb, "em đang đứng ngoài cửa không vào nhà được")
    assert reply.status.value == "ok"
    assert chat.device_type == "smart_lock"
    assert reply.suspected_faults[0].fault_code == "LOCK_LOCKED_OUT"


def test_a_phrase_that_fits_several_appliances_names_none(kb):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    owners = [o for p, o in pipeline._symptom_index().items() if len(o) > 1 and len(p.split()) >= 4]
    if not owners:
        pytest.skip("no shared four-word symptom in this knowledge base")
    phrase = next(p for p, o in pipeline._symptom_index().items() if len(o) > 1 and len(p.split()) >= 4)
    assert pipeline._device_from_symptom(phrase) is None


@pytest.mark.parametrize("text", ["chỗ rửa bát bị rò nước", "chậu rửa chén bị nghẹt", "bồn rửa bát bốc mùi"])
def test_the_place_you_wash_dishes_is_the_sink(kb, text):
    _, chat = _diagnose(kb, text)
    assert chat.device_type == "sink"


def test_the_dishwasher_is_still_the_dishwasher(kb):
    _, chat = _diagnose(kb, "máy rửa bát không xả nước")
    assert chat.device_type == "dishwasher"


@pytest.mark.parametrize(
    "text, address",
    [
        ("nhà có mùi gas", None),
        ("có hỏi được không", None),
        ("nha co may lanh hong", None),
        ("nhà cô máy lạnh hư", "cô"),
        ("cô hỏi chút, máy giặt kêu", "cô"),
        ("Cháu ơi, tủ lạnh nhà bác không lạnh", "bác"),
        ("nha bac may giat hu", "bác"),
        ("ông muốn hỏi bếp gas", "ông"),
        ("chú đang ở nhà, ổ cắm cháy", "chú"),
        ("bà nhờ cháu xem tivi", "bà"),
    ],
)
def test_how_the_customer_names_themself(text, address):
    assert ds.mood_of(text)[1] == address


def test_the_gas_reply_keeps_anh_chi_when_nobody_said_co(kb):
    reply, _ = _diagnose(kb, "nhà có mùi gas")
    assert "cô" not in (reply.message_vi or "").split()


# 5 ------------------------------------------- two words, one clear fault


@pytest.mark.parametrize(
    "text, fault",
    [("lavabo bị tắc", "SINK_CLOGGED"), ("ổ cắm không lên", "OUTLET_NO_POWER"), ("tivi bị lag", "TV_MAIN_BOARD")],
)
def test_two_words_with_one_clear_fault_are_answered(kb, text, fault):
    reply, _ = _diagnose(kb, text)
    assert reply.status.value == "ok"
    assert reply.suspected_faults[0].fault_code == fault


@pytest.mark.parametrize("text", ["tivi bị đơ", "máy lạnh hư rồi", "tủ lạnh bị hỏng", "máy giặt lỗi rồi"])
def test_a_tie_or_a_word_that_says_nothing_still_asks(kb, text):
    reply, _ = _diagnose(kb, text)
    assert reply.status.value == "needs_clarification"
    # A vague report is not a danger report.
    assert not (reply.message_vi or "").startswith("Dạ đây là dấu hiệu nguy hiểm")
