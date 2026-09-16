# app/services/pipeline/device_hint.py
"""Read the device from what the customer already wrote.

A microwave and an oven are hard to tell apart in a photograph, and a person
looking at the same picture often cannot either. The detector should not be
pushed to resolve that: the customer usually just says which it is.

So the description is read first. If it names a device, that is the answer and
nothing is asked. Only when the detector lands on one of a confusable pair and
the text names neither is a question worth a turn — and then exactly one
question, phrased as a choice rather than an interrogation.

This is where "ask the customer" stops being a habit and becomes a decision:
asking about something already said is the fastest way to make a support bot
feel like it is not listening.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.services.pipeline.knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class DeviceHint:
    device_type: str
    matched_alias: str
    """The words that produced this, so a log shows why rather than just what."""


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    return " " + stripped.replace("đ", "d") + " "


def devices_named_in(description: str, kb: KnowledgeBase) -> List[DeviceHint]:
    """Every device the text names, longest alias first.

    Longest first because "máy giặt cửa trên" contains "máy giặt", and reporting
    the more specific match makes the reason legible.
    """
    folded = _fold(description)
    hits: List[DeviceHint] = []

    for device_type in kb.device_types:
        best: Optional[str] = None
        for alias in kb.aliases_vi(device_type):
            if _fold(alias).strip() in folded and (
                best is None or len(alias) > len(best)
            ):
                best = alias
        if best is not None:
            hits.append(DeviceHint(device_type=device_type, matched_alias=best))

    hits.sort(key=lambda h: -len(h.matched_alias))
    return hits


def resolve(
    description: str,
    detected: Optional[str],
    kb: KnowledgeBase,
) -> tuple[Optional[str], Optional[DeviceHint]]:
    """Settle on a device, preferring what the customer said.

    Returns the device to work with and the hint that decided it, if any. The
    text wins over the detector when they disagree: a photograph is ambiguous
    between a microwave and an oven, a sentence saying "lò vi sóng" is not.
    """
    named = devices_named_in(description, kb)
    if not named:
        return detected, None

    if detected is None:
        return named[0].device_type, named[0]

    for hint in named:
        if hint.device_type == detected:
            return detected, hint  # text and photo agree

    # They disagree. Trust the words, but only for a device the detector could
    # plausibly have confused this one with; otherwise the photo is describing
    # something the sentence merely mentioned in passing.
    confusable = set(kb.confusable_with(detected))
    for hint in named:
        if hint.device_type in confusable:
            return hint.device_type, hint

    return detected, None


def confusion_question(
    device_type: Optional[str],
    description: str,
    kb: KnowledgeBase,
) -> Optional[str]:
    """One question, only when the answer is not already in the text.

    Returns None whenever asking would be noise: no device detected, no
    confusable sibling, or the customer already named something.
    """
    if device_type is None:
        return None

    siblings: Sequence[str] = kb.confusable_with(device_type)
    if not siblings:
        return None

    if devices_named_in(description, kb):
        return None  # already told us

    # Prefer the question about something visible. "Bên trong có đĩa xoay
    # không?" is answerable by anyone; "là lò vi sóng hay lò nướng?" is the
    # question they came here unable to answer, handed back to them.
    written = kb.confusion_question(device_type)
    if written is not None:
        return written.question_vi

    options = [device_type, *siblings]
    names = [kb.device_name_vi(o) or o for o in options]
    if len(names) == 2:
        return f"Cho em hỏi thiết bị là {names[0]} hay {names[1]} ạ?"
    listed = ", ".join(names[:-1])
    return f"Cho em hỏi thiết bị là {listed} hay {names[-1]} ạ?"


_YES = {"co", "dung", "phai", "u", "um", "vang", "oke", "ok", "yes"}
_NO = {"khong", "ko", "k", "hong", "chua", "no"}

_UNSURE = (
    "khong ro",
    "khong biet",
    "khong chac",
    "khong nam",
    "chua ro",
    "khong hieu",
    "sao biet",
)
"""Replies that contain a negative word and are not a negative answer.

"Em không rõ lắm" is the customer saying they cannot tell, and reading it as
"no" resolves the appliance from an answer they did not give. Better to leave it
unsettled and let the turn ask again or fall through to a clarification."""

_POLITE = {"da", "vang", "a", "e", "em", "anh", "chi", "the", "thi", "la", "thua"}
"""Words that open a Vietnamese reply without changing it.

"Dạ không" is how the answer actually arrives, and a check that only reads the
first word or the whole string misses every polite one."""


def resolve_confusion_answer(
    answer: str, asked_about: str, kb: KnowledgeBase
) -> Optional[str]:
    """Turn the customer's reply into a device, or None if it settles nothing.

    Three ways a reply can answer. It can name the device outright, which is
    checked first because "lò nướng đó em" ends the matter. It can carry one of
    the words the question was written to elicit — "gắn trên trần". Or it can be
    a bare yes or no, which only means anything against the question that was
    asked, which is why that question has to be remembered.
    """
    question = kb.confusion_question(asked_about)
    if question is None:
        return None

    named = devices_named_in(answer, kb)
    for hint in named:
        if hint.device_type in question.devices:
            return hint.device_type

    folded = _fold(answer)
    for word in question.yes_words_vi:
        if _fold(word).strip() in folded:
            return question.if_yes
    for word in question.no_words_vi:
        if _fold(word).strip() in folded:
            return question.if_no

    # "Không rõ" before anything else: it carries a negative word and is not a
    # negative answer, and reading it as one settles the appliance from an
    # answer the customer did not give.
    if any(phrase in folded for phrase in _UNSURE):
        return None

    # A bare yes or no, after dropping the particles a reply opens with.
    # Negative first, because "không có" contains "có".
    words = [w for w in folded.split() if w not in _POLITE]
    if any(w in _NO for w in words):
        return question.if_no
    if any(w in _YES for w in words):
        return question.if_yes
    return None
