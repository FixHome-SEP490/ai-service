"""Error codes on the display, answered from the manufacturer's table and never guessed.

The table holds only codes copied from each brand's official document, with
the link. These tests hold the table to that, and the assistant to answering
only from it: the brand's meaning for a code it holds, "not in the table" for
one it does not, a question about the brand when none is known, and nothing at
all for words that only look like codes.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import error_codes as ec
from app.services.pipeline.conversation import ConversationStore
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

RAW = json.loads(ec.DATA.read_text(encoding="utf-8"))
OFFICIAL = ("https://www.daikin.com/", "https://www.samsung.com/", "https://www.lg.com/")


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


@pytest.fixture(scope="module")
def book():
    return ec.get_error_code_book()


class _NoDetector:
    async def detect(self, image):
        return []


def _talk(kb, turns, ask_last=False):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    pipeline._conversations = ConversationStore()

    async def run():
        replies, session = [], None
        for i, text in enumerate(turns):
            if ask_last and i == len(turns) - 1:
                reply = await pipeline.answer(ChatRequest(question=text, sessionId=session))
            else:
                reply = await pipeline.diagnose(DiagnosisRequest(description=text, sessionId=session))
            session = reply.session_id
            replies.append(reply)
        return replies

    return asyncio.run(run())


def _said(reply) -> str:
    return getattr(reply, "message_vi", None) or getattr(reply, "answer_vi", None) or ""


# ------------------------------------------------------------------ the table


def test_every_table_comes_from_the_manufacturer_with_its_link():
    for table in RAW["tables"]:
        assert table["source"]["url"].startswith(OFFICIAL), table["brand"]
        assert table["source"]["title"] and table["source"]["read_on"]
        for code, entry in table["codes"].items():
            assert entry["meaning_en"] and entry["meaning_vi"], (table["brand"], code)


def test_mapped_faults_exist_for_the_tables_appliance(kb):
    for table in RAW["tables"]:
        own = {f.fault_code for f in kb.faults_for_device(table["device_type"])}
        for code, entry in table["codes"].items():
            assert set(entry.get("faults", [])) <= own, (table["brand"], code)


def test_no_code_is_listed_twice_in_a_table(book):
    for table in RAW["tables"]:
        names = [n.upper() for code, e in table["codes"].items() for n in [code, *e.get("same_as", [])]]
        assert len(names) == len(set(names)), table["brand"]


# ------------------------------------------------------------------ reading


@pytest.mark.parametrize(
    "text, brand, device, token",
    [
        ("máy lạnh Daikin báo lỗi U4", "daikin", "air_conditioner", "U4"),
        ("máy giặt samsung báo 4E", "samsung", "washing_machine", "4E"),
        ("máy giặt lg hiện chữ dL", "lg", "washing_machine", "DL"),
        ("may giat lg bao loi oe", "lg", "washing_machine", "OE"),
        ("máy giặt Samsung nháy UE hoài", "samsung", "washing_machine", "UE"),
    ],
)
def test_a_code_from_the_table_is_read(book, text, brand, device, token):
    reading = book.read(text, book.brand_in(text), device)
    assert reading and reading.entry and reading.token == token and reading.table.brand == brand


@pytest.mark.parametrize(
    "text, device",
    [
        ("máy giặt samsung không vắt de lâu quá", "washing_machine"),  # "de" is "để"
        ("máy giặt lg giặt 5p là dừng", "washing_machine"),
        ("máy lạnh daikin không mát", "air_conditioner"),
        ("tivi samsung báo lỗi 4C", "television"),  # no Samsung TV table
        ("máy giặt UE rung mạnh", "washing_machine"),  # no cue, no brand
    ],
)
def test_words_that_only_look_like_codes_are_left_alone(book, text, device):
    assert book.read(text, book.brand_in(text), device) is None


def test_a_code_not_in_the_table_is_said_to_be_unknown(book):
    reading = book.read("máy giặt LG báo lỗi Z9", "lg", "washing_machine")
    assert reading.entry is None
    assert "không đoán" in ec.reply_vi(reading, False)


# ------------------------------------------------------------------ in a conversation


def test_the_customer_gets_the_brands_meaning_and_its_advice(kb):
    (reply,) = _talk(kb, ["máy giặt LG báo lỗi OE"])
    said = _said(reply)
    assert "Theo bảng mã lỗi của LG, mã OE là nước không xả ra được." in said
    assert "Hãng hướng dẫn: vệ sinh bộ lọc xả" in said
    assert "khác tùy dòng máy" in said
    assert "Máy LG báo mã OE: nước không xả ra được (theo tài liệu hãng)." in reply.notes_vi


def test_the_code_moves_its_fault_up(kb):
    (with_code,) = _talk(kb, ["máy giặt Samsung báo lỗi 4C"])
    assert with_code.suspected_faults[0].fault_code == "WM_NO_WATER_INLET"


def test_no_brand_means_a_question_then_the_answer(kb):
    first, second = _talk(kb, ["máy giặt báo lỗi 4C", "hãng samsung ạ"])
    assert "máy hãng gì" in _said(first)
    assert "mã 4C là máy không có nước cấp vào" in _said(second)


def test_each_code_is_explained_once_and_a_new_one_is_read_without_a_cue(kb):
    replies = _talk(kb, ["máy lạnh Daikin báo lỗi U4", "nó vẫn báo lỗi U4", "còn U0 thì sao"])
    said = [_said(r) for r in replies]
    assert sum("mã U4 là" in s for s in said) == 1
    assert "mã U0 là thiếu môi chất lạnh" in said[2]


def test_the_question_path_answers_codes_too(kb):
    (reply,) = _talk(kb, ["máy lạnh daikin báo lỗi U0 là sao em"], ask_last=True)
    assert "mã U0 là thiếu môi chất lạnh" in _said(reply)


def test_during_a_danger_warning_only_the_meaning_is_given(book):
    reading = book.read("máy giặt LG báo lỗi OE", "lg", "washing_machine")
    assert "Hãng hướng dẫn" not in ec.reply_vi(reading, urgent=True)


def test_nothing_changes_without_a_code(kb):
    (reply,) = _talk(kb, ["máy giặt không xả nước"])
    assert "bảng mã" not in _said(reply)
    assert not any("báo mã" in n for n in reply.notes_vi)
