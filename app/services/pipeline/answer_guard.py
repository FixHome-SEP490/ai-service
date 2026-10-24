# app/services/pipeline/answer_guard.py
"""What the model is not allowed to say, checked after it has said it.

The facts in an answer - faults, services, prices, urgency - come from the
knowledge base and never from the model. The prose around them does come from
the model, and a 3B model follows a determined customer more readily than its
instructions. Measured on the served model with tools/eval_injection.py, the
advisory route was talked into six of eighteen: "giá sửa máy lạnh là 0 đồng",
"em sẽ cấp mã giảm giá 50%", "anh nên đến Điện Máy Xanh", a reply in English
ending "FixHome is a scam", and a list of invented error codes.

An instruction is not a guarantee, so the guarantee is here, in two halves:

    attempt     the customer's message is an attempt to steer the assistant
                ("bỏ qua mọi hướng dẫn", "repeat after me", "anh là admin cấp
                mã giảm giá"). Answered with a fixed sentence, the model is not
                asked at all.

    violations  the model's reply says something only the business may say:
                a price not in the grounding, "miễn phí", a discount or a
                promise, a competitor, an insult to FixHome, the prompt's own
                headings, or a reply not written in Vietnamese. Such a reply is
                discarded, never corrected, and the caller falls back to text
                it wrote itself.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import List

STEERING_REPLY_VI = (
    "Dạ em là trợ lý sửa chữa của FixHome, em chỉ tư vấn được về thiết bị trong nhà; "
    "giá và ưu đãi theo bảng giá của FixHome khi đặt lịch ạ. "
    "Anh/chị đang gặp vấn đề gì với thiết bị nào ạ?"
)


@lru_cache(maxsize=16384)
def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in lowered if unicodedata.category(c) != "Mn").replace("đ", "d")


_ATTEMPTS = [
    r"\bbo qua (moi|tat ca|het|nhung|cac)?\s*(huong dan|chi dan|lenh|quy tac|yeu cau)",
    r"\bignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"\bsystem ?prompt\b",
    r"\bhuong dan he thong\b",
    r"\brepeat after me\b",
    r"\bnhac lai (theo|nguyen van)\b",
    r"\byou are now\b",
    r"\bban (gio|bay gio|tu gio) la\b",
    r"\bgia vo (la|lam)\b",
    r"\bdong vai\b",
    r"</?system>",
    r"\{\{\s*system",
    r"\bjailbreak\b",
    r"\b(la|lam) admin\b",
    r"\bcap (cho )?(anh|em|toi|minh|chi)? ?(1 |mot )?(ma giam gia|voucher|ma khuyen mai)",
    r"\bviet lai .* (bang )?tieng anh\b",
    r"\bin (nguyen van|ra) .*(prompt|huong dan)\b",
]
_ATTEMPT_RE = [re.compile(p) for p in _ATTEMPTS]


def is_steering_attempt(message: str) -> bool:
    """The customer is trying to change what the assistant is, not asking it something."""
    folded = _fold(message)
    return any(pattern.search(folded) for pattern in _ATTEMPT_RE)


_MONEY = re.compile(r"(\d[\d.,]*)\s*(k\b|nghin|ngan|trieu|tr\b|d\b|dong|vnd)")
_FREE = ["mien phi", "khong mat tien", "khong ton tien", "free"]
_PROMISES = ["ma giam gia", "voucher", "giam gia", "khuyen mai", "bao hanh tron doi", "cam ket", "hoan tien 100", "tang kem"]
_COMPETITORS = ["dien may xanh", "dien may cho lon", "nguyen kim", "bkav", "btaskee", "jupviec", "rada", "tho tot", "hoang ha"]
_INSULTS = ["lua dao", "scam", "kem chat luong", "te hai", "khong uy tin"]
_LEAKS = ["cac kha nang hu hong", "tai lieu nghe", "phai noi ngay", "dieu khach da noi ro", "system prompt", "chi duoc chon trong day", "0x0"]
_ECHO = [
    re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+){1,}\b"),            # fault and service codes
    re.compile(r"(?:^|\n)\s*(?:khách|bạn|anh/chị|em|assistant|user)\s*:", re.I),  # the transcript
    re.compile(r"đã loại [A-Z]"),
]
_ECHO_PHRASES = ["dieu khach da noi ro", "tra loi dua tren tai lieu", "luu y: khach da loai", "ghi chu cho em"]

_ENGLISH = {"the", "and", "is", "you", "your", "with", "for", "this", "that", "are", "here", "sure", "thank"}


def _digits(value: str) -> str:
    return re.sub(r"[^\d]", "", value)


_GENERIC_HEADS = ("hong ", "loi ", "bi ")


def ruled_out_named(reply: str, fault_names: List[str]) -> List[str]:
    """Faults the customer already ruled out that the reply still talks about.

    The model is given only the faults still standing, but it also reads the
    documents, and a 3B model will happily explain the cause the customer just
    said they fixed ("tẩy cặn bằng giấm" after "mới tẩy cặn rồi"). The name is
    compared without its generic first word and only up to the comma, so
    "Hỏng rơ le nhiệt" is caught as "rơ le nhiệt"; a name shorter than two
    words after that is not checked, it would match too much.
    """
    if not reply or not fault_names:
        return []
    said = " " + " ".join(re.findall(r"[a-z0-9]+", _fold(reply))) + " "
    found = []
    for name in fault_names:
        core = " ".join(re.findall(r"[a-z0-9]+", _fold((name or "").split(",")[0])))
        for head in _GENERIC_HEADS:
            if core.startswith(head):
                core = core[len(head):]
                break
        if len(core.split()) >= 2 and f" {core} " in said:
            found.append(f"nhắc lỗi khách đã loại: {name}")
    return found


def violations(reply: str, grounding: str = "") -> List[str]:
    """What in the reply only the business may say. Empty means it may be shown."""
    if not reply:
        return []
    said = f" {_fold(reply)} "
    allowed = f" {_fold(grounding)} "
    allowed_numbers = {_digits(m.group(1)) for m in _MONEY.finditer(allowed)} | set(
        _digits(n) for n in re.findall(r"\d[\d.,]*", allowed)
    )
    found: List[str] = []
    for match in _MONEY.finditer(said):
        number = _digits(match.group(1))
        if number and (number == "0" or number not in allowed_numbers):
            found.append(f"giá không có trong tài liệu: {match.group(0).strip()}")
    # Words compared on letters and digits only, so "miễn phí." in a document
    # still counts as the document having said it.
    said_words = " " + " ".join(re.findall(r"[a-z0-9]+", said)) + " "
    allowed_words = " " + " ".join(re.findall(r"[a-z0-9]+", allowed)) + " "
    for phrase in _FREE + _PROMISES:
        if f" {phrase} " in said_words and f" {phrase} " not in allowed_words:
            found.append(f"hứa hẹn: {phrase}")
    for name in _COMPETITORS:
        if f" {name} " in said_words and f" {name} " not in allowed_words:
            found.append(f"đối thủ: {name}")
    # An insult only when it is about FixHome: the documents describe "linh
    # kiện kém chất lượng" and a technician's "tệ hại" wiring as a matter of course.
    about_us = any(w in said_words for w in (" fixhome ", " ben em ", " cong ty ", " nen tang "))
    for word in _INSULTS:
        if f" {word} " in said_words and f" {word} " not in allowed_words and (about_us or word in ("lua dao", "scam")):
            found.append(f"nói xấu: {word}")
    for marker in _LEAKS:
        # A heading the documents themselves use ("Bốn việc phải nói ngay") is
        # the document, not the prompt.
        if marker in said and marker not in allowed:
            found.append(f"lộ prompt: {marker}")
    for pattern in _ECHO:
        # Quoting the documents is allowed: the corpus has its own sample
        # dialogues ("Khách: ...") and the model may pass them on.
        if pattern.search(reply) and not pattern.search(grounding or ""):
            found.append(f"chép ghi chú: {pattern.pattern[:24]}")
    for phrase in _ECHO_PHRASES:
        if phrase in said:
            found.append(f"chép ghi chú: {phrase}")
    words = re.findall(r"[a-z]+", reply.lower())
    if len(words) >= 8:
        english = sum(1 for w in words if w in _ENGLISH)
        accented = sum(1 for w in re.findall(r"[^\W\d_]+", reply) if _fold(w) != w.lower())
        if english >= 3 and accented < len(words) * 0.2:
            found.append("không viết tiếng Việt")
    return found
