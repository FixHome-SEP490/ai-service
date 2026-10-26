"""What to get ready before the technician comes, said for the appliances in question.

PO 26/10/2026: "trước khi thợ tới em cần làm gì" was answered from the written
corpus, which has nothing on it, and came back either with a technician's own
duty or with "chưa có thông tin". The answer has to fit the appliance: a gas
stove is never told to shut the water off. The steps are written per
appliance in data/visit_prep.json from the knowledge base's own advice and
said word for word, not handed to the model; the general list is the last
resort, for when no appliance is known.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence, Tuple

_PATH = Path(__file__).resolve().parents[2] / "data" / "visit_prep.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_PATH.read_text(encoding="utf-8"))


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn").replace("đ", "d")
    return " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "


_GET_READY = ("chuan bi", "don dep gi", "don san")
"""Asking what to get ready, whatever else is said."""

_BEFORE = ("truoc khi tho", "tho toi thi", "tho den thi", "tho sang thi", "tho qua thi", "truoc khi sua")
_WHAT_TO_DO = ("lam gi", "can gi", "nen gi", "luu y", "de y", "can lam", "nen lam", "phai lam", "lam sao")


def asks_how_to_prepare(text: str) -> bool:
    """Whether the message asks what to do before the technician comes.

    "Em cần chuẩn bị gì", "trước khi thợ tới em cần làm gì". Not "trước khi thợ
    tới có dùng tạm được không": that asks about the appliance, and is answered
    by its diagnosis."""
    folded = _fold(text)
    if any(f" {w} " in folded for w in _GET_READY):
        return True
    return any(f" {b} " in folded for b in _BEFORE) and any(f" {w} " in folded for w in _WHAT_TO_DO)


def steps_for(device_type: Optional[str]) -> Tuple[str, ...]:
    """The steps for one appliance, or the general ones when it has none written."""
    data = _data()
    return tuple(data["devices"].get(device_type or "", data["general"]))


def _listed(steps: Sequence[str]) -> str:
    """One step a line: read by people who are not in a hurry to parse a long sentence."""
    return "\n".join(f"• {s[:1].upper()}{s[1:]}." for s in steps)


def reply_vi(appliances: Sequence[Tuple[str, str]]) -> str:
    """The answer for the appliances of the conversation, as (device type, name).

    One appliance: its steps. Several: a block each. None known: the general
    steps, and an invitation to say which appliance it is."""
    data = _data()
    closing = data["closing"]
    known = [(d, n) for d, n in appliances if d]
    if not known:
        return "\n\n".join(
            [
                "Dạ, trước khi thợ tới anh/chị chuẩn bị giúp em mấy việc sau:\n" + _listed(data["general"]),
                "Anh/chị cho em biết thiết bị nào đang hỏng thì em dặn kỹ hơn cho đúng loại máy. " + closing,
            ]
        )
    if len(known) == 1:
        device, name = known[0]
        return "\n\n".join(
            [
                f"Dạ, để thợ sửa {name.lower()} được nhanh, trước khi thợ tới anh/chị chuẩn bị giúp em:\n"
                + _listed(steps_for(device)),
                closing,
            ]
        )
    parts = ["Dạ, trước khi thợ tới anh/chị chuẩn bị giúp em:"]
    for device, name in known:
        parts.append(f"Với {name.lower()}:\n" + _listed(steps_for(device)))
    parts.append(closing)
    return "\n\n".join(parts)
