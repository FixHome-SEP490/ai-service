"""The conversation as a whole: what the customer rules out stays ruled out.

The case that started this: an air conditioner that was not cooling, the
answer "clean it", the customer saying it had just been cleaned, and the answer
"clean it" again. Everything here is a way that repeat could come back, or a
way the fix for it could start throwing away things the customer did *not*
rule out.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import dialogue_state as ds
from app.services.pipeline import local_pipeline as lp
from app.services.pipeline.conversation import ConversationStore
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm
from tools.dialogue_cases import DIALOGUES, Dialogue
from tools.dialogue_corpus import generate
from tools.eval_dialogue import run_dialogues


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


@pytest.fixture(scope="module")
def lexicon(kb):
    return ds.get_lexicon(kb)


def _read(kb, lexicon, device, text, previous=()):
    return ds.read_turn(text, kb.faults_for_device(device), previous_codes=previous, lexicon=lexicon)


def _excluded(kb, lexicon, device, text, previous=()):
    return {e.fault_code for e in _read(kb, lexicon, device, text, previous).exclusions}


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline(kb):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    pipeline._conversations = ConversationStore()
    return pipeline


# ---------------------------------------------------------------------------
# Reading the way people type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("ko mát", "khong mat"),
        ("hông mát", "khong mat"),
        ("máy lạnh hư rồi", "may lanh hong roi"),
        ("khoong mats", "khong mat"),
        ("khônggggg mát", "khong mat"),
        ("đã vs r", "da ve sinh roi"),
        ("sai rùi", "sai roi"),
        ("răng rứa", "sao vay"),
    ],
)
def test_typing_is_normalised(lexicon, typed, expected):
    assert lexicon.normalize(typed) == expected


def test_a_dialect_word_inside_a_trade_term_is_left_alone(lexicon):
    """"Mô" is "đâu" in Huế; "mô tơ" is a motor everywhere."""
    assert "mo to" in lexicon.normalize("mới thay mô tơ mâm rồi")
    assert lexicon.normalize("máy lạnh mô rồi") == "may lanh dau roi"


def test_leaking_is_not_burning(kb, lexicon):
    """Folded, "chảy" and "cháy" are one word. With accents typed they are not."""
    reading = _read(kb, lexicon, "air_conditioner", "không có chảy nước")
    assert "AC_SMELL_BURNT" not in {e.fault_code for e in reading.exclusions}


# ---------------------------------------------------------------------------
# What a turn rules out
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "device, text, fault",
    [
        ("air_conditioner", "mới vệ sinh tuần trước rồi", "AC_DIRTY_FILTER"),
        ("air_conditioner", "không phải do bẩn đâu", "AC_DIRTY_FILTER"),
        ("air_conditioner", "lưới lọc sạch mà", "AC_DIRTY_FILTER"),
        ("refrigerator", "Bác thông cái lỗ thoát nước rồi mà vẫn chảy", "FRIDGE_DRAIN_BLOCKED"),
        ("water_heater", "rơ le thì nhà tôi kiểm tra rồi không sao", "WH_THERMOSTAT"),
        ("electric_fan", "cháy mô tơ thì không phải rồi", "FAN_MOTOR_BURNT"),
        ("microwave_oven", "em mới thay mô tơ mâm rồi đó", "MW_TURNTABLE_MOTOR"),
        ("electric_fan", "tuan trc mk co goi ng thay day dien roai ma van day nong", "FAN_CORD_DAMAGE"),
        ("light_bulb", "thay bóng rồi vẫn không sáng", "LIGHT_BULB_DEAD"),
    ],
)
def test_exclusions_are_read(kb, lexicon, device, text, fault):
    assert fault in _excluded(kb, lexicon, device, text)


def test_a_denial_in_its_own_clause_belongs_to_the_cause_before_it(kb, lexicon):
    assert "AC_DIRTY_FILTER" in _excluded(
        kb, lexicon, "air_conditioner", "lưới lọc thì em kiểm tra rồi, không sao"
    )


@pytest.mark.parametrize(
    "device, text, fault",
    [
        ("air_conditioner", "chưa vệ sinh lần nào", "AC_DIRTY_FILTER"),
        ("air_conditioner", "có nên vệ sinh không", "AC_DIRTY_FILTER"),
        ("air_conditioner", "vệ sinh hết bao nhiêu tiền", "AC_DIRTY_FILTER"),
        ("power_outlet", "thay ổ mới giá sao", "OUTLET_LOOSE_CONTACT"),
        ("power_outlet", "nhà tui định chỉ cắm một cái", "OUTLET_OVERLOAD"),
        ("smart_lock", "mới thay pin tháng trước mà đã hết", "LOCK_LOW_BATTERY"),
        ("smart_lock", "khóa cửa thông minh mất thẻ từ không mở được cửa", "LOCK_CARD_FAULT"),
        ("refrigerator", "tủ lạnh rã đông rồi mà vẫn đóng tuyết", "FRIDGE_DEFROST_FAULT"),
        ("electric_fan", "quạt không tuốc năng", "FAN_OSCILLATION_FAULT"),
        ("light_bulb", "tụ nóng không bình thường", "LIGHT_FLICKERING"),
    ],
)
def test_what_is_not_an_exclusion_is_not_read_as_one(kb, lexicon, device, text, fault):
    """The opposite failure, and the one an eager fix for the first would cause."""
    assert fault not in _excluded(kb, lexicon, device, text)


def test_a_flat_no_rejects_the_last_answer(kb, lexicon):
    for text in ("không phải đâu", "sai rồi", "hong phai", "trật lất rồi", "nỏ phải"):
        assert _excluded(kb, lexicon, "air_conditioner", text, ["AC_LOW_REFRIGERANT"]) == {
            "AC_LOW_REFRIGERANT"
        }, text


def test_a_bare_word_typed_without_accents_does_not_name_a_cause(kb, lexicon):
    """"cai do" is "cái đó", not "cái dơ"."""
    assert "AC_DIRTY_FILTER" not in _excluded(kb, lexicon, "air_conditioner", "hong phai cai do")


def test_safety_faults_are_never_excluded_by_a_sentence(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("gas_stove", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="bếp có mùi gas", sessionId=chat.session_id))
        await pipeline.diagnose(DiagnosisRequest(description="không phải rò gas đâu", sessionId=chat.session_id))
        return pipeline._conversations.get_or_create(chat.session_id)

    chat = asyncio.run(run())
    assert "STOVE_GAS_LEAK" not in chat.state.excluded_codes()


# ---------------------------------------------------------------------------
# Ranking after the customer has spoken
# ---------------------------------------------------------------------------


def test_the_case_that_started_this(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("air_conditioner", 0.9, "image")
        first = await pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh nhà mình không mát", sessionId=chat.session_id)
        )
        second = await pipeline.diagnose(
            DiagnosisRequest(
                description="mới vệ sinh đây mà, không thể nào do bẩn được",
                sessionId=first.session_id,
            )
        )
        third = await pipeline.answer(ChatRequest(question="vậy nên đặt dịch vụ nào", sessionId=first.session_id))
        return second, third

    second, third = asyncio.run(run())
    faults = [f.fault_code for f in second.suspected_faults]
    assert "AC_DIRTY_FILTER" not in faults
    assert faults and faults[0] == "AC_LOW_REFRIGERANT"
    assert "loại khả năng" in (second.message_vi or "")
    services = [s.service_code for s in second.recommended_services + third.recommended_services]
    assert "VE_SINH_DIEU_HOA_1HP" not in services


def test_a_stated_suspicion_counts(kb, lexicon):
    reading = _read(kb, lexicon, "air_conditioner", "em không biết có phải hết gas không ạ")
    assert reading.boosts.get("AC_LOW_REFRIGERANT", 1.0) > 1.0
    assert "khong biet" not in reading.retrieval_text


def test_a_failed_fix_points_at_the_next_check(kb, lexicon):
    reading = _read(kb, lexicon, "water_heater", "thay thanh đốt mới rồi vẫn không nóng")
    assert "WH_HEATING_ELEMENT" in {e.fault_code for e in reading.exclusions}
    assert reading.persist.get("WH_THERMOSTAT", 1.0) > 1.0
    assert "khong nong" in reading.retrieval_text


def test_not_spinning_is_not_spinning_loudly(kb):
    """Negation is part of the symptom: "không vắt" is not "kêu to khi vắt"."""
    ranked = Retriever(kb).candidate_faults("máy giặt không vắt được", "washing_machine")
    assert ranked[0].fault.fault_code == "WM_NO_SPIN"


def test_prose_about_a_ruled_out_fault_is_not_handed_to_the_model(kb):
    retriever = Retriever(kb)
    codes = ["AC_DIRTY_FILTER", "AC_LOW_REFRIGERANT"]
    passages = retriever.corpus_passages(
        "máy lạnh không mát vệ sinh", device_type="air_conditioner", fault_codes=codes,
        ruled_out={"AC_DIRTY_FILTER"},
    )
    assert all(p.chunk.fault_code != "AC_DIRTY_FILTER" for p in passages)


def test_the_model_is_told_what_was_ruled_out(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("air_conditioner", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="máy lạnh không mát", sessionId=chat.session_id))
        await pipeline.diagnose(DiagnosisRequest(description="đã vệ sinh rồi", sessionId=chat.session_id))
        return pipeline._conversations.get_or_create(chat.session_id)

    facts = asyncio.run(run()).facts_vi(kb)
    assert any(line.startswith("ĐÃ LOẠI AC_DIRTY_FILTER") for line in facts)


# ---------------------------------------------------------------------------
# Holding the session
# ---------------------------------------------------------------------------


def test_a_lost_session_is_rebuilt_from_what_the_customer_said(kb):
    pipeline = _pipeline(kb)
    stale = "f" * 32

    async def run():
        return await pipeline.diagnose(
            DiagnosisRequest(
                description="vậy giờ là bị gì",
                sessionId=stale,
                history=["máy lạnh nhà mình không mát", "mới vệ sinh tuần trước rồi"],
            )
        )

    reply = asyncio.run(run())
    assert reply.session_id and reply.session_id != stale
    chat = pipeline._conversations.get_or_create(reply.session_id)
    assert "AC_DIRTY_FILTER" in chat.state.excluded_codes()
    assert [f.fault_code for f in reply.suspected_faults][:1] == ["AC_LOW_REFRIGERANT"]


def test_history_cannot_rewrite_a_session_that_is_still_held(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh không mát"))
        await pipeline.diagnose(
            DiagnosisRequest(description="còn kêu to", sessionId=first.session_id, history=["tủ lạnh hỏng"])
        )
        return pipeline._conversations.get_or_create(first.session_id)

    chat = asyncio.run(run())
    said = [t.text_vi for t in chat.turns if t.role == "customer"]
    assert said == ["máy lạnh không mát", "còn kêu to"]


def test_an_unknown_id_is_never_adopted_even_with_history(kb):
    pipeline = _pipeline(kb)

    async def run():
        return await pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh không mát", sessionId="guest", history=["x"])
        )

    assert asyncio.run(run()).session_id != "guest"


@pytest.mark.parametrize(
    "history",
    [["a"] * 21, ["x" * 2001], [""]],
)
def test_history_is_bounded(history):
    with pytest.raises(ValueError):
        DiagnosisRequest(description="máy lạnh không mát", history=history)
    with pytest.raises(ValueError):
        ChatRequest(question="máy lạnh không mát", history=history)


def test_two_turns_of_one_session_do_not_interleave(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh không mát"))
        sid = first.session_id
        replies = await asyncio.gather(
            pipeline.diagnose(DiagnosisRequest(description="còn kêu to nữa", sessionId=sid)),
            pipeline.diagnose(DiagnosisRequest(description="với lại chảy nước", sessionId=sid)),
        )
        return sid, replies, pipeline._conversations.get_or_create(sid)

    sid, replies, chat = asyncio.run(run())
    assert all(r.session_id == sid for r in replies)
    roles = [t.role for t in chat.turns]
    # Each customer turn is followed by its own answer, never by the other's.
    for index, role in enumerate(roles[:-1]):
        if role == "customer":
            assert roles[index + 1] == "assistant"


def test_reading_a_long_message_is_fast(kb, lexicon):
    """Two thousand characters against every fault, with no appliance known."""
    every = [f for d in kb.device_types for f in kb.faults_for_device(d)]
    text = ("máy lạnh không mát, mới vệ sinh rồi mà vẫn không mát, không phải do bẩn đâu " * 30)[:2000]
    started = time.perf_counter()
    ds.read_turn(text, every, lexicon=lexicon)
    ds.read_turn("x" * 2000, every, lexicon=lexicon)
    ds.read_turn(" ".join(["khôngggg"] * 250)[:2000], every, lexicon=lexicon)
    assert time.perf_counter() - started < 3.0


# ---------------------------------------------------------------------------
# Staying on the subject
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["ko chỉnh dc nóng lạnh", "phích cắm nóng", "rửa bát lâu lắm", "chỗ công tắc bị nóng", "không phải công tắc đâu"],
)
def test_a_part_named_in_passing_does_not_change_the_appliance(kb, text):
    """A mixer tap's "nóng lạnh" is not a water heater, a plug is not a socket."""
    assert lp._device_asked_for_now(text, kb, strong=True) is None


@pytest.mark.parametrize(
    "text, device",
    [
        ("à còn cái tủ lạnh nhà em nữa, đọng nước dưới đáy tủ", "refrigerator"),
        ("hỏi luôn cái quạt trần: ù mà không quay", "ceiling_fan"),
        ("thôi khoan, giờ cái máy sấy mới gấp, may say nong bat thuong", "clothes_dryer"),
        ("à còn cái tiviiiii nhà em nữa", "television"),
        ("cái lof nướng cũng bij nè", "oven"),
        ("giờ cái lò vi ba mới gấp", "microwave_oven"),
    ],
)
def test_a_new_appliance_named_outright_is_followed(kb, text, device):
    assert lp._device_asked_for_now(text, kb, strong=True) == device


def test_the_conversation_keeps_its_appliance_through_a_part_name(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("light_bulb", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="bấm công tắc không lên đèn", sessionId=chat.session_id))
        await pipeline.diagnose(DiagnosisRequest(description="không phải công tắc đâu", sessionId=chat.session_id))
        return pipeline._conversations.get_or_create(chat.session_id)

    chat = asyncio.run(run())
    assert chat.device_type == "light_bulb"
    assert "LIGHT_SWITCH_FAULT" in chat.state.excluded_codes()


@pytest.mark.parametrize("text", ["đúng rồi", "cảm ơn em nhé", "có nguy hiểm không", "vậy giờ sửa sao", "chào em", "sửa cái đó hết bao nhiêu tiền"])
def test_talk_about_the_conversation_is_not_searched_as_a_symptom(kb, lexicon, text):
    reading = _read(kb, lexicon, "air_conditioner", text)
    assert reading.retrieval_text == ""
    assert reading.meta_only


def test_a_yes_keeps_the_answer_it_agrees_with(kb, lexicon):
    reading = _read(kb, lexicon, "air_conditioner", "đúng rồi đó em", ["AC_CAPACITOR"])
    assert reading.boosts.get("AC_CAPACITOR", 1.0) > 1.0


@pytest.mark.parametrize("text", ["kể chuyện cười đi", "bitcoin giá bao nhiêu", "em có biết đá bóng tối nay không", "cho hỏi giá vàng hôm nay"])
def test_off_topic_mid_conversation_is_refused_and_the_thread_kept(kb, text):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("water_heater", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="bình nóng lạnh không nóng", sessionId=chat.session_id))
        off = await pipeline.answer(ChatRequest(question=text, sessionId=chat.session_id))
        back = await pipeline.answer(ChatRequest(question="vậy giờ sửa sao", sessionId=chat.session_id))
        return off, back, pipeline._conversations.get_or_create(chat.session_id)

    from app.core.config import settings

    off, back, chat = asyncio.run(run())
    assert off.answer_vi == settings.OUT_OF_SCOPE_MESSAGE_VI
    assert chat.device_type == "water_heater"
    assert "bitcoin" not in chat.symptom_text() and "bong" not in chat.symptom_text().split()


@pytest.mark.parametrize(
    "text, danger",
    [
        ("khói ra từ máy lạnh", True),
        ("máy lạnh có mùi khét", True),
        ("ổ cắm bị chập cháy", True),
        ("không có mùi khét", False),
        ("ổ cắm điện thiết bị chập chờn", False),
        ("bếp gas bếp cháy một lúc rồi tắt", False),
        ("lò nướng bị cháy bánh", False),
    ],
)
def test_danger_is_read_when_it_is_described(kb, lexicon, text, danger):
    assert _read(kb, lexicon, "air_conditioner", text).danger is danger


def test_danger_stays_described_after_a_denial(kb):
    """Smoke is still smoke after "chắc không phải cháy đâu"."""
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("air_conditioner", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="máy lạnh có mùi khét khi bật", sessionId=chat.session_id))
        return await pipeline.diagnose(
            DiagnosisRequest(description="chắc không phải cháy đâu", sessionId=chat.session_id)
        )

    reply = asyncio.run(run())
    assert reply.urgency.value == "HIGH"


# ---------------------------------------------------------------------------
# Answers, corrections, a wrong guess
# ---------------------------------------------------------------------------


def _ac_discriminator(kb, text):
    return next(d for d in kb.discriminators_for_device("air_conditioner") if d.question_vi.startswith(text))


@pytest.mark.parametrize("reply, yes", [("không", False), ("dạ không ạ", False), ("chưa", False), ("có", True), ("dạ có", True), ("rồi", True)])
def test_a_bare_yes_or_no_answers_the_question_asked(kb, lexicon, reply, yes):
    entry = _ac_discriminator(kb, "Cục nóng ngoài trời có chạy không")
    answer = ds.answer_to(entry.question_vi, reply, kb.faults_for_device("air_conditioner"), [entry], lexicon)
    assert answer is not None and answer.yes is yes
    favoured = entry.favours_if_yes if yes else entry.favours_if_no
    assert all(answer.factors[c] > 1.0 for c in favoured if c in answer.factors)


def test_a_symptom_starting_with_khong_is_not_an_answer(kb, lexicon):
    entry = _ac_discriminator(kb, "Cục nóng ngoài trời có chạy không")
    assert ds.answer_to(entry.question_vi, "không mát lắm", kb.faults_for_device("air_conditioner"), [entry], lexicon) is None


def test_a_yes_to_a_symptom_question_is_searched_as_said(kb, lexicon):
    answer = ds.answer_to("Thiết bị có hiện tượng kêu to khi vắt không?", "có ạ", kb.faults_for_device("washing_machine"), [], lexicon)
    assert answer.yes and answer.said == "keu to khi vat"


def test_the_answer_reaches_the_ranking(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh nhà em bị sao ấy"))
        asked = first.clarification.questions_vi[0] if first.clarification else None
        await pipeline.diagnose(DiagnosisRequest(description="không", sessionId=first.session_id))
        return asked, pipeline._conversations.get_or_create(first.session_id)

    asked, chat = asyncio.run(run())
    assert asked, "a vague message should be met with a question"
    entry = next((d for d in kb.discriminators_for_device("air_conditioner") if d.question_vi == asked), None)
    if entry is not None:
        factors = chat.state.factors()
        assert any(factors.get(c, 1.0) > 1.0 for c in entry.favours_if_no)


def test_taking_back_a_fix_brings_the_fault_back(kb, lexicon):
    state = ds.DialogueState()
    never = ds.never_excluded_codes()
    state.apply(_read(kb, lexicon, "air_conditioner", "mới vệ sinh lưới lọc rồi"), never)
    assert "AC_DIRTY_FILTER" in state.excluded_codes()
    reading = _read(kb, lexicon, "air_conditioner", "à nhầm, thật ra chưa vệ sinh lưới lọc", ["AC_LOW_REFRIGERANT"])
    assert not reading.denied_previous, "correcting oneself is not rejecting the answer"
    state.apply(reading, never)
    assert "AC_DIRTY_FILTER" not in state.excluded_codes()


@pytest.mark.parametrize(
    "text, device",
    [
        ("à nhầm, khônggggg phải máy sấy mà là tivi", "television"),
        ("nhà mình nói nhầm, là cais tur lạnh chứ không phải bồn cầu", "refrigerator"),
        ("sửa lại: ổ cắm nha hông phải máy rửa chén", "power_outlet"),
        ("à nhầm, k phải quạt máy mà là bóng đèn", "light_bulb"),
        ("cái quạt trần cũng bị nè", "ceiling_fan"),
    ],
)
def test_a_corrected_appliance_is_followed(kb, text, device):
    assert lp._device_asked_for_now(text, kb, strong=True) == device


def test_accents_decide_a_name_when_typed(kb):
    """"Âm trần" is a recessed light, not "ấm". Once "đèn âm trần" became a
    name for a light, the light is the answer; the kettle never is."""
    assert lp._device_asked_for_now("đèn âm trần chảy nước", kb, strong=True) == "light_bulb"
    assert lp._device_asked_for_now("máy âm trần chảy nước", kb, strong=True) != "kettle"


def test_a_correction_holds_on_the_next_turn(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("toilet", 0.9, "image")
        sid = chat.session_id
        await pipeline.diagnose(DiagnosisRequest(description="bồn cầu chảy nước liên tục", sessionId=sid))
        await pipeline.diagnose(DiagnosisRequest(description="à nhầm, là cái bóng đèn chứ không phải bồn cầu", sessionId=sid))
        await pipeline.diagnose(DiagnosisRequest(description="bấm công tắc không lên đèn", sessionId=sid))
        return pipeline._conversations.get_or_create(sid)

    assert asyncio.run(run()).device_type == "light_bulb"


def test_a_wrong_guess_moves_to_the_next_one_the_conversation_points_to(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("air_conditioner", 0.9, "image")
        sid = chat.session_id
        first = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh không mát, chạy lâu mới mát", sessionId=sid))
        held = pipeline._conversations.get_or_create(sid)
        before = [c.fault.fault_code for c in pipeline._retriever.candidate_faults(held.symptom_text(), "air_conditioner", 5)]
        second = await pipeline.diagnose(DiagnosisRequest(description="không phải đâu", sessionId=sid))
        return first, before, second

    first, before, second = asyncio.run(run())
    led = first.suspected_faults[0].fault_code
    nxt = second.suspected_faults[0].fault_code
    assert nxt != led
    assert nxt in [c for c in before if c != led][:3]


def test_a_no_that_says_what_it_is_instead_is_a_no(kb, lexicon):
    reading = _read(kb, lexicon, "gas_stove", "hông phải dzậy, nó vặn nặng tay", ["STOVE_REGULATOR"])
    assert reading.denied_previous
    # What it is instead is still searched.
    assert "nang tay" in reading.retrieval_text


def test_a_no_that_names_a_cause_denies_only_the_cause(kb, lexicon):
    reading = _read(kb, lexicon, "air_conditioner", "hông phải dơ đâu", ["AC_LOW_REFRIGERANT"])
    assert {e.fault_code for e in reading.exclusions} == {"AC_DIRTY_FILTER"}


# ---------------------------------------------------------------------------
# Several appliances in one message; how the customer sounds
# ---------------------------------------------------------------------------


def test_two_appliances_in_one_message_are_both_diagnosed_in_the_same_reply(kb):
    """PO 25/10/2026: no waiting for "xem tiếp"; every appliance is answered.

    The air conditioner stays the conversation's appliance; the fridge gets
    its own conversation, and "xem tiếp" or naming it brings its answer up."""
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh không mát, còn tủ lạnh nhà em cũng chảy nước ra sàn")
        )
        second = await pipeline.diagnose(DiagnosisRequest(description="xem tiếp", sessionId=first.session_id))
        return first, second, pipeline._conversations.get_or_create(first.session_id)

    first, second, chat = asyncio.run(run())
    assert [f.fault_code for f in first.suspected_faults][:1] == ["AC_LOW_REFRIGERANT"]
    fridge = next(d for d in first.devices if d.device_type == "refrigerator")
    assert [f.fault_code for f in fridge.suspected_faults][:1] == ["FRIDGE_DRAIN_BLOCKED"]
    assert "Về tủ lạnh" in (first.message_vi or "")
    assert "xem tiếp" not in (first.message_vi or "")
    assert chat.queued == {}
    assert chat.device_type == "air_conditioner"
    assert second.session_id == first.session_id
    assert second.devices[0].device_type == "refrigerator" and second.devices[0].is_primary
    assert [f.fault_code for f in second.suspected_faults][:1] == ["FRIDGE_DRAIN_BLOCKED"]


def test_a_correction_is_not_split_into_two_appliances(kb):
    pipeline = _pipeline(kb)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device("air_conditioner", 0.9, "image")
        await pipeline.diagnose(DiagnosisRequest(description="à nhầm, không phải máy lạnh mà là tủ lạnh", sessionId=chat.session_id))
        return pipeline._conversations.get_or_create(chat.session_id)

    chat = asyncio.run(run())
    assert chat.device_type == "refrigerator" and not chat.queued


@pytest.mark.parametrize(
    "text, mood, address",
    [
        ("làm ăn kiểu gì mà máy giặt không vắt hoài vậy", "upset", None),
        ("MÁY LẠNH NHÀ TÔI KHÔNG MÁT GÌ CẢ", "upset", None),
        ("ổ cắm nóng quá em sợ quá", "worried", None),
        ("cháu ơi bình nóng lạnh nhà bác không nóng", None, "bác"),
        ("máy lạnh nhà cô chảy nước", None, "cô"),
        ("máy lạnh không mát", None, None),
    ],
)
def test_mood_and_address_are_read(lexicon, text, mood, address):
    assert ds.mood_of(text, lexicon) == (mood, address)


def test_the_customer_is_addressed_as_they_asked():
    assert ds.address_as("Dạ anh/chị yên tâm. Anh/chị đặt dịch vụ giúp em.", "bác") == "Dạ bác yên tâm. Bác đặt dịch vụ giúp em."
    assert ds.address_as("Dạ anh/chị yên tâm.", None) == "Dạ anh/chị yên tâm."


def test_an_upset_customer_gets_an_apology_first(kb):
    pipeline = _pipeline(kb)

    async def run():
        return await pipeline.diagnose(DiagnosisRequest(description="làm ăn kiểu gì mà máy giặt nhà tôi không vắt hoài vậy!!!"))

    assert (asyncio.run(run()).message_vi or "").startswith("Dạ em xin lỗi")


# ---------------------------------------------------------------------------
# Whole conversations
# ---------------------------------------------------------------------------


def _rate(rows, key):
    scored = [r[key] for r in rows if r[key] is not None]
    return sum(1 for v in scored if v) / max(len(scored), 1)


def test_hand_written_conversations():
    rows = asyncio.run(run_dialogues(list(DIALOGUES)))
    assert not [r["turns"] for r in rows if r["repeated"]], "a ruled-out fault came back"
    assert not [r["turns"] for r in rows if r["service_bad"]]
    assert _rate(rows, "leader_ok") >= 0.9
    assert _rate(rows, "heard") >= 0.9


def test_generated_conversations():
    """Every appliance, every way of pushing back, every voice and keyboard.

    Thresholds sit just under what was measured on 4,800 (99.2%, 99.5% and
    98.5% staying on the subject), so a change that costs a point fails here
    rather than in a customer's chat.
    """
    dialogues: list[Dialogue] = generate(limit=600, seed=20261014)
    rows = asyncio.run(run_dialogues(dialogues))
    assert len(rows) >= 550
    assert 1 - _rate(rows, "repeated") >= 0.97
    assert 1 - _rate(rows, "wrongly_excluded") >= 0.98
    assert 1 - _rate(rows, "service_bad") >= 0.98
    # Staying on the subject: a yes, a thanks, a question about price or
    # danger, an off-topic aside, a new appliance named outright.
    assert _rate(rows, "checks_ok") >= 0.95


def test_the_reply_carries_notes_for_the_technician(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh không mát"))
        return await pipeline.diagnose(
            DiagnosisRequest(description="mới vệ sinh tuần trước rồi, em nghĩ có phải hết gas không", sessionId=first.session_id)
        )

    notes = asyncio.run(run()).model_dump(by_alias=True)["notesVi"]
    assert "Khách đã vệ sinh rồi, đã loại bẩn lưới lọc và dàn lạnh." in notes
    assert any(n.startswith("Khách nghi thiếu gas") for n in notes)
    assert not any("_" in n for n in notes), "no fault codes"
