"""A signed-in customer's earlier bookings: said once, passed on, never guessed from.

The backend sends the customer's own last bookings (service, appliance, day).
When the appliance in the conversation is one they had repaired, the assistant
mentions it once and the technician gets it in the notes. It does not change
the diagnosis, it is not said during a danger warning, and an unknown or
unrelated booking is not mentioned at all.
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline.conversation import ConversationStore, day_vi
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

AC_JOB = {"serviceVi": "Sửa điều hòa không mát / chảy nước", "deviceVi": "Máy lạnh", "faultVi": "Thiếu gas, xì gas", "date": "2026-08-03"}
FRIDGE_JOB = {"serviceVi": "Sửa tủ lạnh không lạnh", "date": "2026-09-20"}
RECALL = 'Em thấy ngày 03/08/2026 anh/chị đã đặt "Sửa điều hòa không mát / chảy nước".'


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


def _talk(kb, turns, jobs):
    pipeline = _pipeline(kb)

    async def run():
        replies, session = [], None
        for text in turns:
            reply = await pipeline.diagnose(DiagnosisRequest(description=text, sessionId=session, pastJobs=jobs))
            session = reply.session_id
            replies.append(reply)
        return replies

    return asyncio.run(run())


def _said(replies):
    return [r.message_vi or "" for r in replies]


def test_the_earlier_repair_of_this_appliance_is_mentioned_once(kb):
    # The first reply may be only a question; it is said with the first answer.
    replies = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi", "vẫn không mát", "còn gì nữa không"], [FRIDGE_JOB, AC_JOB])
    said = _said(replies)
    assert sum(RECALL in m for m in said) == 1, said
    assert any("kể với thợ để thợ xem lại lần sửa trước" in m for m in said)


def test_the_technician_gets_it_in_the_notes_with_the_old_guess_marked_as_one(kb):
    _, second = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi"], [AC_JOB])
    notes = second.notes_vi
    assert 'Khách từng đặt "Sửa điều hòa không mát / chảy nước" ngày 03/08/2026, khi đó trợ lý nghi thiếu gas, xì gas.' in notes
    assert "Khách đã vệ sinh rồi, đã loại bẩn lưới lọc và dàn lạnh." in notes


def test_the_old_guess_is_never_said_to_the_customer(kb):
    replies = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi"], [AC_JOB])
    assert not any("khi đó trợ lý nghi" in m for m in _said(replies))


def test_a_booking_for_another_appliance_is_not_mentioned(kb):
    replies = _talk(kb, ["máy giặt không vắt", "chưa thử gì"], [AC_JOB, FRIDGE_JOB])
    assert not any("Em thấy ngày" in m for m in _said(replies))
    assert not any("từng đặt" in n for r in replies for n in r.notes_vi)


def test_it_does_not_change_the_diagnosis(kb):
    with_jobs = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi"], [AC_JOB])
    without = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi"], [])
    for a, b in zip(with_jobs, without):
        assert [f.fault_code for f in a.suspected_faults] == [f.fault_code for f in b.suspected_faults]
        assert a.status == b.status
        assert RECALL not in (b.message_vi or "")


def test_not_while_something_is_dangerous(kb):
    replies = _talk(kb, ["máy lạnh bốc khói có mùi khét", "giờ làm sao em"], [AC_JOB])
    assert all(r.urgency.value == "HIGH" for r in replies)
    assert not any("Em thấy ngày" in m for m in _said(replies))
    # The technician still gets both, the danger line last and never cut.
    notes = replies[-1].notes_vi
    assert notes[-1].startswith("Khách có tả dấu hiệu nguy hiểm")
    assert any(n.startswith("Khách từng đặt") for n in notes)


def test_the_customer_who_never_booked_hears_nothing_new(kb):
    replies = _talk(kb, ["máy lạnh không mát", "mới vệ sinh rồi"], [])
    assert not any("Em thấy ngày" in m for m in _said(replies))
    assert not any("từng đặt" in n for r in replies for n in r.notes_vi)


def test_the_question_path_mentions_it_too(kb):
    pipeline = _pipeline(kb)

    async def run():
        first = await pipeline.diagnose(DiagnosisRequest(description="tủ lạnh không lạnh", pastJobs=[FRIDGE_JOB]))
        return first, await pipeline.answer(
            ChatRequest(question="vậy sửa có lâu không", sessionId=first.session_id, pastJobs=[FRIDGE_JOB])
        )

    first, answer = asyncio.run(run())
    said = (first.message_vi or "") + " " + (answer.answer_vi or "")
    assert said.count('đã đặt "Sửa tủ lạnh không lạnh"') == 1


def test_the_contract_is_strict():
    with pytest.raises(ValidationError):
        DiagnosisRequest(description="máy lạnh không mát", pastJobs=[AC_JOB] * 6)
    with pytest.raises(ValidationError):
        DiagnosisRequest(description="x", pastJobs=[{**AC_JOB, "date": "03/08/2026"}])
    with pytest.raises(ValidationError):
        DiagnosisRequest(description="x", pastJobs=[{**AC_JOB, "address": "12 Lê Lợi"}])
    with pytest.raises(ValidationError):
        ChatRequest(question="x", pastJobs=[{**AC_JOB, "serviceVi": ""}])


def test_day_vi():
    assert day_vi("2026-08-03") == "03/08/2026"
    assert day_vi("") == ""
