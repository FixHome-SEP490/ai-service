"""The four slips seen on the served model on 16/10, and what fixed each.

1. "tui tự clean đầu lọc" - English verbs were not read, so the filter the
   customer had cleaned was suggested again.
2. "không phi điều hoà mà là ổ cắm" after "điuề hoà ..." - a typo in the
   first message left no appliance, and the correction then kept the longer
   name it mentioned instead of the one asked for.
3. "mới tẩy cặn bằng giấm" - the pipeline had ruled the scale out, but the
   model wrote about descaling anyway. A reply that names a fault the
   customer ruled out is now discarded like any other bad reply.
4. A code on the display with no symptom in the message ("hãng daikin",
   "báo lỗi E8") moved nothing, because a boost on a fault the search had
   scored at nothing stays nothing.
"""

from __future__ import annotations

import asyncio

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import answer_guard
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


def _pipeline(kb):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    pipeline._conversations = ConversationStore()
    return pipeline


def _talk(kb, turns, seed=None):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        if seed:
            chat.remember_device(seed, 0.9, "image")
        session, replies = chat.session_id, []
        for text in turns:
            reply = await pipeline.diagnose(DiagnosisRequest(description=text, sessionId=session))
            session = reply.session_id
            replies.append(reply)
        return replies, pipeline._conversations.get_or_create(session)

    return asyncio.run(run())


# 1 ------------------------------------------------------------- English verbs


@pytest.mark.parametrize("word", ["clean", "check"])
def test_english_verbs_are_read(kb, word):
    lexicon = ds.get_lexicon(kb)
    assert lexicon.normalize(f"tui tự {word} đầu lọc xong") != f"toi tu {word} dau loc xong"


def test_a_filter_cleaned_in_english_is_ruled_out(kb):
    replies, chat = _talk(
        kb,
        ["vòi nước nước phun lệch", "tui tự clean đầu lọc xong mà chẳng ăn thua gì"],
        seed="faucet",
    )
    assert "FAUCET_LOW_FLOW" in chat.state.excluded
    assert replies[-1].suspected_faults[0].fault_code != "FAUCET_LOW_FLOW"


# 2 ------------------------------------------------------ typos and corrections


def test_a_typo_in_the_appliance_name_is_still_read(kb):
    _, chat = _talk(kb, ["anh ơi, điuề hoà nhà tôi nước nhỏ giọt vào giường"])
    assert chat.device_type == "air_conditioner"


@pytest.mark.parametrize(
    "first",
    ["điều hoà nhà tôi nước nhỏ giọt vào giường", "anh ơi, điuề hoà nhà tôi nước nhỏ giọt vào giường"],
)
@pytest.mark.parametrize("correction", ["à nhầm, không phải điều hoà mà là ổ cắm", "à nhầm, không phi điều hoà mà là ổ cắm"])
def test_the_appliance_asked_for_wins_a_correction(kb, first, correction):
    replies, chat = _talk(kb, [first, correction, "cắm gì vào cũgn không ăn"])
    assert chat.device_type == "power_outlet"
    assert replies[-1].suspected_faults[0].fault_code.startswith("OUTLET_")


def test_a_correction_on_the_first_message_takes_the_second_name(kb):
    _, chat = _talk(kb, ["không phải máy lạnh mà là tủ lạnh, tủ không lạnh"])
    assert chat.device_type == "refrigerator"


# 3 ------------------------------------------------- what the model may not say


def test_the_guard_finds_a_ruled_out_fault_by_its_core_name():
    names = ["Đóng cặn vôi trong bình", "Hỏng rơ le nhiệt", "Thiếu gas, xì gas"]
    assert answer_guard.ruled_out_named("Có thể do đóng cặn vôi trong bình, anh/chị khử cặn bằng giấm.", names)
    assert answer_guard.ruled_out_named("Khả năng là rơ le nhiệt bị hỏng.", names)
    assert answer_guard.ruled_out_named("Máy bị thiếu gas rồi ạ.", names)
    assert not answer_guard.ruled_out_named("Khả năng là hỏng mâm nhiệt.", names)
    assert not answer_guard.ruled_out_named("", names)
    assert not answer_guard.ruled_out_named("Máy bị thiếu gas rồi ạ.", [])


def test_a_one_word_core_is_not_checked():
    # "Hỏng tụ" would match every "tụ" in any reply.
    assert not answer_guard.ruled_out_named("Khả năng hỏng tụ điện ạ.", ["Hỏng tụ"])


def test_an_answer_never_explains_the_fault_just_ruled_out(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="ấm siêu tốc đun lâu sôi"))
        await pipeline.diagnose(DiagnosisRequest(description="mới tẩy cặn bằng giấm hôm qua rồi", sessionId=first.session_id))
        return await pipeline.answer(ChatRequest(question="vậy là do đâu em", sessionId=first.session_id))

    answer = asyncio.run(run())
    assert "đóng cặn vôi" not in (answer.answer_vi or "").lower()


# 4 --------------------------------------------------------- codes, no symptom


@pytest.mark.parametrize(
    "turns, device, fault",
    [
        (["cai dieu hoa bao loi e8", "hang daikin"], "air_conditioner", "AC_COMPRESSOR_FAULT"),
        (["máy giặt nhà em hãng Samsung hiện mã 3C nhé"], "washing_machine", "WM_MOTOR_FAULT"),
        (["máy giặt Samsung cứ nháy lỗi UB, là bị gì vậy"], "washing_machine", "WM_NO_SPIN"),
        (["điều hoà nhà tôi hiện mã H7", "của daikin ạ"], "air_conditioner", "AC_OUTDOOR_FAN_MOTOR"),
    ],
)
def test_the_fault_a_code_names_reaches_the_list(kb, turns, device, fault):
    replies, chat = _talk(kb, turns, seed=device)
    assert fault in [f.fault_code for f in replies[-1].suspected_faults][:3]
