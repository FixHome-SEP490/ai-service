# app/services/pipeline/acknowledgement.py
"""What the assistant says in the six seconds before it has an answer.

A diagnosis with a photograph takes several seconds. Six seconds of nothing
after sending a message reads as nobody being there, and a customer who has
just described a broken fridge at ten at night reads silence as being ignored.
So something is said immediately, before the work starts.

Two things make that line worth having a module for.

It has to vary. One fixed sentence repeated on every turn stops being politeness
and starts being a machine noise; a customer who sends three messages and gets
"Dạ em nhận được thông tin rồi ạ" three times has learnt that nobody is reading.
So lines are drawn without repeating within a session.

And it has to fit the turn. A price question does not deserve "em kiểm tra"; it
deserves "để em tra bảng giá". A fourth message is not a first greeting. An
angry customer needs the annoyance acknowledged before anything else. And a
message that smells of live electricity or gas gets no pleasantry at all — the
safety instruction IS the acknowledgement, because it cannot wait for the
pipeline to finish.

The lines live in `app/data/acknowledgements.json` so they can be edited without
touching code, and so the client can fetch the whole set once and pick locally.
Picking locally matters: the point is that the line appears instantly, and a
round trip to ask for it would defeat that.
"""

from __future__ import annotations

import json
import random
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "acknowledgements.json"

Situation = str

_SITUATIONS: Sequence[Situation] = (
    "first_text",
    "first_photo",
    "follow_up",
    "price_question",
    "general_question",
    "before_asking_back",
    "long_wait",
    "customer_upset",
    "urgent_mentioned",
)

_SAFETY_KINDS: Sequence[str] = ("electrical", "gas", "water_on_electrics")


def _fold(text: str) -> str:
    """Lowercase and strip diacritics, so "khét" and "khet" both match.

    Customers type without tone marks constantly, and the safety triggers below
    are the last place where a missing dấu should change the answer.
    """
    stripped = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in stripped if unicodedata.category(ch) != "Mn")


_ELECTRICAL_CUES = (
    "mui khet",
    "khet",
    "chay khet",
    "nhua chay",
    "boc khoi",
    "co khoi",
    "khoi",
    "nhay aptomat",
    "nhay cb",
    "nhay cau dao",
    "nhay at",
    "te tay",
    "giat dien",
    "bi giat",
    "chap dien",
    "toe lua",
    "tia lua",
    "no nho",
)

_GAS_CUES = (
    "mui gas",
    "mui ga",
    "xi gas trong nha",
    "ro gas",
    "ngui mui gas",
    "mui nhu bat quet",
    "mui khi ga",
    "ho gas",
)

_WATER_CUES = (
    "nuoc chay vao o dien",
    "nuoc gan o cam",
    "nuoc vao o cam",
    "uot o dien",
    "nuoc chay vao bang dien",
)

_UPSET_CUES = (
    "buc minh",
    "buc qua",
    "chan qua",
    "qua te",
    "lam an kieu gi",
    "lua dao",
    "gian doi",
    "khong chap nhan",
    "phan nan",
    "that vong",
    "cai gi ky vay",
    "sao ky vay",
    "lan thu may roi",
)

_URGENT_CUES = (
    "gap",
    "gap lam",
    "ngay bay gio",
    "cang som cang tot",
    "trong hom nay",
    "khan",
    "dang can gap",
    "toi nay",
)

_PRICE_CUES = (
    "bao nhieu",
    "bao nhieu tien",
    "gia",
    "nhieu tien",
    "het bao nhieu",
    "chi phi",
    "bang gia",
    "phi",
    "mac khong",
    "re khong",
)


class Acknowledgements:
    """The lines, plus a memory of what each session has already heard."""

    def __init__(self, data: Optional[dict] = None) -> None:
        self._data = data if data is not None else _load()
        self._seen: Dict[str, Dict[Situation, List[str]]] = {}

    # -- selection -------------------------------------------------------

    def pick(
        self,
        *,
        session_id: Optional[str] = None,
        text: str = "",
        has_image: bool = False,
        is_follow_up: bool = False,
        rng: Optional[random.Random] = None,
    ) -> str:
        """The line to show for this turn.

        Safety wins over everything: if the message carries a cue of live
        electricity, escaping gas, or water reaching wiring, the instruction is
        returned instead of a pleasantry. Getting that order wrong is the one
        failure here that matters — a customer reads the first line while the
        thing is still plugged in.
        """
        chooser = rng or random
        safety = self.safety_kind(text)
        if safety is not None:
            lines = self._data["safety_first"][safety]
            return chooser.choice(lines)

        situation = self.situation(
            text=text, has_image=has_image, is_follow_up=is_follow_up
        )
        return self._draw(situation, session_id, chooser)

    def situation(
        self, *, text: str = "", has_image: bool = False, is_follow_up: bool = False
    ) -> Situation:
        """Which bucket this turn falls into.

        Order matters. Upset is checked before anything else that is not safety,
        because a customer who is angry and asking a price wants the annoyance
        acknowledged first; answering their price question briskly reads as not
        having noticed.
        """
        folded = _fold(text)

        if _has_cue(folded, _UPSET_CUES):
            return "customer_upset"
        if _has_cue(folded, _URGENT_CUES):
            return "urgent_mentioned"
        if has_image:
            return "first_photo" if not is_follow_up else "follow_up"
        if is_follow_up:
            return "follow_up"
        if _has_cue(folded, _PRICE_CUES):
            return "price_question"
        if text.strip().endswith("?"):
            return "general_question"
        return "first_text"

    def safety_kind(self, text: str) -> Optional[str]:
        """Which safety instruction applies, or None.

        Deliberately narrow. A false positive tells a customer to cut power they
        did not need to cut, which costs them a minute; a false negative leaves
        someone switching a smoking appliance back on to see if it still smells.
        Cues are matched on folded text so missing tone marks do not disarm it.
        """
        folded = _fold(text)
        if _has_cue(folded, _GAS_CUES):
            return "gas"
        if _has_cue(folded, _ELECTRICAL_CUES):
            return "electrical"
        if _has_cue(folded, _WATER_CUES):
            return "water_on_electrics"
        return None

    # -- variety ---------------------------------------------------------

    def _draw(
        self, situation: Situation, session_id: Optional[str], chooser: random.Random
    ) -> str:
        """A line this session has not heard yet, if there is one left.

        When the bucket is exhausted the memory for it resets rather than
        falling back to a fixed line: going round the list a second time is much
        less noticeable than saying the same sentence every turn.
        """
        lines = list(self._data.get(situation) or self._data["first_text"])
        if session_id is None:
            return chooser.choice(lines)

        heard = self._seen.setdefault(session_id, {}).setdefault(situation, [])
        fresh = [line for line in lines if line not in heard]
        if not fresh:
            heard.clear()
            fresh = lines

        chosen = chooser.choice(fresh)
        heard.append(chosen)
        return chosen

    def forget(self, session_id: str) -> None:
        self._seen.pop(session_id, None)

    # -- for the client --------------------------------------------------

    def all_lines(self) -> dict:
        """The whole set, for a client that wants to pick locally.

        Mobile fetches this once and caches it. The line has to appear the
        instant the customer hits send, so asking the server for it each turn
        would defeat the only thing it is for.
        """
        return {
            "version": self._data.get("version"),
            "situations": {name: list(self._data[name]) for name in _SITUATIONS},
            "safetyFirst": {
                kind: list(self._data["safety_first"][kind]) for kind in _SAFETY_KINDS
            },
        }


def _has_cue(folded: str, cues: Sequence[str]) -> bool:
    return any(cue in folded for cue in cues)


def _load() -> dict:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    missing = [name for name in _SITUATIONS if not raw.get(name)]
    if missing:
        raise ValueError(f"acknowledgements.json is missing: {', '.join(missing)}")
    safety = raw.get("safety_first") or {}
    missing_safety = [kind for kind in _SAFETY_KINDS if not safety.get(kind)]
    if missing_safety:
        raise ValueError(
            f"acknowledgements.json safety_first is missing: {', '.join(missing_safety)}"
        )
    return raw


_INSTANCE: Optional[Acknowledgements] = None


def get_acknowledgements() -> Acknowledgements:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = Acknowledgements()
    return _INSTANCE
