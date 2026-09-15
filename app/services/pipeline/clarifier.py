# app/services/pipeline/clarifier.py
"""Decide what to ask when the diagnosis is not settled.

A fixed list of questions is a form, not a conversation. "Thiết bị gặp sự cố là
loại nào?" is useless once a photo has already identified the device, and
"Hiện tượng bắt đầu từ khi nào?" rarely separates one fault from another.

A useful question is one whose answer eliminates candidates. If the shortlist is
low refrigerant and a dirty filter, the only question worth asking is whether
the unit was cleaned recently, because either answer removes one of them. If the
shortlist is a single fault, there is nothing to separate and the question
should instead confirm it.

Questions are derived from the symptoms already written in the knowledge base
rather than authored separately, so adding a fault brings its questions with it
and the two cannot drift apart.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from app.services.pipeline.knowledge_base import Discriminator, Fault

MAX_QUESTIONS = 3


@dataclass(frozen=True)
class Question:
    text_vi: str
    symptom_vi: str
    """The symptom being asked about, so a client can send the answer back."""

    splits: int
    """How many candidates this would eliminate. Higher separates better."""


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d")


def _already_said(symptom: str, description: str) -> bool:
    """Skip what the customer has already told us, in any spelling.

    Asking "có kêu cộc cộc không?" right after someone wrote "quạt kêu cộc cộc"
    reads as not having listened, which costs more trust than the question
    gains information.
    """
    folded = _fold(description)
    symptom_folded = _fold(symptom)
    if symptom_folded in folded:
        return True
    words = [w for w in symptom_folded.split() if len(w) > 2]
    if not words:
        return False
    # Most of the symptom's meaningful words present counts as said.
    hits = sum(1 for w in words if w in folded)
    return hits / len(words) >= 0.75


def _phrase(symptom: str) -> str:
    """Turn a symptom into something a person would actually ask."""
    return f"Thiết bị có hiện tượng {symptom} không?"


def build_questions(
    candidates: Sequence[Fault],
    description: str,
    limit: int = MAX_QUESTIONS,
    discriminators: Sequence[Discriminator] = (),
) -> List[Question]:
    """Rank questions by how evenly they divide the candidates.

    A symptom that every candidate shares tells us nothing; neither does one no
    candidate has. The useful ones sit in between, and a symptom held by roughly
    half the shortlist is the single most informative thing to ask about.
    """
    if not candidates:
        return []

    if len(candidates) == 1:
        return _confirmation_questions(candidates[0], description, limit)

    # Hand-written questions first. One whose two sides both intersect the
    # shortlist is guaranteed to eliminate something, which no templated
    # question can promise.
    chosen = _from_discriminators(candidates, discriminators, limit)
    if len(chosen) >= limit:
        return chosen

    total = len(candidates)
    scored: List[Question] = []
    seen: set[str] = set()

    for fault in candidates:
        for symptom in fault.symptoms_vi:
            key = _fold(symptom)
            if key in seen or _already_said(symptom, description):
                continue
            seen.add(key)

            holders = sum(1 for c in candidates if symptom in c.symptoms_vi)
            if holders == total:
                continue  # shared by everything, answering changes nothing

            # Distance from an even split, inverted so an even split ranks top.
            balance = total - abs(total - 2 * holders)
            scored.append(
                Question(text_vi=_phrase(symptom), symptom_vi=symptom, splits=balance)
            )

    scored.sort(key=lambda q: (-q.splits, q.text_vi))
    asked = {q.text_vi for q in chosen}
    return chosen + [q for q in scored if q.text_vi not in asked][: limit - len(chosen)]


def _from_discriminators(
    candidates: Sequence[Fault],
    discriminators: Sequence[Discriminator],
    limit: int,
) -> List[Question]:
    shortlist = {c.fault_code for c in candidates}
    scored: List[Question] = []

    for entry in discriminators:
        yes = shortlist & set(entry.favours_if_yes)
        no = shortlist & set(entry.favours_if_no)
        if not yes or not no:
            # One side touches nothing on the shortlist, so an answer on that
            # side rules nothing out and the question is wasted.
            continue
        scored.append(
            Question(
                text_vi=entry.question_vi,
                symptom_vi=entry.question_vi,
                splits=min(len(yes), len(no)) * 10,
            )
        )

    scored.sort(key=lambda q: (-q.splits, q.text_vi))
    return scored[:limit]


def _confirmation_questions(
    fault: Fault, description: str, limit: int
) -> List[Question]:
    """One candidate left: ask for the symptoms that would confirm it."""
    questions = [
        Question(text_vi=_phrase(symptom), symptom_vi=symptom, splits=1)
        for symptom in fault.symptoms_vi
        if not _already_said(symptom, description)
    ]
    return questions[:limit]


def device_questions(device_name_vi: Optional[str]) -> List[str]:
    """Fallback when nothing was retrieved at all.

    Generic, but not the same generic in both cases: with a device identified
    from the photo there is no point asking what the device is.
    """
    if device_name_vi:
        return [
            f"{device_name_vi} bắt đầu có hiện tượng này từ khi nào?",
            "Hiện tượng xảy ra liên tục hay thỉnh thoảng?",
            "Thiết bị có phát ra tiếng động, mùi lạ hoặc rò rỉ gì không?",
        ]
    return [
        "Thiết bị gặp sự cố là loại nào?",
        "Hiện tượng bắt đầu từ khi nào và xảy ra liên tục hay thỉnh thoảng?",
        "Thiết bị có phát ra tiếng động, mùi lạ hoặc rò rỉ gì không?",
    ]


def texts(questions: Iterable[Question]) -> List[str]:
    return [q.text_vi for q in questions]
