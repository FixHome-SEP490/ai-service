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

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from app.services.pipeline.knowledge_base import Discriminator, Fault

MAX_QUESTIONS = 1
"""One question a turn.

Three at once is a form, not a conversation. Nobody answers three; they answer
the first and ignore the rest, or they answer none and leave. The ranking
already knows which single question separates the shortlist best — asking that
one and waiting is the whole point of having ranked them.

The device either/or is allowed alongside it, because that one settles which
appliance is being discussed and the other settles what is wrong with it.
"""


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
    if hits / len(words) >= 0.75:
        return True

    # A long question is answered when any one of its clauses already is.
    # "Có mùi khét hoặc thấy vết cháy đen ở ổ cắm không?" came back to someone
    # who had written "ổ cắm bị cháy đen, có mùi khét": every clause of it was
    # in their sentence, but spread over enough words to stay under the
    # threshold above.
    return any(_clause_said(part, folded) for part in _CLAUSE_SPLIT.split(symptom_folded))


_CLAUSE_SPLIT = re.compile(r"(?:hoac|hay|va|,|;)|,")


def _clause_said(clause: str, folded_description: str) -> bool:
    words = [w for w in clause.split() if len(w) > 2]
    # Two words or more, so "có" or "không" alone cannot match everything.
    if len(words) < 2:
        return False
    return all(w in folded_description for w in words)


_NEGATIONS = ("khong", "ko", "chua", "chang", "chal")
_NEGATION_SCOPE = 4
"""How many words after a negation it is taken to cover.

"Máy nước nóng nhà em không nóng" negates "nóng". Four words is enough for
"không nóng lên được nữa" and short enough that the next clause does not get
swept in."""


def _negated_words(description: str) -> set[str]:
    """Words the customer has said are NOT happening.

    Asked "máy nước nóng không nóng", the shortlist still holds a fault whose
    symptom is "nóng chậm hơn trước", and asking about it produced "Nước có
    nóng nhưng lâu hơn trước phải không?" — contradicting the sentence it was
    replying to. A customer reads that as not having been listened to, and they
    are right.
    """
    folded = _fold(description).split()
    negated: set[str] = set()
    for index, word in enumerate(folded):
        if word in _NEGATIONS:
            negated.update(
                w for w in folded[index + 1 : index + 1 + _NEGATION_SCOPE] if len(w) > 2
            )
    return negated


def _contradicts(symptom: str, negated: set[str]) -> bool:
    """Whether asking this would argue with what the customer already said.

    Both directions are caught, and both should be. A symptom asserting a word
    the customer negated contradicts them; one negating the same word repeats
    them. Neither is worth a turn.
    """
    if not negated:
        return False
    return any(w in negated for w in _fold(symptom).split() if len(w) > 2)


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
    chosen = _from_discriminators(candidates, discriminators, limit, description)
    if len(chosen) >= limit:
        return chosen

    total = len(candidates)
    scored: List[Question] = []
    seen: set[str] = set()
    negated = _negated_words(description)

    for fault in candidates:
        for symptom in fault.symptoms_vi:
            key = _fold(symptom)
            if key in seen or _already_said(symptom, description):
                continue
            if _contradicts(symptom, negated):
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
    return _take_distinct(chosen, scored, limit)


_SAME_QUESTION = 0.7
"""Word overlap above which two questions are asking the same thing.

"bật đèn nhưng nước lạnh" and "bật đèn đỏ mà nước lạnh" are different strings
and one question. Both came back in the same reply, which reads as padding out
a list rather than wanting to know something."""


def _take_distinct(
    chosen: List[Question], rest: List[Question], limit: int
) -> List[Question]:
    """Fill up to the limit, skipping anything that repeats a question already in."""
    out = list(chosen)
    for question in rest:
        if len(out) >= limit:
            break
        if any(_overlap(question.symptom_vi, k.symptom_vi) >= _SAME_QUESTION for k in out):
            continue
        out.append(question)
    return out


def _overlap(left: str, right: str) -> float:
    a = {w for w in _fold(left).split() if len(w) > 2}
    b = {w for w in _fold(right).split() if len(w) > 2}
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _from_discriminators(
    candidates: Sequence[Fault],
    discriminators: Sequence[Discriminator],
    limit: int,
    description: str = "",
) -> List[Question]:
    shortlist = {c.fault_code for c in candidates}
    scored: List[Question] = []
    # Hand-written questions are chosen first and were the only ones not
    # checked against what the customer said. That is how "Nước có nóng nhưng
    # lâu hơn trước phải không?" came back twice to someone who had opened with
    # "máy nước nóng không nóng".
    negated = _negated_words(description)

    for entry in discriminators:
        if _already_said(entry.question_vi, description) or _contradicts(
            entry.question_vi, negated
        ):
            continue
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
    negated = _negated_words(description)
    questions = [
        Question(text_vi=_phrase(symptom), symptom_vi=symptom, splits=1)
        for symptom in fault.symptoms_vi
        if not _already_said(symptom, description)
        and not _contradicts(symptom, negated)
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
