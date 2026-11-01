"""The diagnostic state is kept, versioned and survives a restart.

PO 01/11/2026 (audit approved): measured on the served model, "Máy lạnh bị chảy
nước và không lạnh." → "Không." → "Bên phải dàn lạnh." → "Vậy giờ em thấy sao?"
changed its answer with every message and came back on the fourth to exactly
the first, forgetting the third. The shortlist was rebuilt from scratch each
turn, answers were never tied to the question they answered, and everything
lived in this process's memory only. These tests pin the four-turn scenario
the PO gave, a long conversation, and a restart in the middle of one.
"""

import asyncio
import json
from pathlib import Path

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import diagnostic_state
from app.services.pipeline.conversation import ConversationStore
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline, _spoken_question
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()
ROOT = Path(__file__).resolve().parents[1]

PO_SCENARIO = [
    "Máy lạnh bị chảy nước và không lạnh.",
    "Không.",
    "Bên phải dàn lạnh.",
    "Vậy giờ em thấy sao?",
]


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline(store=None) -> LocalPipeline:
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)
    if store is not None:
        pipeline._conversations = store
    return pipeline


def _talk(pipeline, turns, session_id=None, state=None):
    async def run():
        replies, sid, carried = [], session_id, state
        for text in turns:
            reply = await pipeline.diagnose(
                DiagnosisRequest(description=text, session_id=sid, diagnostic_state=carried)
            )
            sid, carried = reply.session_id, reply.diagnostic_state
            replies.append(reply)
        return replies

    return asyncio.run(run())


def _canonical(reply):
    return reply.diagnostic_state["canonical"]


def _faults(reply):
    return [f.fault_code for f in reply.suspected_faults]


def test_every_reply_carries_a_versioned_state_that_validates():
    replies = _talk(_pipeline(ConversationStore()), PO_SCENARIO)
    versions = [r.state_version for r in replies]
    assert versions == [1, 2, 3, 4]
    for reply in replies:
        state = diagnostic_state.CanonicalState.model_validate(_canonical(reply))
        assert state.schema_version == diagnostic_state.SCHEMA_VERSION
        assert state.state_version == reply.state_version


def test_the_po_scenario_keeps_every_fact_and_never_forgets_the_third_turn():
    replies = _talk(_pipeline(ConversationStore()), PO_SCENARIO)
    last = _canonical(replies[-1])
    device = last["devices"][0]
    assert device["deviceType"] == "air_conditioner"
    # Every message the customer sent is still on record, in order, with its turn.
    assert [s["textVi"] for s in device["statements"]] == PO_SCENARIO
    assert [s["turn"] for s in device["statements"]] == [1, 2, 3, 4]
    assert all(s["source"] == "USER_REPORTED" for s in device["statements"])
    # "Vậy giờ em thấy sao?" brings nothing new: the answer stays what the
    # third turn made it, instead of snapping back to the first.
    assert _faults(replies[3]) == _faults(replies[2])
    # Nothing is ever confirmed by the assistant.
    statuses = {h["status"] for h in device["hypotheses"]}
    assert statuses <= {"POSSIBLE", "LESS_LIKELY", "RULED_OUT"}
    assert last["diagnosisStatus"] != "CONFIRMED"


def test_no_question_is_asked_twice_and_answers_are_tied_to_their_question():
    turns = PO_SCENARIO[:3] + ["Có, nước nhỏ giọt dưới dàn lạnh", "Vậy giờ em thấy sao?"]
    replies = _talk(_pipeline(ConversationStore()), turns)
    qa = _canonical(replies[-1])["qa"]
    questions = [q["questionVi"] for q in qa]
    assert len(questions) == len(set(questions))
    answered = [q for q in qa if q["status"] == "ANSWERED"]
    assert answered, qa
    for q in answered:
        assert q["answeredTurn"] == q["askedTurn"] + 1
    # Asked back is not an answer.
    assert all(q["answerVi"] != "Vậy giờ em thấy sao?" for q in qa)


def test_while_two_faults_are_level_the_answer_asks_one_question_to_tell_them_apart():
    replies = _talk(_pipeline(ConversationStore()), PO_SCENARIO[:3])
    third = replies[2]
    assert len(third.suspected_faults) >= 2
    assert "cho em hỏi thêm" in (third.message_vi or "")
    assert _canonical(third)["diagnosisStatus"] == "COLLECTING_INFORMATION"
    pending = [q for q in _canonical(third)["qa"] if q["status"] == "PENDING"]
    assert len(pending) == 1


def test_a_yes_to_the_question_narrows_the_faults():
    replies = _talk(_pipeline(ConversationStore()), PO_SCENARIO[:3] + ["Có, nước nhỏ giọt dưới dàn lạnh"])
    assert _faults(replies[3]) == ["AC_DRAIN_BLOCKED"]
    assert _canonical(replies[3])["diagnosisStatus"] == "LIKELY"


def test_a_restart_in_the_middle_changes_nothing():
    """Backend sends back the state it stored; the new process carries on."""
    store = ConversationStore()
    before = _talk(_pipeline(store), PO_SCENARIO[:3])
    uninterrupted = _talk(_pipeline(store), PO_SCENARIO[3:], session_id=before[-1].session_id)

    fresh = _pipeline(ConversationStore())  # the process restarted: nothing held
    first_half = _talk(_pipeline(ConversationStore()), PO_SCENARIO[:3])
    resumed = _talk(
        fresh, PO_SCENARIO[3:], session_id=first_half[-1].session_id, state=first_half[-1].diagnostic_state
    )
    assert resumed[0].session_id == first_half[-1].session_id
    assert _faults(resumed[0]) == _faults(uninterrupted[0])
    assert resumed[0].state_version == 4
    assert _canonical(resumed[0])["qa"] == _canonical(uninterrupted[0])["qa"]


def test_an_older_stored_state_never_replaces_a_newer_conversation():
    store = ConversationStore()
    pipeline = _pipeline(store)
    replies = _talk(pipeline, PO_SCENARIO[:3])
    stale = replies[0].diagnostic_state
    held = store.peek(replies[-1].session_id)
    assert diagnostic_state.restore(stale, store, held.session_id) is None
    assert store.peek(held.session_id) is held


def test_a_state_for_another_session_or_with_unknown_classes_is_refused():
    store = ConversationStore()
    replies = _talk(_pipeline(store), PO_SCENARIO[:2])
    state = replies[-1].diagnostic_state
    assert diagnostic_state.restore(state, ConversationStore(), "someone-else") is None
    tampered = json.loads(json.dumps(state))
    tampered["engine"]["conversation"]["__dc__"] = "Popen"
    assert diagnostic_state.restore(tampered, ConversationStore(), replies[-1].session_id) is None


def test_a_long_conversation_keeps_everything_it_was_told():
    turns = [
        "máy lạnh không mát",
        "chạy cả ngày mà phòng vẫn nóng",
        "không",
        "mới vệ sinh rồi",
        "dàn nóng vẫn quay",
        "có tiếng kêu nhỏ",
        "máy Daikin",
        "dùng được 5 năm rồi",
        "không có mùi lạ",
        "ừ",
        "vẫn vậy",
        "Vậy giờ em thấy sao?",
        "có cần gọi thợ không",
        "vẫn chảy chút nước",
        "ok em",
    ]
    replies = _talk(_pipeline(ConversationStore()), turns)
    last = _canonical(replies[-1])
    said = [s["textVi"] for d in last["devices"] for s in d["statements"]]
    for text in turns:
        assert text in said, text
    assert last["turns"] == len(turns)
    questions = [q["questionVi"] for q in last["qa"]]
    assert len(questions) == len(set(questions))
    # "mới vệ sinh rồi" ruled the dirty filter out, and it stays out.
    ruled = {h["faultCode"] for d in last["devices"] for h in d["hypotheses"] if h["status"] == "RULED_OUT"}
    assert "AC_DIRTY_FILTER" in ruled
    for reply in replies[4:]:
        assert "AC_DIRTY_FILTER" not in _faults(reply)


def test_the_published_schema_is_the_one_the_code_writes():
    published = json.loads((ROOT / "docs" / "diagnostic-state.schema.json").read_text(encoding="utf-8"))
    assert published == diagnostic_state.json_schema(), "python tools/write_state_schema.py"


def test_the_templated_question_is_said_as_a_person_would():
    assert _spoken_question("Thiết bị có hiện tượng đóng tuyết không?", "Máy lạnh") == "Máy lạnh nhà mình có bị đóng tuyết không ạ?"
    assert _spoken_question("Dàn nóng có quay không ạ?", "Máy lạnh") == "Dàn nóng có quay không ạ?"


def test_a_no_narrows_and_never_brings_in_a_fault_nobody_described():
    """Measured on the served model 01/11/2026: "Không." to the drip question
    let a faulty control board in to fill the second place, and the price went
    from 1.299.000đ to 4.049.000đ on no evidence."""
    from app.services.pipeline.conversation import Conversation

    chat = Conversation("s")
    chat.hypotheses = ["AC_LOW_REFRIGERANT", "AC_DRAIN_BLOCKED"]
    chat.hypotheses_device = "air_conditioner"
    chat.state.penalties["AC_DRAIN_BLOCKED"] = 0.45
    assert chat.keep_hypotheses(["AC_LOW_REFRIGERANT", "AC_PCB_FAULT"], "air_conditioner", new_symptom=False) == [
        "AC_LOW_REFRIGERANT"
    ]
    # A new symptom may still bring in a new leader.
    assert chat.keep_hypotheses(["AC_PCB_FAULT"], "air_conditioner", new_symptom=True)[0] == "AC_PCB_FAULT"
