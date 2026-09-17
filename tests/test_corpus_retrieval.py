"""Retrieval over the written corpus, checked as behaviour rather than wiring.

The corpus sat on disk for a while with nothing reading it, so these tests are
mostly about the four decisions that make it reach an answer at all: narrow by
appliance, require a shortlist, keep the authoring notes out, and put the prose
somewhere the model will actually read it.

Scores are asserted as orderings and as floors, never as exact numbers. BM25
constants are tuning, and a test that pins them turns tuning into a breakage.
"""

from __future__ import annotations

import pytest

from app.services.pipeline import context as ctxmod
from app.services.pipeline.conversation import Conversation
from app.services.pipeline.corpus import get_corpus
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.qwen_client import build_context_prompt
from app.services.pipeline.retriever import Retriever


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


@pytest.fixture(scope="module")
def retriever(kb):
    return Retriever(kb)


def _build(kb, retriever, message: str, device_type):
    chat = Conversation(session_id="test")
    chat.add("customer", message)
    candidates = (
        retriever.candidate_faults(message, device_type, top_k=3) if device_type else []
    )
    return ctxmod.build(
        kb,
        retriever,
        chat,
        message,
        device_type,
        "description",
        candidates,
        has_image=False,
    )


# -- the corpus is loaded at all -------------------------------------------


def test_corpus_loads_every_layer():
    kinds = {chunk.doc_type for chunk in get_corpus()}
    assert {"fault", "device", "persona", "system"} <= kinds


def test_corpus_chunks_carry_what_retrieval_filters_on():
    """device_type and fault_code are the filters, so they cannot be blank."""
    for chunk in get_corpus():
        if chunk.doc_type == "fault":
            assert chunk.fault_code, f"{chunk.source_file} thiếu fault_code"
            assert chunk.device_type, f"{chunk.source_file} thiếu device_type"
        if chunk.doc_type == "device":
            assert chunk.device_type, f"{chunk.source_file} thiếu device_type"


# -- narrowing --------------------------------------------------------------


def test_passages_stay_within_the_detected_appliance(retriever):
    """The filter that makes the rest of the scoring mean anything.

    2,380 fault sections discuss noise, smell, heat and what to check first. A
    washing-machine bearing outranked an air-conditioner fan before this.
    """
    hits = retriever.corpus_passages(
        "quat khong quay", device_type="electric_fan", fault_codes=["FAN_CAPACITOR"]
    )
    assert hits
    assert {h.chunk.device_type for h in hits} == {"electric_fan"}


def test_no_shortlist_means_no_passages(retriever):
    """An off-topic message shares no wording with any curated symptom, so the
    shortlist is empty — and that, not a score floor, is what stops it."""
    assert retriever.corpus_passages("hom nay an gi ngon", device_type="oven") == []
    assert retriever.corpus_passages("dat lich sua chua the nao") == []


def test_shortlisted_fault_outranks_its_neighbours(retriever):
    """The shortlist is the strongest signal in the pipeline; prose follows it."""
    hits = retriever.corpus_passages(
        "bep gas nha em co mui gas",
        device_type="gas_stove",
        fault_codes=["STOVE_GAS_LEAK"],
    )
    assert hits
    assert hits[0].chunk.fault_code == "STOVE_GAS_LEAK"


# -- what must never be retrieved ------------------------------------------


def test_the_sourcing_note_is_never_handed_over(retriever):
    """"Nền tri thức của tài liệu này" records which standard a file was written
    from. It is how the corpus stays honest and it is not for a customer."""
    for device, codes in [
        ("gas_stove", ["STOVE_GAS_LEAK"]),
        ("air_conditioner", ["AC_LOW_REFRIGERANT"]),
        ("toilet", ["TOILET_CLOGGED"]),
    ]:
        hits = retriever.corpus_passages(
            "nen tri thuc cua tai lieu nay nguon nao",
            device_type=device,
            fault_codes=codes,
            top_k=20,
            min_score=0.0,
        )
        assert all("Nền tri thức" not in h.chunk.heading_vi for h in hits)


def test_phrasing_lists_are_demoted_not_promoted(retriever):
    """"Khách nói thế nào" is a list of the words customers type, with no advice
    in it. Written from the same vocabulary as the message, it outscores the
    section that explains what to do unless it is held back."""
    hits = retriever.corpus_passages(
        "quat phai lay tay quay moi chay",
        device_type="electric_fan",
        fault_codes=["FAN_CAPACITOR"],
        top_k=3,
    )
    assert hits
    assert not hits[0].chunk.heading_vi.startswith("Khách nói thế nào")


# -- the business layer is kept apart --------------------------------------


def test_business_questions_reach_the_business_layer(retriever):
    for question, expected in [
        ("dat lich sua chua the nao", "quy-trinh-dat-lich.md"),
        ("bao hanh bao lau", "bao-hanh.md"),
    ]:
        hits = retriever.business_passages(question)
        assert hits, question
        assert hits[0].chunk.source_file.endswith(expected)


def test_business_and_fault_passages_do_not_share_a_budget(retriever):
    """A fault question must not spend its passages on the booking flow."""
    hits = retriever.corpus_passages(
        "bon cau bi nghet", device_type="toilet", fault_codes=["TOILET_CLOGGED"]
    )
    assert all(h.chunk.doc_type != "system" for h in hits)


# -- the assembled bundle ---------------------------------------------------


def test_context_carries_prose_for_an_explanatory_question(kb, retriever):
    """The question the corpus was written for.

    Before this the bundle held the fault's name, the phrases customers use for
    it and a price — enough to classify, nothing to explain with.
    """
    ctx = _build(kb, retriever, "vi sao dan lanh bam tuyet", "air_conditioner")
    assert ctx.passages
    assert all(h.chunk.device_type == "air_conditioner" for h in ctx.passages)


def test_prompt_includes_the_retrieved_prose(kb, retriever):
    ctx = _build(kb, retriever, "vi sao dan lanh bam tuyet", "air_conditioner")
    prompt = build_context_prompt(ctx)
    assert "TÀI LIỆU NGHỀ" in prompt
    assert ctx.passages[0].chunk.heading_vi in prompt


def test_prompt_survives_a_context_without_the_new_fields(kb, retriever):
    """Older callers build a context without the corpus fields; the prompt must
    still render rather than raise."""

    class Bare:
        device_name_vi = "Máy lạnh"
        device_type = "air_conditioner"
        device_source_vi = None
        history: list = []
        latest_message = "may lanh khong mat"
        already_asked: list = []
        candidates: list = []
        price_rows: list = []
        policies: list = []

    assert "THIẾT BỊ" in build_context_prompt(Bare())


# -- the question box, not only the photograph -----------------------------


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _ask(client, question: str, device_type=None) -> dict:
    body = {"question": question}
    if device_type:
        body["deviceType"] = device_type
    response = client.post("/api/v1/chat/ask", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_an_explanatory_question_is_answered_from_the_corpus(client):
    """The gap a live run found.

    The corpus was wired into diagnosis and stopped there, so this surface —
    the one a chat box calls — still answered from the small policy table.
    Asked why an evaporator ices up, it explained how often to clean a
    refrigerator: retrieved, true, and about a different appliance.
    """
    body = _ask(client, "vi sao dan lanh bam tuyet", "air_conditioner")
    cited = [c["docId"] for c in body["citations"]]
    assert any(doc.startswith("KB_FAULT_AC") for doc in cited), cited


def test_a_dangerous_question_warns_on_this_surface_too(client):
    """Typing it into the question box is the same room as photographing it."""
    body = _ask(client, "bep gas nha em co mui gas", "gas_stove")
    assert "khoá van bình gas" in body["answerVi"].lower()
    assert body["citations"][0]["docId"] == "KB_FAULT_STOVE_GAS_LEAK"


def test_a_policy_question_still_reaches_policy(client):
    """The corpus must not crowd out the tables it was never meant to replace."""
    body = _ask(client, "bao hanh bao lau")
    assert any(c["docId"].startswith("POLICY") for c in body["citations"])
