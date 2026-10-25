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

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from typing import List, Optional, Sequence

from app.services.pipeline.knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class DeviceHint:
    device_type: str
    matched_alias: str
    """The words that produced this, so a log shows why rather than just what."""


@lru_cache(maxsize=65536)
def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    return " " + stripped.replace("đ", "d") + " "


NOT_THIS_DEVICE = {
    # "tu say" and "gian phoi" are a drying cabinet and a clothes airer: they
    # dry clothes, they are sold under the same search terms, and they are not
    # the machine the 350.000d service cleans — that one has a lint filter, a
    # vent duct and a drum, none of which a fabric tent has.
    # The dish, shoe and hand dryers are named with "sấy" in front: as bare
    # words "bát" also folds from "bất" and "tay" sits in "vân tay", so "máy sấy
    # nóng bất thường" was taken back as a dish dryer and named no appliance.
    "clothes_dryer": (
        "toc", "say bat", "say chen", "bat dia", "chen bat", "say giay", "say tay",
        "quat suoi", "tu say", "gian phoi", "mac phoi", "sao phoi",
    ),
    "water_heater": ("nuoc nong lanh", "binh thuy"),
    "electric_fan": ("quat thong gio", "quat hut mui"),
}
"""Words that take an alias back, keyed by the device the alias belongs to.

"Máy sấy" is a clothes dryer, a hair dryer, a dish dryer and a shoe dryer, and
the alias list could only claim one of them. It claimed the clothes dryer, so
"máy sấy tóc bị cháy khét" came back as a tumble dryer — and since a clogged
dryer is a fire risk, the answer was a four-step fire warning about a hair
dryer somebody was holding.

Matched as whole words on the tone-stripped text, for the reason every other
list in this project is: three-letter fragments collide constantly. "Tóc" folds
to "toc", which is not a substring of anything that matters here, but the rule
holds anyway because the next entry added will not be so lucky.
"""


def _disqualified(device_type: str, folded: str) -> bool:
    """Whether something in the text says this is not that device."""
    words = _folded_words(folded)
    for phrase in NOT_THIS_DEVICE.get(device_type, ()):
        if f" {phrase} " in words:
            return True
    return False


def _overlaps_a_disqualifier(device_type: str, folded: str, alias: str) -> bool:
    """Whether a disqualifier is built out of the same words as the alias.

    Length was the original test for this, and length is the wrong signal.
    "Tủ sấy quần áo" is a drying cabinet: the alias "sấy quần áo" is three words
    and the disqualifier "tủ sấy" is two, so the longer, more specific-looking
    phrase was the wrong one, and the cabinet came back as a tumble dryer with
    a tumble dryer's lint-fire warning.

    What actually separates the two cases is whether they occupy the same words.
    In "tủ sấy quần áo" the disqualifier and the alias share "sấy" — it is one
    phrase, and the first two words say which. In "máy sấy quần áo và máy sấy
    tóc" the disqualifier sits somewhere else in the sentence, describing a
    second appliance, and the alias still means what it says.
    """
    words = _folded_words(folded)
    start = words.find(f" {alias} ")
    if start < 0:
        return False
    alias_span = (start, start + len(alias) + 2)

    for phrase in NOT_THIS_DEVICE.get(device_type, ()):
        at = words.find(f" {phrase} ")
        while at >= 0:
            if at < alias_span[1] and at + len(phrase) + 2 > alias_span[0]:
                return True
            at = words.find(f" {phrase} ", at + 1)
    return False


@lru_cache(maxsize=16384)
def _folded_words(folded: str) -> str:
    """The folded text reduced to space-separated words, padded at both ends."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "


_FALSE_FRIENDS = {"bật": "batt"}
"""Typed words that fold onto a disqualifier and mean something else.

"Máy sấy bật lên không thấy gì chạy" folds to "may say bat len", which holds
"say bat", the dish dryer; a clothes dryer that would not start was taken back
as a dish dryer and named no appliance at all. Where the customer typed the
accent, the word is kept apart before folding."""


def _keep_false_friends_apart(text: str) -> str:
    words = re.split(r"(\W+)", unicodedata.normalize("NFC", text.lower()))
    return "".join(_FALSE_FRIENDS.get(w, w) for w in words)


def devices_named_in(description: str, kb: KnowledgeBase) -> List[DeviceHint]:
    """Every device the text names, longest alias first.

    Longest first because "máy giặt cửa trên" contains "máy giặt", and reporting
    the more specific match makes the reason legible.

    A device whose name is taken back by a later word is dropped entirely: see
    NOT_THIS_DEVICE. That is deliberately stronger than ranking it lower, since
    the wrong appliance carries the wrong faults, the wrong prices and — in at
    least one case — the wrong safety warning.
    """
    folded = _fold(_keep_false_friends_apart(description))
    hits: List[DeviceHint] = []

    for device_type in kb.device_types:
        best: Optional[str] = None
        for alias in kb.aliases_vi(device_type):
            if _fold(alias).strip() in folded and (
                best is None or len(alias) > len(best)
            ):
                best = alias
        if best is None:
            continue
        # The specific alias survives a disqualifier elsewhere in the sentence:
        # somebody who typed "máy sấy quần áo" has said which one they mean,
        # whatever else they went on to mention. But not one built out of the
        # same words — "tủ sấy quần áo" is the alias with a different first
        # word, and that first word is the whole meaning.
        folded_alias = _fold(best).strip()
        if _overlaps_a_disqualifier(device_type, folded, folded_alias):
            continue
        if len(best.split()) < 3 and _disqualified(device_type, folded):
            continue
        hits.append(DeviceHint(device_type=device_type, matched_alias=best))

    hits.sort(key=lambda h: -len(h.matched_alias))
    if not hits:
        # Nothing on the alias list. People also say "tủ Toshiba", "con
        # Daikin", "máy giặc": the brand or a slip of the keyboard, not a
        # missing word. Tried only now, so no alias match is ever overruled.
        hits = _by_name(folded, kb) or _by_brand(folded, kb) or _misspelt(folded, kb)
    return hits


def known_names() -> dict:
    """{device: [folded names]} from device_naming.json "names": what customers
    call an appliance beyond its aliases ("máy thổi gió", "bệt", "con MRB")."""
    return {d: tuple(n.split() for n in names) for d, names in _naming_names().items()}


@lru_cache(maxsize=1)
def _naming_names() -> dict:
    if not _NAMING_PATH.exists():
        return {}
    data = json.loads(_NAMING_PATH.read_text(encoding="utf-8"))
    return {d: tuple(_fold(n).strip() for n in names) for d, names in data.get("names", {}).items()}


def _by_name(folded: str, kb: KnowledgeBase) -> List[DeviceHint]:
    """The appliance one of its known names stands for, as whole words, when
    the names found point at exactly one appliance (the longest wins)."""
    padded = " " + _folded_words(folded) + " "
    known = set(kb.device_types)
    best: dict = {}
    for device, names in _naming_names().items():
        if device not in known:
            continue
        for name in names:
            if name and f" {name} " in padded and len(name) > len(best.get(device, "")):
                best[device] = name
    if not best:
        return []
    longest = max(best.values(), key=len)
    devices = {d for d, n in best.items() if n == longest}
    if len(devices) != 1:
        return []
    device = devices.pop()
    return [DeviceHint(device_type=device, matched_alias=longest)]


_NAMING_PATH = Path(__file__).resolve().parents[2] / "data" / "device_naming.json"
_CLASSIFIERS = ("con", "cai", "chiec", "may", "bo", "cay")


@lru_cache(maxsize=1)
def _naming() -> dict:
    if not _NAMING_PATH.exists():
        return {"brands": {}, "heads": {}, "cues": {}}
    data = json.loads(_NAMING_PATH.read_text(encoding="utf-8"))
    return {
        key: {tuple(k.split()): tuple(v) for k, v in data.get(key, {}).items()}
        for key in ("brands", "heads", "cues")
    }


def _spans(tokens: List[str], phrase: tuple) -> List[int]:
    n = len(phrase)
    return [i for i in range(len(tokens) - n + 1) if tuple(tokens[i : i + n]) == phrase]


def _by_brand(folded: str, kb: KnowledgeBase) -> List[DeviceHint]:
    """The appliance a brand names, once the words around it leave only one.

    "Con Daikin" is an air conditioner: Daikin makes nothing else we repair.
    "Tủ Toshiba" is a fridge, because "tủ" is said only of the fridge among
    the appliances Toshiba makes. "Con Electrolux cửa trước" is a washing
    machine. "Cái Panasonic" stays unknown and the customer is asked, since
    Panasonic makes ten of them."""
    naming = _naming()
    tokens = _folded_words(folded).split()
    known = set(kb.device_types)
    found: List[DeviceHint] = []
    for brand, makes in naming["brands"].items():
        for at in _spans(tokens, brand):
            candidates = [d for d in makes if d in known]
            start = at
            # The word naming the kind of thing comes just before the brand:
            # "tủ Toshiba", "bếp từ Bosch", "cái quạt Mitsubishi".
            best_head: Optional[tuple] = None
            for head in naming["heads"]:
                for h in _spans(tokens[max(0, at - 4) : at], head):
                    end = max(0, at - 4) + h + len(head)
                    if end <= at and (best_head is None or len(head) > len(best_head)):
                        best_head, start = head, max(0, at - 4) + h
            if best_head is not None:
                narrowed = [d for d in candidates if d in naming["heads"][best_head]]
                candidates = narrowed or candidates
            if len(candidates) > 1:
                rest = tokens[:start] + tokens[at + len(brand) :]
                for cue, points_to in naming["cues"].items():
                    if _spans(rest, cue):
                        narrowed = [d for d in candidates if d in points_to]
                        candidates = narrowed or candidates
            if len(candidates) == 1:
                found.append(
                    DeviceHint(device_type=candidates[0], matched_alias=" ".join(tokens[start : at + len(brand)]))
                )
    devices = {h.device_type for h in found}
    return found if len(devices) == 1 else []


def _one_edit(a: str, b: str) -> int:
    """Edit distance between two short words, stopping once past one."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 1:
        return 2
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _misspelt(folded: str, kb: KnowledgeBase) -> List[DeviceHint]:
    """An alias typed with one letter wrong: "máy giặc", "đìu hòa", "bồn càu".

    Only aliases of two words or more and six letters or more, only with the
    first letter right, and only when every such near miss points at the same
    appliance. A one-letter slip in a short word is a different word too often
    to guess at."""
    tokens = _folded_words(folded).split()
    devices = set()
    hits: List[DeviceHint] = []
    for device_type in kb.device_types:
        for alias in kb.aliases_vi(device_type):
            words = _fold(alias).split()
            if len(words) < 2 or sum(len(w) for w in words) < 6:
                continue
            n = len(words)
            for i in range(len(tokens) - n + 1):
                window = tokens[i : i + n]
                if window[0][:1] != words[0][:1]:
                    continue
                edits = [(_one_edit(x, y), y) for x, y in zip(window, words)]
                # The slip has to be in a word long enough to keep its identity:
                # "quạt gắn" is one letter from "quạt bàn" and means a ceiling.
                if sum(e for e, _ in edits) == 1 and all(len(y) >= 4 for e, y in edits if e):
                    devices.add(device_type)
                    hits.append(DeviceHint(device_type=device_type, matched_alias=" ".join(window)))
                    break
    return hits[:1] if len(devices) == 1 else []


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



_NEGATORS = {"khong", "ko", "k", "chang", "chua", "dau"}
"""Words that turn a mention into its opposite, checked as whole words.

The question asks about something visible and the reply mentions it — but half
the time to deny it. "Không phải trần đâu ạ" contains the word the ceiling fan
question was written to elicit, and matching on the word alone read that as a
yes: the three commonest pairs in the catalogue, the fan, the sink and the
socket, all resolved to exactly the wrong one of the two.

Whole words, not substrings, and only just before the phrase. "Ko" inside
another word, or a "không" from the start of a long sentence, would put the
same fault back in a harder place to see.
"""

_NEGATION_WINDOW = 24
"""How far back a negator still governs the phrase, in characters.

Long enough for "nhà em không dùng ..." and short enough that a denial about
something else earlier in the sentence does not reach across.
"""


def _negated(folded: str, phrase: str) -> bool:
    """Whether the reply denies the phrase rather than confirming it.

    "Không rõ" is excluded on purpose. It is not a denial, it is the customer
    saying they cannot tell, and treating it as one would answer the question
    for them — so "em không rõ, chắc là quạt trần" stays a ceiling fan.
    """
    index = folded.find(phrase)
    if index < 0:
        return False
    before = folded[max(0, index - _NEGATION_WINDOW):index]
    if any(unsure in before for unsure in _UNSURE):
        return False
    return bool(set(before.split()) & _NEGATORS)


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

    folded = _fold(answer)

    named = devices_named_in(answer, kb)
    for hint in named:
        if hint.device_type not in question.devices:
            continue
        if not _negated(folded, _fold(hint.matched_alias).strip()):
            return hint.device_type
        # They named it to rule it out. "Không có bình gas" names the gas
        # stove by one of its own aliases, and reading that as the answer
        # picked the appliance the customer had just denied.
        others = [d for d in question.devices if d != hint.device_type]
        if len(others) == 1:
            return others[0]
        return None  # three choices and one ruled out still leaves two

    # A denial of the phrase answers the question just as well as a
    # confirmation of it, and in the opposite direction. `or None` throughout,
    # because a question offering three choices leaves both of these empty and
    # an empty string is not a device.
    for word in question.yes_words_vi:
        phrase = _fold(word).strip()
        if phrase in folded:
            if _negated(folded, phrase):
                return question.if_no or None
            return question.if_yes or None
    for word in question.no_words_vi:
        phrase = _fold(word).strip()
        if phrase in folded:
            if _negated(folded, phrase):
                return question.if_yes or None
            return question.if_no or None

    # "Không rõ" before anything else: it carries a negative word and is not a
    # negative answer, and reading it as one settles the appliance from an
    # answer the customer did not give.
    if any(phrase in folded for phrase in _UNSURE):
        return None

    # A bare yes or no, after dropping the particles a reply opens with.
    # Negative first, because "không có" contains "có".
    words = [w for w in folded.split() if w not in _POLITE]
    if any(w in _NO for w in words):
        return question.if_no or None
    if any(w in _YES for w in words):
        return question.if_yes or None
    return None
