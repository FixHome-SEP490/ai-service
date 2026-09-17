"""Aggregate floors for retrieval, so a tuning change cannot quietly cost recall.

Every other test in this suite asserts one behaviour on one message. That is
the right shape for a rule and the wrong shape for a ranking function: BM25
constants, stopword lists and weighting schemes trade cases against each other,
and a change that fixes the message someone happened to write a test for while
breaking forty others passes a suite of individual assertions.

So the numbers are asserted in bulk, from two sources that were not written to
flatter the retriever. The case suite in tools/chat_cases.py is how customers
were observed to write. The second source is the corpus itself: every fault
file lists, in quotation marks, the phrasings that fault arrives as, and those
were written per fault by someone thinking about the trade rather than about
scoring.

The floors sit a little below what the code currently scores. They are a
regression alarm, not a target -- except the two that are set at exactly one,
where a miss is a defect rather than a shortfall.
"""

from __future__ import annotations

from typing import Dict, List

import pytest

from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.retriever import Retriever
from tools.chat_cases import CASES
from tools.eval_retrieval import run_case
from tools.sync_symptoms import phrases_by_fault


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


@pytest.fixture(scope="module")
def retriever(kb):
    return Retriever(kb)


@pytest.fixture(scope="module")
def results(kb, retriever):
    return [run_case(kb, retriever, case) for case in CASES]


def _rate(values) -> float:
    scored = [v for v in values if v is not None]
    assert scored, "không có ca nào được chấm"
    return sum(1 for v in scored if v) / len(scored)


def _failures(results, attr) -> List[str]:
    return [r.case.text for r in results if getattr(r, attr) is False]


# -- the observed case suite -----------------------------------------------


def test_the_case_suite_is_big_enough_to_mean_something():
    """A hundred cases was the point at which a single fix stopped moving the
    number by a percent and started moving it by a tenth of one."""
    assert len(CASES) >= 120


def test_most_messages_reach_the_right_fault(results):
    rate = _rate([r.shortlist_ok for r in results])
    assert rate >= 0.95, f"{rate:.0%}, trượt: {_failures(results, 'shortlist_ok')}"


def test_most_messages_reach_the_written_explanation(results):
    rate = _rate([r.corpus_ok for r in results])
    assert rate >= 0.90, f"{rate:.0%}, trượt: {_failures(results, 'corpus_ok')}"


def test_every_dangerous_message_gets_its_warning_pinned(results):
    """No floor on this one. Missing a warning is not a shortfall in a rate."""
    assert not _failures(results, "pin_ok")


def test_nothing_is_retrieved_for_an_off_topic_message(results):
    """Also no floor. A passage is treated downstream as something the answer
    may be built from, so confident prose about an air conditioner in reply to
    "hôm nay ăn gì ngon" is worse than an empty hand."""
    assert not _failures(results, "silence_ok")


# -- the corpus checked against itself --------------------------------------


def _high_urgency_phrasings(kb) -> Dict[str, List[str]]:
    """Extracted by the same code the sync tool uses, deliberately.

    A second copy of the regex here quietly disagreed with the tool's: written
    with a length bound inside the pattern instead of after it, it could begin
    a match at a closing quotation mark and pair every quote in the section
    with the wrong partner, which made a line of ordinary prose look like
    something a customer had said.
    """
    high = {
        fault.fault_code: fault
        for device in kb.device_types
        for fault in kb.faults_for_device(device)
        if fault.urgency.upper() == "HIGH"
    }
    harvested = phrases_by_fault()
    quoted = {code: harvested[code] for code in high if code in harvested}
    missing = sorted(set(high) - set(quoted))
    assert not missing, f"bệnh khẩn không có mục trích lời khách: {missing}"
    return quoted


def _device_of(kb, code: str) -> str:
    return next(
        f.device_type
        for d in kb.device_types
        for f in kb.faults_for_device(d)
        if f.fault_code == code
    )


def test_no_dangerous_phrasing_is_met_with_silence(kb, retriever):
    """The failure that has no recovery.

    An empty shortlist pins no warning and retrieves no prose, so the model is
    left to answer a burst pipe from nothing. Landing on a neighbouring fault
    of the same appliance is survivable -- the customer is asked a question and
    the right fault comes back on the second message. Landing on nothing is
    not, because there is no second message worth having.
    """
    silent = [
        phrase
        for code, phrases in _high_urgency_phrasings(kb).items()
        for phrase in phrases
        if not retriever.candidate_faults(phrase, _device_of(kb, code), top_k=3)
    ]
    assert not silent, f"không trả về gì cho: {silent}"


def test_dangerous_phrasings_mostly_reach_their_own_fault(kb, retriever):
    hits = total = 0
    missed = []
    for code, phrases in _high_urgency_phrasings(kb).items():
        device = _device_of(kb, code)
        for phrase in phrases:
            total += 1
            shortlist = [
                s.fault.fault_code
                for s in retriever.candidate_faults(phrase, device, top_k=3)
            ]
            if code in shortlist:
                hits += 1
            else:
                missed.append(f"{phrase!r} -> {shortlist}")
    assert hits / total >= 0.95, f"{hits}/{total}; trượt: {missed}"


def test_symptoms_stay_in_step_with_the_corpus():
    """Editing a fault file without re-running the sync is the way this drifts
    back. It drifted once already, far enough that two HIGH faults could not be
    reached by the words the corpus itself said customers use."""
    kb_data = get_knowledge_base()
    harvested = phrases_by_fault()
    behind = []
    for device in kb_data.device_types:
        for fault in kb_data.faults_for_device(device):
            have = {p.casefold() for p in fault.symptoms_vi}
            missing = [
                p for p in harvested.get(fault.fault_code, []) if p.casefold() not in have
            ]
            if missing:
                behind.append(f"{fault.fault_code} thiếu {len(missing)}")
    assert not behind, f"chạy python tools/sync_symptoms.py --write — {behind}"
