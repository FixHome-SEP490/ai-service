"""The customer telling the assistant its conclusion was wrong, read by code.

chat2 left "sai rồi" to the language model, and the model reads the whole
conversation: after "máy giặt không vắt được", "không phải bệnh đó, máy kêu
lúc cấp nước" came back as the same belt-or-unbalanced-load verdict, and a
bare "sai rồi" went to the question tier, which answered with that verdict
again one turn later (fixhome.sbs, 12/11). The response also stopped carrying
`customerDisagreed`, so the booking form kept the customer's "sai rồi" in the
description the technician reads.

Here code decides that a message turns the last conclusion down, the
diagnosis is no longer allowed to pick a fault the customer refused, and what
the customer says after the "no" is the account that counts. The vocabulary is
the dialogue lexicon's `previous_denials` (app/data/dialogue_knowledge.json),
the one the previous pipeline used, so both read "sai rồi" the same way.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from app.services.pipeline import dialogue_state
from app.services.pipeline.dialogue_state import _NO_TAIL, _PARTICLES, _SELF_CORRECTION, _without_opening

# Said anywhere in the message, these turn the last answer down: "máy kêu lúc
# cấp nước chứ không phải bệnh đó", "em đoán sai rồi".
ANYWHERE = (
    "doan sai", "chan doan sai", "noi sai roi", "sai benh", "sai loi roi",
    "khong phai benh do", "khong phai loi do", "khong phai benh nay", "khong phai loi nay",
    "chu khong phai benh", "chu khong phai loi",
)
# What may follow an unaccented "khong dung" that still means "không đúng":
# "khong dung roi", "khong dung dau", "khong dung benh". Anything else after it
# is the verb "dùng": "khong dung duoc nua", "chua dung lan nao" (BUG 19).
_RIGHT_TAIL = _PARTICLES | _NO_TAIL | frozenset({"roi", "benh", "loi", "vay", "the", "het", "y", "lam", "gi"})
_SEGMENTS = re.compile(r"[,.;!?\n]+")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower()).replace("đ", "d")
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in text if unicodedata.category(c) != "Mn")))


def _typed(text: str) -> List[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", (text or "").lower()))


def _clause_denies(clause: str) -> bool:
    """Whether one clause opens with a "no" to the last answer."""
    lex = dialogue_state.get_lexicon()
    words = _without_opening(lex.normalize(clause).split())
    text = " ".join(words)
    for pattern in lex.previous_denials:
        if text != pattern and not text.startswith(pattern + " "):
            continue
        after = text[len(pattern):].split()
        if " " not in pattern and after and after[0] not in _RIGHT_TAIL:
            # One word on its own is too loose: "sai giờ rồi" is about the appointment.
            return False
        if pattern.endswith("dung"):
            typed = _typed(clause)
            if "dùng" in typed and "đúng" not in typed:
                # Typed with its accents: "không dùng được nữa" is a symptom.
                return False
            if after and after[0] not in _RIGHT_TAIL and "đúng" not in typed:
                # Typed without them: "khong dung duoc nua roi em".
                return False
        return True
    return False


def denial(text: str) -> Optional[str]:
    """What the customer says after turning the last answer down, or None when nothing is turned down.

    "sai rồi" gives "", "không phải bệnh đó, máy kêu lúc cấp nước" gives
    "máy kêu lúc cấp nước", in the customer's own spelling. "Không dùng được
    nữa", "chưa dùng lần nào" and "à nhầm, ..." (the customer taking back
    their own words) turn nothing down."""
    folded = " " + _fold(text) + " "
    if any(f" {m} " in folded for m in _SELF_CORRECTION):
        return None
    pieces = [p.strip() for p in _SEGMENTS.split(text or "") if p.strip()]
    if not pieces:
        return None
    if not _clause_denies(pieces[0]) and not any(f" {m} " in folded for m in ANYWHERE):
        return None
    return account(text)


def _bare(piece: str) -> bool:
    """A clause that is only the "no": "sai rồi", "không phải bệnh đó đâu", "em đoán sai rồi"."""
    lex = dialogue_state.get_lexicon()
    words = _without_opening(lex.normalize(piece).split())
    joined = " ".join(words)
    if not words:
        return True
    for pattern in (*lex.previous_denials, *ANYWHERE):
        if joined == pattern or joined.startswith(pattern + " "):
            if all(w in _RIGHT_TAIL for w in joined[len(pattern):].split()):
                return True
    return False


def _without_trailing_denial(piece: str) -> str:
    """"máy kêu lúc cấp nước chứ không phải bệnh đó" without the part after "chứ"."""
    words = piece.split()
    folded = [_fold(w) for w in words]
    for pattern in sorted(ANYWHERE, key=len, reverse=True):
        parts = pattern.split()
        for start in range(len(folded) - len(parts), 0, -1):
            if folded[start:start + len(parts)] == parts and all(w in _RIGHT_TAIL for w in folded[start + len(parts):]):
                if start > 0 and folded[start - 1] == "chu":
                    start -= 1
                return " ".join(words[:start]).rstrip(" ,")
    return piece


def account(text: str) -> str:
    """The message without its clauses of bare denial, at either end, as typed.

    For the booking description: "sai rồi, máy vẫn mát nhưng chảy nước" is
    "máy vẫn mát nhưng chảy nước", "máy kêu lúc cấp nước, không phải bệnh đó"
    is "máy kêu lúc cấp nước", and a message that was only the denial is ""."""
    pieces = [p.strip() for p in _SEGMENTS.split(text or "") if p.strip()]
    while pieces and _bare(pieces[0]):
        pieces = pieces[1:]
    while pieces and _bare(pieces[-1]):
        pieces = pieces[:-1]
    if pieces:
        pieces[-1] = _without_trailing_denial(pieces[-1])
    return ", ".join(pieces)[:1000]
