# app/services/pipeline/local_pipeline.py
"""Orchestrates detector, retrieval, VLM and knowledge-base lookup."""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import re
import time
import unicodedata
from collections import OrderedDict
from functools import lru_cache
from typing import Any, List, Optional, Sequence

import logging

from app.core.config import settings
from app.schemas.chat import AnswerStatus, ChatRequest, ChatResponse, Citation
from app.schemas.diagnosis import (
    BoundingBox,
    Clarification,
    DetectedDevice,
    DeviceSuggestion,
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    Engine,
    PhotoReading,
    ModelInfo,
    EvidenceSource,
    PriceEstimate,
    RecommendedService,
    SuspectedFault,
    TraceStage,
    UrgencyLevel,
    VisibleCondition,
)
from app.services.pipeline import answer_guard
from app.services.pipeline import clarifier
from app.services.pipeline import context
from app.services.pipeline import device_hint
from app.services.pipeline import error_codes
from app.services.pipeline import service_catalog
from app.services.pipeline import visit_prep
from app.services.pipeline import dialogue_state
from app.services.pipeline.conversation import Conversation, day_vi, get_conversation_store
from app.services.pipeline.detector import Detection, Detector
from app.services.pipeline.images import ImagePayload, load_base64_image
from app.services.pipeline.knowledge_base import KnowledgeBase
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import VisionLanguageModel, VlmVerdict

_IDENTIFY_PATTERNS = (
    "la cai gi", "la gi", "may gi", "thiet bi gi", "cai gi vay", "gi vay",
    "gi day", "gi the", "nhan ra", "doan xem", "biet day la",
)
"""Someone asking what the appliance is, not reporting that it broke.

A photograph with "đây là cái gì vậy em" is a question, and it was answered
with the device name followed by three questions about leaks. Nobody mentioned
a leak. Answering something nobody asked, in the same breath as answering what
they did ask, is how an assistant stops feeling like it read the message."""

_SYMPTOM_WORDS = (
    "hong", "hu", "keu", "ro ri", "ro nuoc", "chay", "khet", "khong ", "chap",
    "nhay aptomat", "yeu", "cham", "nong qua", "lanh qua", "rung", "nut", "vo",
    "tac", "nghet", "bi ",
)
"""Words that turn a photograph into a fault report.

Checked alongside the identification patterns, because "đây là máy gì mà kêu to
thế" is both a question and a symptom, and the symptom is the part worth acting
on."""

_TRADE_WORDS = (
    "hong", "hu ", "sua", "thay", "keu", "ro ri", "ro nuoc", "chap", "chay",
    "khet", "nong", "lanh", "nuoc", "dien", "tho", "bao tri", "ve sinh",
    # No bare "may". Stripped of tone marks it is both "máy", the machine, and
    # "mấy", the word every counting question ends with: "2 cộng 2 bằng mấy"
    # was answered because of it. Appliances are recognised by name through
    # devices_named_in, which is the better signal anyway.
    "lap dat", "thiet bi", "bong", "den", "o cam", "cong tac", "voi", "bon",
    "ong ", "quat", "lo ", "bep", "tu ", "binh ", "aptomat", "gas",
    # Asking what to book is the point of the whole conversation, and it was
    # being refused as off-topic: "giờ tôi nên thuê dịch vụ nào" came back with
    # "em chỉ hỗ trợ các vấn đề về điện, nước và đồ gia dụng".
    "dich vu", "thue", "dat lich", "book", "goi tho", "bao gia", "sua",
    # The business questions. Without these, "bảo hành bao lâu" reads as a
    # sentence about nothing and the customer is told it is out of scope —
    # after retrieval has already found the document written to answer it.
    "bao hanh", "chinh sach", "hoan tien", "huy lich", "fixhome", "hoa don",
    # Three words that used to be matched by accident. "Cống nhà tắm bốc mùi
    # hôi" passed because "cống" contains "ong ", and "cắm sạc vào ổ mà lỏng
    # lẻo" because "lỏng" does too; whole-word matching took both away along
    # with the false positives. Chosen by running every case in chat_cases.py
    # against the gate: "gia" was the obvious fourth and it lets in questions
    # about the price of gold and of bitcoin.
    "mui", "cam", "mac",
    # Asking how the bill is put together is the commonest business question
    # there is, and it was refused: "bên mình tính giá sao" carries no appliance
    # and no symptom, and bare "gia" cannot be a trade word because it lets in
    # the price of gold. As phrases they are unambiguous.
    "tinh gia", "tinh tien", "gia ca", "bang gia", "phi dich vu",
    # Two words that are a fault report and nothing else. "Bị lỗi" alone was
    # refused as off-topic, which is the assistant telling somebody reporting a
    # fault that faults are not its subject.
    "bi loi", "bi hong", "gap van de", "co van de", "truc trac",
)
"""Words that place a question inside the trade.

Coarse on purpose. The model's own NGOAI_PHAM_VI answer cannot be relied on —
asked "bitcoin giá bao nhiêu" it explained how to track cryptocurrency prices —
and a repair company answering questions about anything is worse than one
answering fewer questions."""

_NOT_HOUSEHOLD = (
    "may bay", "xe may", "o to", "xe hoi", "xe oto", "laptop", "may tinh",
    "dien thoai", "iphone", "android", "may anh", "dong ho", "xe dap",
)
_STILL_HOUSEHOLD = ("dong ho nuoc", "dong ho dien")
"""Reads as one of the refusals above and is squarely in the trade.

A water meter is plumbing and an electricity meter is electrics, and both are
"đồng hồ" — the same two words as the wristwatch FixHome does not repair. "Đồng
hồ nước bị rò" is a leak.
"""

"""Things with electricity or an engine that FixHome does not repair.

The trade words are coarse by design, and coarse let these through: "xe máy
không nổ" matched on "may", "laptop không lên nguồn" on "nguon", "điều hoà xe
hơi không mát" on the air conditioner it is not. Named outright, they are
refused before anything else looks at them."""

_GREETING_PHRASES = frozenset({
    "alo", "a lo", "co ai khong", "co ai o day khong", "co ai do khong",
    "co ai khong a", "cho hoi", "xin chao", "chao shop", "chao ban",
})
"""Whole messages that are only a hello, matched exactly."""

_GREETING_TOKENS = frozenset({
    "chao", "hello", "hi", "hey", "alo", "cam", "on", "thanks", "thank", "you",
    "ok", "oke", "okie", "da", "vang", "u", "um", "uh", "co", "khong", "yes",
    "em", "anh", "chi", "ban", "oi", "a", "ah", "nhe", "nha", "voi", "the",
})
"""Words a message can be made *entirely* of and still say nothing.

Never matched as a prefix. `startswith` on folded text made "có mùi khét" a
greeting, because "có" folds to "co" and "co" was in this list — so the most
dangerous message a customer can send was answered with "Dạ em chào anh/chị ạ".
So were "không lên nguồn", "có nước rò", "có tiếng nổ" and "dạ máy lạnh hỏng".

The rule that prevents this is the same one the retriever learned: whole words
only, and a word this short can never decide anything on its own. It decides
here only when every other word in the message is also one of these.
"""


@lru_cache(maxsize=16384)
def _fold_vi(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return folded.replace("đ", "d")


def _is_greeting(text: str) -> bool:
    """A hello or a bare acknowledgement, with nothing else in it."""
    folded = _fold_vi(text)
    words = re.findall(r"[a-z0-9]+", folded)
    if not words or len(words) > 5:
        return False
    if " ".join(words) in _GREETING_PHRASES:
        return True
    return all(word in _GREETING_TOKENS for word in words)


def _is_not_household(text: str) -> bool:
    """Whether the customer is reporting something FixHome does not repair.

    Whole words, never substrings. "Ô tô" folds to "o to", which sits inside
    "thợ tới" — so every message containing the commonest phrase in the trade,
    "bao lâu thợ tới", "khi nào thợ tới nhà em", "cần thợ tới sửa tủ lạnh", was
    answered with a refusal explaining that FixHome does not repair cars.

    This refusal fires before every other branch, which is why it had to be the
    coarsest check in the file and why a false positive here is the most
    expensive one: the customer is told their question is out of scope and the
    turn ends.
    """
    folded = _fold_vi(text)
    padded = " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "
    if any(phrase in padded for phrase in _STILL_HOUSEHOLD):
        return False
    for word in _NOT_HOUSEHOLD:
        at = padded.find(f" {word} ")
        if at < 0:
            continue
        # "Kêu như máy bay" is how a customer describes a noisy washing machine,
        # and it was refused as a question about aircraft. A comparison names the
        # thing it compares to; it does not report it.
        if padded[max(0, at - 5):at + 1].endswith(" nhu "):
            continue
        return True
    return False


def _is_identification(text: str) -> bool:
    """Asking what it is, and not also saying it is broken."""
    folded = _fold_vi(text)
    if not any(p in folded for p in _IDENTIFY_PATTERNS):
        return False
    return not any(w in folded for w in _SYMPTOM_WORDS)


_BOOKING_VERBS = frozenset({
    "dat", "book", "thue", "hen", "goi", "keu", "can", "xin", "chot", "muon",
})
"""Words that turn a sentence from describing into buying, as whole words.

Matched against a word list rather than as substrings, so "đặt" in "đặt nồi lên
bếp" is seen but produces nothing on its own — a verb only counts alongside one
of the objects below.
"""

_BOOKING_WHO = (
    "tho", "lich", "dich vu", "don", "ban tho",
    "nguoi toi", "nguoi sua", "nguoi den",
)
"""A person or a booking. Unambiguous: nobody asks for a thợ to describe one.

Split from the service words below because one verb is too weak to count
against those but strong enough against these. "Cho em một bạn thợ tới xem máy
giặt" is a request for a technician; "cho em hỏi cái này có sửa được không" is
not, and both are "cho" plus something.
"""

_BOOKING_WHAT = (
    "ve sinh", "sua", "thong tac", "lap dat", "bao duong", "bao tri",
)
"""The work itself. Needs a verb with more intent behind it than "cho"."""

_WEAK_BOOKING_VERBS = frozenset({"cho"})
"""Verbs that only count alongside a person or a booking, never a service word."""

_BOOKING_PHRASES = (
    "dang ky dich vu", "dat cho toi", "dat cho minh", "dat giup",
    "book giup", "lam sao de dat", "dat nhu nao", "dat the nao",
    "co nhan", "co sua", "co lam", "co ve sinh", "co thong tac",
    "nhan sua", "nhan ve sinh", "nhan lam",
    # "Yêu cầu" cannot be reached through the verb list: "yêu" folds onto "yếu",
    # which is in half the symptom lists in the corpus — a weak flame, weak
    # water pressure, a fan running weakly — so it is matched only beside the
    # person being requested.
    "yeu cau tho", "yeu cau nguoi",
    # A verb with the object left implied, which is how a customer who has
    # already been shown a service says yes.
    "dat luon", "chot luon",
    "cho toi dat", "cho em dat", "cho anh dat", "cho chi dat", "cho minh dat",
)
"""Forms that carry the intent without a verb-and-object pair in reach.

"Bên mình có nhận vệ sinh máy lạnh không" is a buying question with no buying
verb in it: the customer is asking whether the service exists, and the useful
answer is the service and its price, not a diagnosis of a machine they have not
described.
"""

_ALREADY_BOOKED = (
    "da dat", "dat roi", "dat hom qua", "dat hom truoc", "lich dat",
    "bi huy", "chua toi", "chua den", "sai vi tri", "truoc khi",
    "tho toi chua", "da den chua", "bao lau thi tho",
)
"""Sentences about a booking that already exists, which must not be read as a
new one.

"Tôi đã đặt lịch rồi mà thợ chưa tới" was read as booking intent and answered
with a service and a booking button, which is the one reply that cannot help
someone whose complaint is that the booking they made has not produced anybody.
Checked before the positive patterns, because the positive words are all present
in these sentences too.
"""


def _wants_to_book(text: str) -> bool:
    """Whether the customer has stopped describing and started buying.

    Asked "bây giờ anh muốn đặt lịch vệ sinh máy lạnh", the service used to
    answer with a diagnosis: two possible faults, a price range and a list of
    things to try first. Nobody asked what was wrong. Diagnosing someone who is
    trying to book puts a wall of text between them and the thing they came to
    do, so this path must be wide — a customer who says plainly that they want a
    technician gets the service and the button, and no diagnosis.
    """
    folded = _fold_vi(text)
    padded = " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "

    if any(phrase in padded for phrase in _ALREADY_BOOKED):
        return False

    if any(phrase in padded for phrase in _BOOKING_PHRASES):
        return True

    words = set(padded.split())

    # "Book" is an English loanword in Vietnamese and is only ever used for
    # this, so it needs no object: "muốn book", "book giúp em". Whole-word
    # matching keeps it out of "facebook".
    if "book" in words:
        return True

    # Padded on both sides, never as a bare substring. Matching "tho" inside a
    # word made eight real symptom phrases read as requests to book: "thoi" in
    # "lò chạy cho vui thôi", "thoat" in "chỗ thoát nước bị hoen", "thong" in
    # "khoá thông minh kêu nhưng không mở". The same mistake has now been found
    # three times in this file, in three different keyword lists.
    if words & _BOOKING_VERBS:
        return any(f" {obj} " in padded for obj in _BOOKING_WHO + _BOOKING_WHAT)
    if words & _WEAK_BOOKING_VERBS:
        return any(f" {obj} " in padded for obj in _BOOKING_WHO)

    # Redirecting an order is ordering. "Đổi sang thợ sửa tủ lạnh giúp em"
    # carries none of the verbs above, so it read as a description and came
    # back as a diagnosis of the appliance the customer had just moved away
    # from. Someone who is changing what they are about to book has already
    # stopped describing.
    if any(f" {phrase} " in padded for phrase in _ASKS_FOR):
        return any(f" {obj} " in padded for obj in _BOOKING_WHO + _BOOKING_WHAT)

    return False


_BUSINESS_WORDS = (
    "bao hanh", "chinh sach", "hoan tien", "huy", "dat lich", "quy trinh",
    "fixhome", "hoa don", "cam ket", "khieu nai", "danh gia", "thanh toan",
    "dat tho", "goi tho", "dich vu", "ung dung", "app",
)
"""What makes a question about the business rather than about a machine."""


_FOLLOW_UP_MAX_WORDS = 6
"""Above this a question carries enough of itself to retrieve on.

Six words is where "gia bao nhieu" and "con cai kia thi sao" sit and where a
real standalone question starts. Getting it wrong in the safe direction means
retrieving on one message too many, which the retriever already handles: it is
given the whole thread on the diagnosis side and always has been."""


_DIALOGUE_TURNS = 6
"""How much of the thread the model is shown.

Enough to follow a reference back a couple of exchanges, short enough that a
3B model with a passage budget still spends most of its attention on the
documents."""


def _recent_dialogue(chat: Conversation, kb: Optional[KnowledgeBase] = None) -> str:
    """The last few turns, labelled, oldest first.

    customer_text() joins only what the customer said, which is right for
    retrieval and wrong for a prompt: the model needs to see what it already
    answered, or it answers it again.
    """
    lines = [
        ("Khách" if t.role == "customer" else "Bạn") + f": {t.text_vi}"
        for t in chat.turns[-_DIALOGUE_TURNS:]
    ]
    # What the whole thread established, not only the turns that fit: a cause
    # ruled out eight messages ago is still ruled out.
    if kb is not None:
        note = chat.plain_facts_vi(kb)
        if note:
            lines += ["", note]
    return "\n".join(lines)


def _standalone_question(question: str, chat: Conversation, kb: KnowledgeBase) -> str:
    """The question with enough of the thread in front of it to mean something.

    "Chi phí thay aptomat máy giặt", then "giá bao nhiêu". The second message
    retrieved on three words that name no appliance and no part, matched a
    policy line about fixed-price services, and the customer was told something
    true about a different subject. It is not a new question; it is the end of
    the previous one.
    """
    # The cleaned form of each earlier turn where there is one: "mới vệ sinh
    # rồi" said nothing that is happening, and prefixed to the next question it
    # retrieved cleaning advice for a customer who had just ruled cleaning out.
    earlier = [
        t.text_vi if t.retrieval_vi is None else t.retrieval_vi
        for t in chat.turns
        if t.role == "customer"
    ][:-1]
    earlier = [text for text in earlier if text]
    if not earlier:
        return question
    if len(_fold_vi(question).split()) > _FOLLOW_UP_MAX_WORDS:
        return question
    if _device_named_in(question, kb) is not None:
        return question
    return f"{earlier[-1]} {question}"


def _asks_about_the_business(question: str) -> bool:
    """Whether the five business documents are relevant at all.

    They were being consulted for every question, and one of them outranked
    the fault documents on "máy lạnh không mát" because it happens to discuss
    an air conditioner that is not cooling — as an example of what the
    manufacturer's warranty covers. The customer asked why their machine was
    not cooling and was told to go and check their warranty first, which is a
    repair company talking its own customer out of the job.
    """
    return _mentions(question, _BUSINESS_WORDS)


_MONEY_WORDS = ("gia", "tien", "bao nhieu", "chi phi", "cost", "het bao", "mac", "re")
"""What makes a question one about cost.

Matched as whole words. Substring matching was called safe here on the grounds
that price rows are only ever added to what is already retrieved and never
decide whether to answer — and that was true and still not safe, because the
price row is added *first*, and the first passage is the one the model answers
from.

Two words collide once the diacritics come off, and both of them collide with
something customers type constantly:

    gia  is also "giặt", which folds to "giat" — so every single question about
         a washing machine was read as a question about price. "Máy giặt nhà em
         không vắt được" was answered with the cost of a door glass.

    re   is also "remote" — so every question about a handset was too.

Four appliances of the twenty-two are named with one of those two strings
inside. This is the fourth time this class of bug has been found in this
codebase; the rule written down after the third was whole-word matching and
never an alias under four characters, and this list predates it."""


def _mentions(question: str, words: Sequence[str]) -> bool:
    """Whether the question uses any of these words, as whole words.

    One function for both keyword lists, because the bug it fixes was written
    twice: each list had its own copy of fold-then-substring, and a fix applied
    to one would have left the other to be found again later.

    Padded with spaces on both sides so a phrase of two words matches on its
    own boundaries too — " bao nhieu " is found inside " het bao nhieu tien "
    and not inside a longer word at either end.
    """
    folded = _fold_vi(question)
    padded = " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "
    return any(f" {word} " in padded for word in words)


def _asks_about_money(question: str) -> bool:
    """Whether the customer is asking what something costs."""
    return _mentions(question, _MONEY_WORDS)


logger = logging.getLogger(__name__)

_VAGUE_WORDS = {
    "hu", "hong", "loi", "bi", "sao", "roi", "van", "de", "truc", "trac", "nua", "lai", "nha", "em",
    "anh", "chi", "minh", "toi", "cai", "chiec", "may", "giup", "voi", "di", "a", "nhe", "oi", "gi",
}
"""Words that say something is wrong without saying what: "máy lạnh hư rồi"."""

_VAGUE_WORDS |= {
    "dung", "thay", "ta", "duoc", "lam", "hoi", "dao", "nay", "hom", "khac", "yen",
    "ung", "y", "nhu", "moi", "mua", "biet", "the", "nao", "tot", "ky", "ki", "la",
    "co", "khong", "cho", "no", "cu", "thi", "ma", "day", "dau", "gan", "truoc", "gio",
}
"""And the words of a complaint that names nothing: "dùng thấy không ổn lắm",
"có vấn đề gì đó", "dạo này hơi lạ". Each of them occurs somewhere in the
symptom lists. Typed without accents, words that also fold from a symptom
("on" is "ồn", "ro" is "rò", "do" is "đỏ", "tam" is "tắm") are left out of
this list: there the doubt goes to the customer."""

_VAGUE_ACCENTED = {
    "hư", "hỏng", "lỗi", "bị", "sao", "rồi", "vấn", "đề", "trục", "trặc", "nữa", "lại", "nhà", "em",
    "anh", "chị", "mình", "tôi", "cái", "chiếc", "máy", "giúp", "với", "đi", "à", "nhé", "ơi", "gì",
    "dùng", "thấy", "ổn", "đó", "tả", "được", "lắm", "lạ", "kỳ", "kì", "hơi", "dạo", "này", "mấy",
    "hôm", "nay", "khác", "yên", "tâm", "ưng", "ý", "như", "mới", "mua", "biết", "rõ", "thế", "nào",
    "tốt", "có", "không", "nó", "cứ", "thì", "là", "mà", "đấy", "đâu", "gần", "đây", "trước", "giờ",
}

_CONVERSATION = (
    "xem nhờ cháu thợ hỏi qua hình chào quá ấy tui ni chuyện kiểm tra nói chút ba năm tháng vẻ bà "
    "làm xin tình trạng ạ á cô đã coi hổng răng đang e sửa mong chán thật sự đặt khôn gặp tư vấn chắc "
    "con nhỏ ê bực sợ định ay ăn kiểu bác hộ nỏ rùi bữa hoài chồng vợ mẹ bố hông huhu hic ừm ờ luôn "
    "chung muốn trời thử rút xài hệ thống nguồn điện nước chạy ông anh chị em ơi dạ vâng nghen nha nè "
    "hen hả hử nhá nhé đó đây kia rứa chi mô tê tề dzậy zậy vậy thế đấy "
    "giùm dùm rành hồi tuần từ chừ hiểm nguy nấu tắm khóa vân tay ổ cắm bếp lò quạt tủ vòi bồn ống "
    "đèn bóng bình ấm sấy đồ bát chén giặt lọc sen cầu lavabo tivi tv"
).split()
"""Words of the conversation around a report rather than the report: who is
asking, who told them, asking for a technician, how long they have had it.
Counted from the vague messages of the dev half of the understanding bank,
which were being answered as though they described a fault."""

_VAGUE_ACCENTED |= set(_CONVERSATION) - {"ấm", "điện", "nước", "chỗ", "kia"}
# Without accents only the words that fold from nothing else: "chay" is also
# "cháy", "den" is "đen", "am" is "ấm" (warm), "nuoc" and "dien" are what the
# complaint is about. "ổ cắm bị chay den" lost its fire to this list once.
_VAGUE_WORDS |= set(
    "xem chau tho qua chao tui ni chuyen kiem tra chut xin tinh trang coi khon gap chac "
    "hoai chong huhu hic um luon muon troi xai gium dum anh chi em oi vang nghen nha ne hen "
    "nhe dzay zay vay".split()
)



def _without_framing_tokens(tokens, lexicon) -> list:
    """The conversation's words minus what surrounds the report.

    The phrase lists the search drops (`framing`, `meta_phrases` and the hedges
    in `dialogue_knowledge.json`), matched on the reader's folded words."""
    phrases = sorted(
        set(lexicon.framing) | set(lexicon.meta_phrases) | set(lexicon.hedges), key=len, reverse=True
    )
    folded = [t.f for t in tokens]
    kept = []
    i = 0
    while i < len(tokens):
        for phrase in phrases:
            if phrase and tuple(folded[i : i + len(phrase)]) == phrase:
                i += len(phrase)
                break
        else:
            kept.append(tokens[i])
            i += 1
    return kept


_VAGUE_NEGATED = frozenset(
    "duoc on biet ro sao co phai the lam nhu tot yen binh thuong ung y on dinh tam hieu".split()
)
"""Words whose negation is not a complaint about anything in particular."""


_SUPPLY_WORDS = frozenset({"dien", "nuoc", "nong", "lanh", "gas", "ga", "khi", "lua", "gio"})
"""What the appliance delivers is named in its name ("Ổ cắm điện", "Máy lọc
nước") and is also what a complaint is about ("không có điện")."""

_CLEAR_LEAD = 0.3
"""How far the first fault must lead the second for a two-word report to be
answered without a question back."""

_URGENCY_RANK = {UrgencyLevel.LOW: 0, UrgencyLevel.MEDIUM: 1, UrgencyLevel.HIGH: 2}


class _Trace:
    """Collects what each stage did, or nothing at all when not asked for.

    The no-op form matters: a trace that is always built costs every customer
    request the string formatting and the copying, to produce something only an
    operator ever reads.
    """

    def __init__(self, wanted: bool) -> None:
        self._wanted = wanted
        self.stages: List[TraceStage] = []
        self._started = time.perf_counter()

    def mark(self) -> None:
        self._started = time.perf_counter()

    def add(self, name: str, ok: bool, summary_vi: str, **detail: Any) -> None:
        if not self._wanted:
            return
        elapsed = int((time.perf_counter() - self._started) * 1000)
        self.stages.append(
            TraceStage(
                name=name, ms=elapsed, ok=ok, summary_vi=summary_vi, detail=detail
            )
        )
        self.mark()


_DEVICE_HEADS = frozenset(
    """may tu quat lo bep am binh tivi ti tv bon chau voi sen o bong den ong duong
    khoa toilet lavabo microwave dieu cau cay be bet""".split()
)
"""First words of a name that names an appliance rather than a part of one.

"Tủ lạnh", "máy sấy", "ổ cắm", "vòi nước" name a machine. Several aliases do
not: "nóng lạnh" is a setting on a mixer tap, "phích cắm" is the plug on every
appliance, "rửa bát" is what a sink is used for. Those are fine for finding the
appliance when nothing else is known, and wrong for deciding that the customer
has moved on from the one they were talking about: a tap that "không chỉnh được
nóng lạnh" was turned into a water heater, a fan whose "phích cắm nóng" into a
socket, and every word said after that was searched against the wrong machine.
"""


def _named_spans(text: str, kb: KnowledgeBase) -> List[tuple]:
    """See _named_spans_uncached; remembered per text, as devices_named_in is."""
    return list(_named_spans_cached(text, kb))


@lru_cache(maxsize=4096)
def _named_spans_cached(text: str, kb: KnowledgeBase) -> tuple:
    return tuple(_named_spans_uncached(text, kb))


def _named_spans_uncached(text: str, kb: KnowledgeBase) -> List[tuple]:
    """(device, alias, start, end) for each appliance named, on word boundaries.

    `devices_named_in` matches inside words, so "nám" holds "ấm" and "quạt trần"
    holds "quạt": a sentence about a ceiling fan named two appliances and
    resolved to none. Here an alias must stand as whole words, and one that sits
    inside a longer match is the same mention, not a second appliance. Its
    disqualifiers ("máy sấy tóc" is not a clothes dryer) are kept by only
    considering the devices it accepts.
    """
    allowed = {h.device_type for h in device_hint.devices_named_in(text, kb)}
    lowered = unicodedata.normalize("NFC", text.lower())
    words_at = list(re.finditer(r"[^\W_]+", lowered))
    typed = [m.group(0) for m in words_at]
    folded = [_fold_vi(w) for w in typed]
    # Where punctuation stands between two words: a name never spans it.
    # "Đọng nước - máy lạnh chạy..." read as "nước máy", a water pipe.
    broken = {
        k for k in range(1, len(words_at))
        if re.search(r"[,.;!?:\n\-–—()]", lowered[words_at[k - 1].end() : words_at[k].start()])
    }
    spans = []
    for device in sorted(allowed):
        for alias in kb.aliases_vi(device):
            wanted = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", alias.lower()))
            if not wanted:
                continue
            n = len(wanted)
            for i in range(len(typed) - n + 1):
                if folded[i : i + n] != [_fold_vi(w) for w in wanted]:
                    continue
                # Accents decide where the customer typed them: "âm trần" is a
                # recessed light, not "ấm", whatever the letters fold to.
                if any(
                    typed[i + j] != _fold_vi(typed[i + j])
                    and wanted[j] != _fold_vi(wanted[j])
                    and typed[i + j] != wanted[j]
                    for j in range(n)
                ):
                    continue
                if any(k in broken for k in range(i + 1, i + n)):
                    continue
                spans.append((device, alias, i, i + n))
    # Most specific first: length without the classifier, so "quạt trần" beats
    # "cái quạt" over the same words of "cái quạt trần".
    # Then the one that starts first, then by name: two names of one length
    # overlapping ("vòi nước máy" holds "vòi nước" and "nước máy") used to be
    # settled by the order a set happened to iterate in, which changes from one
    # process to the next, and the same message was cut differently each run.
    def words_of(alias: str) -> List[str]:
        return [w for w in re.findall(r"[^\W_]+", _fold_vi(alias)) if w not in ("cai", "chiec")]

    spans.sort(
        key=lambda span: (
            -len(words_of(span[1])),
            # Of two names of one length overlapping, the one that names a
            # machine: "nước máy lạnh" is the air conditioner, not tap water.
            0 if (words_of(span[1]) or [""])[0] in _DEVICE_HEADS else 1,
            span[2],
            span[0],
            span[1],
        )
    )
    kept: List[tuple] = []
    for span in spans:
        # Overlapping is the same mention: "cái quạt trần" holds both "cái quạt"
        # and "quạt trần", and it is one ceiling fan.
        if any(span[2] < k[3] and k[2] < span[3] for k in kept):
            continue
        kept.append(span)
    return kept


_AS_AN_OBJECT = frozenset(
    "vào của cho như giống khác chi bằng từ trong trên dưới cạnh gần nối cắm bên sau trước "
    "lên xuống ở tại qua theo kiểu tựa hệt đến tới với đo vặn ra chảy gắn xả sạc dùng xài "
    "thử kiểm lắp thay sang đổi gầm phông".split()
)
"""Words after which an appliance is a thing in someone else's sentence.

"Cắm cái quạt vào ổ", "mùi giống như vòi bồn rửa", "nối từ tủ lạnh": the fan,
the sink and the fridge are not appliances the customer is reporting, and
cutting the message there handed half a socket's description to a fan."""


_INDICATOR_AFTER = frozenset("cho bao xanh do nguon led hien tin nhan nhay".split())
"""After "đèn": the light of another appliance, not a light bulb: "đèn chờ không
sáng", "đèn báo", "cái đèn xanh nhỏ trên đó"."""


def _what_it_is(mention: tuple, folded: List[str]) -> Optional[tuple]:
    """A mention read with the words around it, or None when it names no appliance.

    "Cái quạt trên trần nhà" is a ceiling fan, "bình đun nước tắm" a water
    heater, and "đèn chờ" the standby light of the appliance being described.
    """
    device, start, end = mention
    after = folded[end : end + 3]
    if device == "electric_fan" and after[:2] in (["tren", "tran"], ["tran", "nha"]):
        return ("ceiling_fan", start, end + 2)
    if device == "kettle" and "tam" in after[:2]:
        return ("water_heater", start, end)
    if device == "light_bulb" and folded[end - 1 : end] == ["den"] and after[:1] and after[0] in _INDICATOR_AFTER:
        return None
    return mention


def _appliance_mentions(text: str, kb: KnowledgeBase) -> List[tuple]:
    """See _appliance_mentions_uncached; remembered per text.

    A turn read the same message for its appliances four times: to cut it,
    to check for a correction, to route it and to pick the photograph's lead.
    """
    return list(_appliance_mentions_cached(text, kb))


@lru_cache(maxsize=4096)
def _appliance_mentions_cached(text: str, kb: KnowledgeBase) -> tuple:
    return tuple(_appliance_mentions_uncached(text, kb))


def _appliance_mentions_uncached(text: str, kb: KnowledgeBase) -> List[tuple]:
    """(device, first token, end token) for every appliance the customer reports.

    By the names that name a machine (not "nóng lạnh", a tap setting), and by
    a brand with the word for the kind of thing before it ("lò Sharp", "con
    Senko", "bếp Taka") when the brand and that word leave one appliance. A
    name used as the object of someone else's sentence is left out. Token
    positions are those of `re.findall(r"[^\\W_]+", NFC(text).lower())`.
    """
    typed = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))
    folded = [_fold_vi(w) for w in typed]
    found = []
    for device, alias, start, end in _named_spans(text, kb):
        head = ([w for w in re.findall(r"[a-z0-9]+", _fold_vi(alias)) if w not in ("cai", "chiec")] or [""])[0]
        if head in _DEVICE_HEADS:
            found.append((device, start, end))
    known = set(kb.device_types)
    # What customers call it beyond the aliases ("máy thổi gió", "bệt", "con MRB").
    for device, names in device_hint.known_names().items():
        if device not in known:
            continue
        for words in names:
            n = len(words)
            for i in range(len(folded) - n + 1):
                if folded[i : i + n] == list(words):
                    found.append((device, i, i + n))
    # An alias of two words or more typed with one letter wrong ("lò vi xóng",
    # "máy xấy"), first letter right, in a word of four letters or more.
    # Compared with the accents where the customer typed them: without, "mấy
    # lần" is one letter from "máy lạnh" and "vơi được" from "vòi nước".
    for device in kb.device_types:
        for alias in kb.aliases_vi(device):
            accented = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", alias.lower()))
            words = [_fold_vi(w) for w in accented]
            if len(words) < 2 or sum(len(w) for w in words) < 6:
                continue
            n = len(words)
            for i in range(len(folded) - n + 1):
                window = folded[i : i + n]
                if window == words or window[0][:1] != words[0][:1]:
                    continue
                plain = typed[i : i + n] == window
                pairs = zip(window, words) if plain else zip(typed[i : i + n], accented)
                edits = [(device_hint._one_edit(x, y), y) for x, y in pairs]
                if sum(e for e, _ in edits) == 1 and all(len(y) >= 4 for e, y in edits if e):
                    found.append((device, i, i + n))
    naming = device_hint._naming()
    for brand, makes in naming["brands"].items():
        n = len(brand)
        for at in range(len(folded) - n + 1):
            if tuple(folded[at : at + n]) != brand:
                continue
            candidates = [d for d in makes if d in known]
            start, best = at, None
            for head, kinds in naming["heads"].items():
                for h in range(max(0, at - 4), at - len(head) + 1):
                    if tuple(folded[h : h + len(head)]) == head and (best is None or len(head) > len(best)):
                        best, start = head, h
            if best is not None:
                candidates = [d for d in candidates if d in naming["heads"][best]] or candidates
            if len(candidates) > 1:
                after = folded[at + n : at + n + 10]
                for cue, points_to in naming["cues"].items():
                    if any(tuple(after[i : i + len(cue)]) == cue for i in range(len(after))):
                        candidates = [d for d in candidates if d in points_to] or candidates
            if len(candidates) == 1:
                found.append((candidates[0], start, at + n))
    found = [_what_it_is(m, folded) for m in found]
    found = [m for m in found if m is not None]
    found.sort(key=lambda m: (m[1], -(m[2] - m[1])))
    kept: List[tuple] = []
    for mention in found:
        if any(mention[1] < k[2] and k[1] < mention[2] for k in kept):
            continue
        # Right after another appliance's name it is a part of that one:
        # "vòi bồn rửa", "xi phông bồn rửa" is the sink's tap, the sink's trap.
        # Against every name found, kept or not: in "vặn vòi bồn rửa" the tap
        # is left out as an object, and the sink after it is still its sink.
        if any(f[2] == mention[1] and f[0] != mention[0] for f in found):
            continue
        before = typed[mention[1] - 2 : mention[1]] if mention[1] else []
        # "Ngoài ra tủ lạnh...", "kèm theo cái quạt": the "ra" and the "theo"
        # belong to the connector, which opens the next appliance.
        joined = " ".join(_fold_vi(w) for w in before)
        if joined in _TWO_WORD_CONNECTORS or _punctuated_before(text, mention[1]):
            # Nor across a comma: "...bên trong, lò nướng set 160 độ", "...ấn
            # vào không nảy lên, khóa Xiaomi" start a new clause.
            kept.append(mention)
            continue
        if any(w in _AS_AN_OBJECT for w in before[-1:]) or (
            len(before) == 2 and before[-1] in ("cái", "chiếc", "con") and before[0] in _AS_AN_OBJECT
        ):
            continue
        kept.append(mention)
    if not kept or not re.search(r"[,.;!?\n]", text):
        return kept
    # Someone who uses punctuation starts a new appliance at a new clause: after
    # a comma or full stop, or a connecting word ("còn", "với lại", "thêm").
    # In the middle of a clause the name is part of what is being described:
    # "ổ cắm cứ mỗi khi máy lạnh chạy là nóng" is about the socket.
    starts = [m.start() for m in re.finditer(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))]
    norm = unicodedata.normalize("NFC", text.lower())
    clause: List[tuple] = []
    for mention in kept:
        i = mention[1]
        if clause and clause[-1][0] == mention[0]:
            clause.append(mention)
            continue
        gap = norm[: starts[i]] if i < len(starts) else norm
        prev = typed[max(0, i - 3) : i]
        opens = (
            not clause
            or bool(re.search(r"[,.;!?:\n-]\s*(?:\S+\s*){0,2}$", gap))
            or any(w in _CONNECTORS or (w == _fold_vi(w) and w in _FOLDED_CONNECTORS) for w in prev)
        )
        if opens:
            clause.append(mention)
    return clause


_CONNECTORS = frozenset(
    "còn với lại cả ngoài ra thêm nữa và rồi xong mà kèm theo quên nhân tiện luôn".split()
)
"""Words that move a message from one appliance to the next."""

_FOLDED_CONNECTORS = frozenset(_fold_vi(w) for w in _CONNECTORS)
"""The same typed without accents: "va bep gas cai num xoay cung ngac"."""

_FILLERS = re.compile(
    r"(?<![^\W_])(?:nói chung là|kiểu là|kiểu như là|ừm+|ờm*|ừ+|hmm+|ơ+|à+)(?![^\W_])\s*",
    re.IGNORECASE,
)
"""Words a dictated message is full of: "quạt à trần", "bếp kiểu là từ", "ổ ừm
cắm". They fall inside the names of the appliances, which were then not found.
Matched with their accents, so "a" and "o" typed plainly are left alone."""


def _without_fillers(text: str) -> str:
    """The message without the spoken fillers (see _FILLERS)."""
    cleaned = _FILLERS.sub("", unicodedata.normalize("NFC", text))
    return re.sub(r"\s+([,.!?])", r"\1", re.sub(r"[ \t]{2,}", " ", cleaned)).strip()


def _said_once(text: str) -> str:
    """A reply about several appliances with each wordless sentence said once.

    Two appliances whose repair is not open each closed with "Anh/chị cần sửa
    thiết bị khác thì nhắn em nhé" in the same reply. Sentences with a figure
    in them are kept every time: the same price can be right for two
    appliances.
    """
    seen = set()
    out = []
    for block in text.split("\n\n"):
        kept = []
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            key = sentence.strip().lower()
            if len(key) > 25 and not re.search(r"\d", key) and key in seen:
                continue
            seen.add(key)
            kept.append(sentence)
        if kept:
            out.append(" ".join(kept))
    return "\n\n".join(b for b in out if b.strip())


def _punctuated_before(text: str, index: int) -> bool:
    """Whether punctuation stands between word `index` and the word before it."""
    spans = [m.span() for m in re.finditer(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))]
    if index <= 0 or index >= len(spans):
        return index == 0
    gap = unicodedata.normalize("NFC", text.lower())[spans[index - 1][1] : spans[index][0]]
    return bool(re.search(r"[,.;!?:\n]", gap))


_TWO_WORD_CONNECTORS = frozenset(("ngoai ra", "kem theo", "voi lai", "them nua", "nhan tien", "con lai"))
"""Connectors whose second word is also one that makes a noun an object."""


def _split_by_appliance(text: str, kb: KnowledgeBase) -> List[tuple]:
    """[(device, words about it)] in the order the customer brought them up.

    Cut where a different appliance is first named, whatever the punctuation:
    voice typing and "không dấu câu" give one long run of words, and cutting
    only at commas left all of it to the first appliance. Words before the
    first name belong to it; an appliance named twice gets both pieces."""
    norm = unicodedata.normalize("NFC", text)
    spans = [m.span() for m in re.finditer(r"[^\W_]+", norm.lower())]
    mentions = _appliance_mentions(norm, kb)
    cuts = []
    for device, start, _end in mentions:
        if not cuts or cuts[-1][0] != device:
            cuts.append((device, start))
    if len({d for d, _ in cuts}) < 2 or len(spans) != len(re.findall(r"[^\W_]+", norm.lower())):
        return []
    pieces: dict = {}
    for i, (device, start) in enumerate(cuts):
        begin = 0 if i == 0 else spans[start][0]
        end = spans[cuts[i + 1][1]][0] if i + 1 < len(cuts) else len(norm)
        piece = norm[begin:end].strip(" ,.;:-")
        piece = re.sub(r"\s*(?:,|\.|;)?\s*(?:còn|với lại|với cả|ngoài ra|thêm nữa|thêm cái|thêm|và|rồi|cả|xong|mà|kèm theo|à quên)$", "", piece, flags=re.IGNORECASE).strip(" ,.;:-")
        if piece:
            pieces[device] = f"{pieces[device]} {piece}".strip() if device in pieces else piece
    return list(pieces.items()) if len(pieces) >= 2 else []


def _strongly_named_in(text: str, kb: KnowledgeBase) -> Optional[str]:
    """The one appliance this text names by a machine's name, if exactly one."""
    devices = {
        device
        for device, alias, _start, _end in _named_spans(text, kb)
        if ([w for w in re.findall(r"[a-z0-9]+", _fold_vi(alias)) if w not in ("cai", "chiec")] or [""])[0]
        in _DEVICE_HEADS
    }
    return devices.pop() if len(devices) == 1 else None


def _device_named_in(question: str, kb: KnowledgeBase) -> Optional[str]:
    """The appliance the customer named, when nobody passed one in.

    A chat box has no photograph and usually no device field, least of all on
    the first message — but the customer almost always names the appliance,
    because that is how people describe a problem. Without this the corpus was
    unreachable from the question box unless the client happened to fill in a
    field it has no way of knowing yet.

    Only used when nothing better is known: an appliance settled by a
    photograph or by an earlier message in the same session always wins, since
    a later sentence mentioning a fridge does not mean the air conditioner
    stopped being the subject.
    """
    named = device_hint.devices_named_in(question, kb)
    return named[0].device_type if len(named) == 1 else None


_ASKS_FOR = ("doi sang", "doi qua", "doi thanh", "chuyen sang", "chuyen qua", "doi lai thanh", "ma la")
"""Phrases where the appliance the customer wants is named straight after.

"đổi sang vệ sinh máy lạnh", "chuyển qua tủ lạnh đi". There is nothing to work
out: the next appliance named is the one they asked for.
"""

_REJECTS = (
    "thay vi", "thay cho", "chu khong phai", "khong phai", "khong con",
    "bo", "huy", "thoi khong", "khong lay", "khong can", "dung dat",
)
"""Phrases where the appliance named next is the one being turned down.

This is the shape that the first version got wrong, because it assumed the
rejection always came second. Customers put it on either side:

    "thợ tủ lạnh thay vì thợ máy lạnh"      the air conditioning is refused
    "không phải máy lạnh đâu, tủ lạnh"      the air conditioning is refused
    "bỏ máy lạnh đi, đặt tủ lạnh"           the air conditioning is refused

In all three the marker sits immediately before the appliance being dropped,
and what the customer wants is simply the other one they named. Reading the
position of the wanted appliance instead of the position of the refusal made
half of these resolve to nothing.
"""


def _first_device_in(folded_text: str, kb: KnowledgeBase) -> Optional[str]:
    """The appliance named earliest in an already-folded string.

    Needed because a refusal marker is followed by the appliance being refused
    and then, often, by the one being asked for: "bỏ máy lạnh đi, đặt tủ lạnh".
    Resolving the whole tail finds two appliances and gives up, which left
    every sentence of this shape changing nothing.
    """
    earliest: Optional[str] = None
    earliest_at = len(folded_text) + 1

    for hint in device_hint.devices_named_in(folded_text, kb):
        for alias in kb.aliases_vi(hint.device_type):
            at = folded_text.find(_fold_vi(alias).strip())
            if 0 <= at < earliest_at:
                earliest_at = at
                earliest = hint.device_type

    return earliest


def _device_asked_for_now(latest: str, kb: KnowledgeBase, strong: bool = False) -> Optional[str]:
    """The appliance this turn asks for, when it is changing the subject.

    A session remembers the appliance so a bare follow-up still means
    something, and that is right until the customer changes their mind. Then it
    is exactly wrong: told "máy lạnh không mát" and then "em đổi ý, đặt thợ sửa
    ống nước nhé", the service offered stayed air conditioning, because the
    remembered appliance beat the sentence that had just replaced it. Measured
    on the running service: every way of asking to switch came back with the
    original service.

    Three steps, in order of how directly the customer said it. An explicit
    "đổi sang X" names X and needs no reasoning. Otherwise anything marked as
    refused is removed, and if exactly one appliance is left standing, that is
    the one. Failing both, a sentence naming a single appliance changes the
    subject to it.

    Naming two appliances with no marker at all still resolves to nothing:
    "máy lạnh với tủ lạnh nhà em đều cũ rồi" is one sentence about two
    machines, and guessing which to book is worse than leaving the session in
    charge.

    Returns None when this turn changes nothing, which is the common case.
    """
    if strong:
        # Typed the way people type: "khônggggg phải", "hông phải", "cais tur
        # lạnh", "lof nướng". With an appliance to drift from, names and
        # markers are read on the normalised text, accents kept.
        from app.services.pipeline import dialogue_state

        latest = dialogue_state.get_lexicon(kb).normalize_accented(latest)

    folded = _fold_vi(latest)
    padded = " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "

    for phrase in _ASKS_FOR:
        position = padded.find(f" {phrase} ")
        if position >= 0:
            wanted = _device_named_in(padded[position + len(phrase) :], kb)
            if wanted:
                return wanted

    refused = set()
    for phrase in _REJECTS:
        position = padded.find(f" {phrase} ")
        while position >= 0:
            # Only as far as the next refusal or the end: "bỏ máy lạnh đi, đặt
            # tủ lạnh" must refuse the air conditioner without also refusing
            # the fridge that follows it.
            after = padded[position + len(phrase) + 1 :]
            dropped = _first_device_in(after, kb)
            if dropped:
                refused.add(dropped)
            position = padded.find(f" {phrase} ", position + 1)

    if refused:
        named = [d.device_type for d in device_hint.devices_named_in(padded, kb)]
        if strong:
            # Whole words, one mention per place: "quạt trần" is not also "cái quạt".
            named = list(dict.fromkeys(span[0] for span in _named_spans(latest, kb)))
        left = [d for d in named if d not in refused]
        if len(left) == 1:
            return left[0]

    # With an appliance already in the conversation (`strong`), only a
    # machine's name moves it - see _DEVICE_HEADS. Without one, or when the
    # customer is asking for a tradesman ("đặt cho anh thợ điện"), any mention
    # will do, because there is nothing to drift away from.
    if not strong:
        return _device_named_in(latest, kb)

    # No marker at all. A turn that names one appliance on its own still
    # changes the subject - "tủ lạnh cũng hỏng nữa" is about the fridge now -
    # and a turn naming none leaves the session's appliance alone. Named, not
    # mentioned: a part or a setting ("phích cắm", "nóng lạnh") is not a new
    # subject. See _DEVICE_HEADS.
    return _strongly_named_in(latest, kb)


_NEXT_ONE = ("xem tiep", "tiep di", "tiep theo", "cai kia", "cai con lai", "con lai", "xem cai kia", "the con", "tiep", "xem tip", "tip di")
"""Asking for the appliance that was waiting: "xem tiếp", "còn cái kia thì sao"."""

_ALSO = ("còn", "thêm", "nữa", "với cả", "với lại", "ngoài ra", "cả", "luôn", "cái này", "cái nữa", "thì")
"""Words that add an appliance to the visit rather than swap one: "còn cái
quạt nữa", "thêm cái lò vi sóng", "với cả bình nóng lạnh", "à cái tivi thì
mất tiếng" (the "thì" that sets one appliance against the one before)."""

def _says_also(text: str) -> bool:
    """Whether the message adds an appliance (see _ALSO).

    Read with its accents: folded, "còn" is "con", the child in "con nhỏ nó
    cứ hỏi", and "cả" is "cá". Typed without any accent, the folded words are
    all there is to go on.
    """
    accented = " " + " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text.lower()))) + " "
    if any(f" {w} " in accented for w in _ALSO):
        return True
    if _fold_vi(text) != text.lower():
        return False
    folded = " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "
    return any(f" {_fold_vi(w)} " in folded for w in _ALSO)


_ADDS_NEW = ("còn", "thêm", "cái này", "ngoài ra", "với cả", "với lại", "nhân tiện")
"""The stronger half of _ALSO: words that bring up one more thing, not "nữa",
"luôn" or "thì", which as often add a symptom to the same appliance."""


def _adds_something(text: str) -> bool:
    """Whether the message brings up something new (see _ADDS_NEW)."""
    accented = " " + " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text.lower()))) + " "
    if any(f" {w} " in accented for w in _ADDS_NEW):
        return True
    if _fold_vi(text) != text.lower():
        return False
    folded = " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "
    return any(f" {_fold_vi(w)} " in folded for w in _ADDS_NEW)


_POINTS_BACK = ("no", "cai do", "may do", "con do", "cai may do", "chiec do")
"""The appliance just talked about, by pronoun: "nó kêu to", "cái đó sửa
bao nhiêu". These stay on it whatever the symptom would suggest. Not "cái này":
with it the customer points at something new ("còn cái này nữa")."""

_ORDINAL_WORDS = {
    "1": 0, "mot": 0, "nhat": 0, "dau": 0, "dau tien": 0,
    "2": 1, "hai": 1, "nhi": 1,
    "3": 2, "ba": 2,
    "cuoi": -1, "cuoi cung": -1,
}
_ORDINAL = re.compile(
    r"\b(?:(?:anh|hinh|tam)\s+(?:so\s+|thu\s+)?(1|2|3|mot|hai|ba|dau tien|dau|cuoi cung|cuoi)"
    r"|(?:cai|may|thiet bi|con|chiec)\s+(?:thu\s+(1|2|3|nhat|hai|nhi|ba)|(dau tien|cuoi cung|cuoi))"
    r"|(?:anh|hinh|tam)\s+(?:thu\s+)(nhat|nhi))\b"
)
"""Which photograph the customer means by its place: "cái thứ hai", "ảnh 3",
"tấm đầu", "máy cuối cùng". Read on the folded text, so "anh 2" typed without
accents counts, which is why a bare number is only taken after a word for a
picture and never after "cái" or "máy" ("máy 2 cửa" is a fridge)."""


_SHORT_NAMES = {
    "electric_fan": ("quạt",),
    "ceiling_fan": ("quạt",),
    "air_conditioner": ("cục lạnh", "cục nóng", "dàn nóng", "điều hòa", "máy lạnh"),
    "water_heater": ("bình", "nóng lạnh"),
    "refrigerator": ("tủ",),
    "freezer": ("tủ",),
    "microwave_oven": ("lò",),
    "oven": ("lò",),
    "television": ("tv",),
}
"""What an appliance is called once everyone knows which one is meant.

"Quạt quay yếu" names nothing on its own: a fan is also a part of the air
conditioner and the fridge. In a visit whose photographs show one fan, it is
that fan. The same for "cục lạnh", "cái bình", "cái tủ"."""

_PART_AFTER = ("gio", "dan", "tan nhiet", "hut", "cua", "dong co", "may nen", "lanh", "nong", "cap", "dien", "nuoc", "thuong")

_FOLDED_TOO_SHORT = {"tu", "lo", "binh"}
"""Short names that, typed without accents, are other words: "từ hôm qua",
"lo lắng", "bình thường". Only taken with their accents."""


def _short_named(text: str, devices: Sequence[str]) -> Optional[str]:
    """The one appliance of `devices` this text calls by its short name, if exactly one.

    Not when the short name is followed by a part ("quạt dàn lạnh", "tủ điện").
    """
    accented = " " + " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text.lower()))) + " "
    folded = " " + " ".join(re.findall(r"[a-z0-9]+", _fold_vi(text))) + " "
    found = set()
    for device in dict.fromkeys(devices):
        for short in _SHORT_NAMES.get(device, ()):
            plain = _fold_vi(short)
            places = [(accented, short)] + ([] if plain in _FOLDED_TOO_SHORT else [(folded, plain)])
            for haystack, needle in places:
                for match in re.finditer(rf" {re.escape(needle)} ", haystack):
                    after = _fold_vi(haystack[match.end():])
                    if len(needle.split()) == 1 and any(after.startswith(w + " ") for w in _PART_AFTER):
                        continue
                    found.add(device)
    return found.pop() if len(found) == 1 else None


def _photo_ordinal(folded: str) -> Optional[int]:
    """The position of the photograph a message points at, 0-based, -1 for the last."""
    match = _ORDINAL.search(folded)
    if not match:
        return None
    word = next(g for g in match.groups() if g)
    return _ORDINAL_WORDS.get(word)

_CORRECTION_MARKERS = (
    "khong phai", "chu khong", "ma la", "nham", "sua lai", "doi sang", "doi qua", "chuyen sang", "chuyen qua",
    "thay vi", "bo", "huy", "hong phai", "ko phai", "k phai", "kp", "no phai", "dau phai",
)

_MARKER_ACCENTS = {"bo": {"bỏ"}, "huy": {"huỷ", "hủy"}, "nham": {"nhầm"}}
"""One-word markers that, folded, are other words ("bộ", "bo mạch", "huy
hiệu"): typed with accents, only these spellings are the marker."""

_BETWEEN_MARKER_AND_NAME = frozenset(("la", "cai", "chiec", "con", "phai", "sang", "qua", "thanh", "di", "dau", "ma"))
"""What may stand between a marker and the appliance it is about: "không
phải là cái máy lạnh", "đổi sang con tủ lạnh". Anything else and the marker
belongs to the sentence: "chứ không quay trớn và bếp Taka"."""

_NAMES_NEXT = frozenset(("khong phai", "ko phai", "k phai", "hong phai", "chu khong phai", "thay vi", "ma la", "doi sang", "chuyen sang"))
"""Markers that can only be followed by the appliance they correct."""

_REFUSED_AFTER = ("thoi khong", "khong can", "dung dat", "huy")
"""Refusals that come after the appliance they drop: "máy lạnh thì thôi
không cần nữa", "tủ lạnh huỷ đi"."""


def _corrects_an_appliance(text: str, kb: KnowledgeBase) -> bool:
    """Whether the message changes which appliance it is about.

    The markers ("không phải", "bỏ", "chuyển sang", "mà là") are read on the
    folded words, where "bộ" is "bỏ" and "chuyển sang gió mạnh" is "chuyển
    sang": a message about a fridge's fan and a ceiling fan's speed control
    ("hỏng bộ chỉnh") was taken for a correction and never cut, so one of the
    two appliances was lost. A marker counts only next to an appliance it
    names: just before it, or for a refusal, just after.
    """
    typed = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))
    folded = [_fold_vi(w) for w in typed]
    spans = [(start, end) for _d, start, end in _appliance_mentions(text, kb)]
    spans += [(start, end) for _d, _a, start, end in _named_spans(text, kb)]
    if not spans:
        return False
    for marker in _CORRECTION_MARKERS + _REJECTS + _ASKS_FOR:
        words = marker.split()
        n = len(words)
        for i in range(len(folded) - n + 1):
            if folded[i : i + n] != words:
                continue
            accented = _MARKER_ACCENTS.get(marker)
            if accented and typed[i] != folded[i] and typed[i] not in accented:
                # "Hư bo rồi" is the board, "bỏ" is dropping something.
                continue
            if any(
                start >= i + n
                and (
                    all(w in _BETWEEN_MARKER_AND_NAME for w in folded[i + n : start])
                    # "Không phải đường ống nước": a word of the name the
                    # alias leaves out.
                    or (marker in _NAMES_NEXT and start - (i + n) <= 1)
                )
                for start, _end in spans
            ):
                return True
            if marker in _REFUSED_AFTER and any(i - 3 <= end <= i for _start, end in spans):
                return True
    return False


_SEGMENT_RE = re.compile(r"[,.;!?\n]+|\s(?:còn|với lại|với cả|ngoài ra|thêm nữa|cũng như)\s", re.IGNORECASE)
"""Where one message moves from one appliance to the next."""


def _ranked_by_retrieval(
    chosen: Sequence[str],
    shortlist: Optional[Sequence[Any]],
    *,
    saw_a_photograph: bool,
    excluded: Optional[set] = None,
) -> List[str]:
    """Retrieval's leader first, then whatever the model chose from the shortlist.

    Which fault it is, is a fact, and the architecture says the language model
    does not contribute facts. It was contributing this one, and it was making it
    worse. Measured on the 464 diagnosis cases of the suite, against the served
    model:

        the expected fault ranked first by retrieval      429/464   92.5%
        the expected fault anywhere in retrieval's top 3  464/464  100.0%
        the model's own selection                         340/464   73.3%

    So the model was nineteen points behind simply taking the first retrieved
    fault, and the cost was not only the name: a wrong pick maps to a wrong
    service, and "quạt điện đảo gió không ăn" — a broken oscillation mechanism,
    ranked first by retrieval — came back as a damaged power cord whose only
    service is a generic inspection.

    The model's choice is kept, after retrieval's, and there is a second reason
    beyond the photograph: it can read a sentence and the scorer only counts
    words. "Máy lạnh không mát dù mới vệ sinh" excludes a dirty filter in so many
    words, and the scorer ranks a dirty filter first precisely because "vệ sinh"
    appears — 0.75 against 0.58 for the low refrigerant that is actually likely.
    The model gets that one right and retrieval gets it wrong.

    So this is a trade, not a strict improvement, and the trade is worth making
    because the response carries a shortlist rather than a single verdict: both
    faults are shown, and on average the right one is placed first far more often
    than before.

    It is also why this only applies when there is no photograph. Shown an image
    the model has evidence no ranking of the customer's words contains — a
    cracked panel, a burn mark, water under a machine — and there it stays in
    charge. That half is unmeasured and should be described as such: the suite
    sends text, and there is no set of photographs labelled by fault to measure
    it with. All the figures above are from text-only turns.

    Codes the model invented are dropped, as they were before — it may only
    choose from what was retrieved. Simulated over the same 464 cases, this rule
    takes the reported fault from 73.3 to 96.3 percent correct.

    Safety pinning is unaffected: it already keys on retrieval's own top-ranked
    fault and never read this list.
    """
    # Nothing the customer has ruled out comes back, whoever proposed it. The
    # model reads the conversation and usually respects a denial; usually is
    # not good enough for the one thing the customer has just said is wrong.
    banned = excluded or set()
    chosen = [code for code in chosen if code not in banned]
    if saw_a_photograph:
        return list(chosen)
    ranked = [getattr(f, "fault_code", None) for f in (shortlist or [])]
    ranked = [code for code in ranked if code and code not in banned]
    if not ranked:
        return list(chosen)
    kept = [code for code in chosen if code in ranked]
    leader = ranked[0]
    return [leader] + [code for code in kept if code != leader]


class LocalPipeline:
    """The self-hosted diagnosis pipeline.

    Stages: detect the device, retrieve candidate faults for that device, let
    the VLM read the crop and the description and choose among the candidates,
    then resolve every code back to curated Vietnamese content.
    """

    def __init__(
        self,
        detector: Detector,
        vlm: VisionLanguageModel,
        retriever: Retriever,
        kb: KnowledgeBase,
    ) -> None:
        self._detector = detector
        self._vlm = vlm
        self._retriever = retriever
        self._kb = kb
        self._conversations = get_conversation_store()
        self._seen_photos: "OrderedDict[str, Optional[Detection]]" = OrderedDict()
        kb_version = getattr(kb, "version", None)
        self._model_info = ModelInfo(
            # Path rather than a name, because the name is always "best.pt" and
            # the run it came from is the only thing that identifies it.
            detector=settings.YOLO_WEIGHTS_PATH or None,
            vlm=settings.VLM_MODEL_NAME if settings.VLM_BASE_URL else None,
            knowledge_base_version=kb_version,
        )

    def _read_turn(
        self,
        chat: Conversation,
        text: str,
        device_type: Optional[str],
        trace: Optional["_Trace"] = None,
    ) -> dialogue_state.TurnReading:
        """Read what this message establishes, before anything retrieves on it.

        Against the appliance being talked about when it is known, and against
        every appliance when it is not; exclusions are per fault code, so the
        wider read cannot leak into another appliance's shortlist.
        """
        pool = (
            self._kb.faults_for_device(device_type)
            if device_type
            else [f for d in self._kb.device_types for f in self._kb.faults_for_device(d)]
        )
        lexicon = dialogue_state.get_lexicon(self._kb)
        reading = dialogue_state.read_turn(
            text,
            pool,
            previous_codes=chat.shortlist,
            lexicon=lexicon,
        )
        shown = self._display_code(chat, text, device_type)
        if shown is not None and shown.entry is not None:
            for code in shown.entry.faults:
                chat.state.from_codes[code] = error_codes.CODE_BOOST
            # "hãng daikin" or "báo lỗi E8" carries no symptom, and a boost on a
            # fault the search scored at nothing is still nothing. The fault the
            # brand's table names is searched for by its name and symptoms too.
            names = []
            for c in shown.entry.faults:
                fault = self._kb.fault(c)
                if fault is not None:
                    names += [fault.name_vi, *fault.symptoms_vi[:2]]
            if names:
                reading.retrieval_text = " ".join([reading.retrieval_text or text, *names])
        # The answer to the question we just asked. Read before anything else
        # has a chance to call "không" a denial of the last answer.
        question, chat.pending_question = chat.pending_question, None
        if question and not chat.awaiting_confusion_about:
            answer = dialogue_state.answer_to(
                question,
                text,
                pool,
                self._kb.discriminators_for_device(device_type),
                lexicon,
            )
            if answer is not None:
                reading.exclusions = [
                    e for e in reading.exclusions if e.kind != "previous"
                ]
                reading.denied_previous = False
                for code, factor in answer.factors.items():
                    if factor >= 1.0:
                        reading.boosts[code] = max(factor, reading.boosts.get(code, 1.0))
                    else:
                        reading.penalties[code] = min(factor, reading.penalties.get(code, 1.0))
                reading.retrieval_text = " ".join(
                    part for part in (answer.said, reading.retrieval_text if answer.rest else "") if part
                )
                if trace is not None:
                    trace.add(
                        "dialogue",
                        True,
                        f"Khách trả lời {'có' if answer.yes else 'không'} cho: {question}",
                        answer="yes" if answer.yes else "no",
                        factors=answer.factors,
                    )
        chat.observe(reading, dialogue_state.never_excluded_codes())
        if trace is not None and (
            reading.exclusions or reading.penalties or reading.reinstated
        ):
            trace.add(
                "dialogue",
                True,
                "Khách loại trừ: "
                + (", ".join(e.fault_code for e in reading.exclusions) or "không")
                + (f"; hạ điểm: {', '.join(reading.penalties)}" if reading.penalties else ""),
                excluded=[
                    {"code": e.fault_code, "how": e.kind, "phrase": e.phrase_vi}
                    for e in reading.exclusions
                ],
                penalized=dict(reading.penalties),
                reinstated=list(reading.reinstated),
                retrieval_text=reading.retrieval_text,
            )
        return reading

    def _acknowledgement(
        self, chat: Conversation, device_type: Optional[str], next_code: Optional[str]
    ) -> Optional[str]:
        """The sentence that tells the customer what they ruled out was heard.

        Only for what this turn newly ruled out, and only for the appliance the
        answer is about: read against every appliance, "đã vệ sinh" also rules
        out a scaled kettle, which nobody in this conversation mentioned.
        """

        def name_of(code: str) -> Optional[str]:
            fault = self._kb.fault(code)
            return fault.name_vi if fault else None

        fresh = []
        for exclusion in chat.state.last_new:
            fault = self._kb.fault(exclusion.fault_code)
            if fault is None:
                continue
            if device_type is not None and fault.device_type != device_type:
                continue
            fresh.append(exclusion)
        if not fresh:
            return None
        nxt = None
        if next_code and next_code not in chat.state.excluded:
            nxt = name_of(next_code)
        return dialogue_state.acknowledgement_vi(fresh, name_of, nxt)

    def _resume(self, chat: Conversation, requested_id: Optional[str], history) -> None:
        """Rebuild a lost conversation from what the customer said before.

        Only into a conversation that was just created in place of the one the
        client named; see `history` on the request. Each earlier message is read
        the way it was read the first time, so what it ruled out is ruled out
        again, and the device it named is the device again.
        """
        if not history or not self._conversations.resumed(chat, requested_id):
            return
        for text in list(history)[-20:]:
            text = (text or "").strip()[:2000]
            if not text:
                continue
            chat.add("customer", text)
            named = (
                _device_asked_for_now(text, self._kb, strong=True)
                if chat.device_type
                else _device_named_in(text, self._kb)
            )
            if named and chat.device_type is None:
                chat.remember_device(named, 0.6, "memory")
            self._read_turn(chat, text, named or chat.device_type)
        # What the replay ruled out was acknowledged when it was first said.
        chat.state.last_new = []

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        async with self._conversations.lock(request.session_id):
            return await self._diagnose_locked(request)

    async def _diagnose_locked(self, request: DiagnosisRequest) -> DiagnosisResponse:
        response = await self._diagnose_routed(request)
        return self._with_photo_guesses(response, request)

    def _with_photo_guesses(self, response: DiagnosisResponse, request: DiagnosisRequest) -> DiagnosisResponse:
        """What each photograph of this request was read as, and the guesses said aloud.

        Not a question: the diagnosis goes on, and the customer who sees a
        guess is wrong says so in a word ("ảnh 2 là tủ lạnh"), or with the
        label the client shows under the photograph."""
        if not request.images:
            return response
        readings = []
        for index, image in enumerate(request.images[:3]):
            seen = self._seen_photos.get(hashlib.sha1(image.encode("ascii", "ignore")).hexdigest())
            device_type = seen.device_type if seen is not None else None
            uncertain = bool(seen is not None and seen.uncertain)
            if len(request.images) == 1 and response.device is not None:
                # One photograph and the words named its appliance: it is that one.
                device_type = response.device.device_type
                uncertain = response.device.uncertain
            name = self._kb.device_name_vi(device_type) if device_type else None
            readings.append(PhotoReading(index=index, device_type=device_type, name_vi=name, uncertain=uncertain))
        guessed = [(r.index, r.name_vi) for r in readings if r.uncertain and r.name_vi]
        update = {"photos": readings}
        if guessed:
            several = len(request.images) > 1
            said = [f"{'ảnh ' + str(i + 1) if several else 'ảnh'} là {name.lower()}" for i, name in guessed]
            example = f"ảnh {guessed[0][0] + 1} là ..." if several else "ảnh là ..."
            note = f"Em đoán {', '.join(said)}, nếu chưa đúng anh/chị nhắn em \"{example}\" để em xem lại nhé."
            update["message_vi"] = f"{response.message_vi}\n\n{note}" if response.message_vi else note
        return response.model_copy(update=update)

    def _photo_fix(self, chat: Conversation, text: str) -> Optional[tuple]:
        """(photograph index, appliance it shows) for "ảnh 2 là tủ lạnh", if this says so."""
        folded = " " + dialogue_state.get_lexicon(self._kb).normalize(text) + " "
        match = re.search(
            r" (?:anh|hinh|tam)(?: anh)?\s*(?:so |thu )?(1|2|3|mot|hai|ba|nay|do)?\s*(?:la|moi la|phai la|chup)\s+(.+)",
            folded,
        )
        if not match:
            return None
        rest = match.group(2)
        device = _strongly_named_in(dialogue_state.get_lexicon(self._kb).normalize_accented(rest), self._kb) or _device_named_in(
            rest, self._kb
        )
        if device is None:
            return None
        photos = chat.memo.get("", {}).get("photos", [])
        word = match.group(1)
        if word in ("nay", "do", None):
            place = len(photos) - 1 if photos else 0
        else:
            place = _ORDINAL_WORDS.get(word, 0)
        return place, device

    def _visit_prep_text(self, chat: Conversation, text: str) -> str:
        """What to get ready, for the appliance the message names, else the visit's."""
        lexicon = dialogue_state.get_lexicon(self._kb)
        named = _strongly_named_in(lexicon.normalize_accented(text), self._kb) or _device_named_in(text, self._kb)
        if named:
            appliances = [named]
        else:
            lead = chat.memo.get("", {}).get("lead")
            appliances = list(dict.fromkeys(d for d in [lead, chat.device_type, *chat.others] if d))
        return visit_prep.reply_vi([(d, self._kb.device_name_vi(d) or d) for d in appliances[:3]])

    def _visit_prep_response(self, request: DiagnosisRequest) -> DiagnosisResponse:
        """The same, on the diagnosis route, with the visit's appliances kept on the reply.

        Kept because the client rebuilds its booking bar from `devices` on
        every reply, and a reply without them would take the bar away."""
        chat = self._conversations.get_or_create(request.session_id)
        chat.add("customer", request.description)
        response = DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.OK,
            message_vi=dialogue_state.address_as(self._visit_prep_text(chat, request.description), chat.address),
            confidence=0.9,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )
        lead = chat.memo.get("", {}).get("lead") or chat.device_type
        order = list(dict.fromkeys(d for d in [lead, chat.device_type, *chat.kept, *chat.others] if d))[:3]
        if len(order) < 2:
            return response
        devices = [self._device_entry(d, chat, i == 0, None) for i, d in enumerate(order)]
        services = [e.service.model_copy(update={"device_type": e.device_type}) for e in devices if e.service is not None]
        return response.model_copy(update={"devices": devices, "recommended_services": services})

    async def _diagnose_routed(self, request: DiagnosisRequest) -> DiagnosisResponse:
        if not request.images and visit_prep.asks_how_to_prepare(request.description):
            return self._visit_prep_response(request)
        known = self._conversations.peek(request.session_id)
        fix = (
            self._photo_fix(known, request.description)
            if known is not None and known.parent_id is None and known.device_type and not request.images
            else None
        )
        if fix is not None:
            corrected = await self._correct_photo(known, request, *fix)
            if corrected is not None:
                return corrected
        photographed: List[Optional[Detection]] = []
        if known is not None and known.parent_id is None and known.device_type and request.images:
            photographed = list(
                await asyncio.gather(*(self._safe_detect(i) for i in request.images[:3]))
            )
        target = None
        if known is not None and known.parent_id is None:
            target = self._other_device_asked(known, request.description, photographed, bool(request.images))
        if known is not None and target:
            self._remember_photos(known, photographed)
            index = next(
                (i for i, d in enumerate(photographed) if d is not None and d.device_type == target), None
            )
            if index is not None:
                # Only its own photograph: the others in the same message are
                # the visit's to place, not this appliance's to diagnose.
                known.memo.setdefault(target, {}).update(
                    {"image_index": index, "confidence": photographed[index].confidence}
                )
                request = request.model_copy(update={"images": [request.images[index]]})
            elif photographed:
                request = request.model_copy(update={"images": []})
            return await self._answer_other(known, target, request)
        response = await self._diagnose_one(request)
        if not response.session_id:
            return response
        chat = self._conversations.get_or_create(response.session_id)
        fresh: List[str] = []
        if chat.parent_id is None:
            fresh = await self._answer_others(chat, request)
            chat.memo.setdefault("", {})["lead"] = chat.device_type
            if request.images:
                self._remember_photos(
                    chat,
                    photographed
                    or [self._seen_photos.get(hashlib.sha1(i.encode("ascii", "ignore")).hexdigest()) for i in request.images[:3]],
                )
        return self._with_devices(response, chat, request.description, fresh=fresh)

    async def _correct_photo(
        self, chat: Conversation, request: DiagnosisRequest, place: int, device_type: str
    ) -> Optional[DiagnosisResponse]:
        """The customer says photograph `place` shows `device_type`.

        The appliance it was taken for leaves the visit and the named one takes
        its place, asked what is wrong with it like any appliance only seen in
        a photograph; when it was the conversation's own appliance, the
        ordinary correction ("không phải X mà là Y") does the switch."""
        photos = chat.memo.setdefault("", {}).setdefault("photos", [])
        old = photos[place] if 0 <= place < len(photos) else None
        if old == device_type:
            return None
        if 0 <= place < len(photos):
            photos[place] = device_type
        old_memo = chat.memo.get(old, {}) if old else {}
        new_memo = chat.memo.setdefault(device_type, {})
        if old_memo.get("image_index") is not None:
            new_memo["image_index"] = old_memo["image_index"]
        new_memo["uncertain"] = False
        name = (self._kb.device_name_vi(device_type) or device_type).lower()
        if old is not None and old == chat.device_type:
            old_name = (self._kb.device_name_vi(old) or old).lower()
            switched = request.model_copy(update={"description": f"không phải {old_name} mà là {name}"})
            # diagnose() already holds the visit's lock for this turn.
            response = await self._diagnose_one(switched)
            chat.memo.setdefault("", {})["lead"] = device_type
            return self._with_devices(response, chat, switched.description)
        if old is not None:
            chat.others.pop(old, None)
            chat.queued.pop(old, None)
            chat.memo.pop(old, None)
        if device_type not in chat.others and device_type != chat.device_type:
            self._join_visit(chat, device_type, 0.0, "image")
        if device_type == chat.device_type:
            return None
        return await self._answer_other(chat, device_type, request.model_copy(update={"description": name}))

    @staticmethod
    def _remember_photos(chat: Conversation, found: Sequence[Optional[Detection]]) -> None:
        """Every photograph of the visit in the order it was sent, by appliance."""
        if found:
            chat.memo.setdefault("", {}).setdefault("photos", []).extend(
                d.device_type if d is not None else None for d in found
            )

    def _join_visit(self, chat: Conversation, device_type: str, confidence: float, source: str) -> str:
        """A conversation of its own for an appliance added to the visit mid-way."""
        own = self._conversations.get_or_create(None)
        own.remember_device(device_type, confidence, source)
        own.parent_id = chat.session_id
        chat.others[device_type] = own.session_id
        chat.queued.pop(device_type, None)
        return device_type

    async def _diagnose_one(self, request: DiagnosisRequest) -> DiagnosisResponse:
        """One appliance's turn, with everything said around the answer."""
        response = await self._diagnose_turn(request)
        if not response.session_id:
            return response
        chat = self._conversations.get_or_create(response.session_id)
        device_type = (
            response.device.device_type if response.device else chat.device_type
        )
        next_code = (
            response.suspected_faults[0].fault_code if response.suspected_faults else None
        )
        ack = self._acknowledgement(chat, device_type, next_code)
        message = response.message_vi
        if ack:
            message = f"{ack} {message}" if message else ack
        urgent = response.urgency == UrgencyLevel.HIGH
        if urgent and not response.suggested_actions_vi and chat.state.danger:
            # "hôi mùi gas" alone: urgency was right, but the reply was only a
            # question about the stove, and the customer was told nothing to do
            # while the house smelt of gas. The steps come first, before any
            # question, from the knowledge base and never from the model.
            steps = self._safety_steps(request.description, device_type)
            if steps:
                response = response.model_copy(update={"suggested_actions_vi": steps})
                lead = "Dạ đây là dấu hiệu nguy hiểm, anh/chị làm ngay giúp em: " + "; ".join(
                    step[:1].lower() + step[1:] for step in steps
                ) + "."
                message = f"{lead} {message}" if message else lead
        code_line = self._error_code_line(chat, request.description, urgent)
        message = self._framed(chat, message, urgent, extra=code_line)
        clarification = response.clarification
        if clarification is not None and chat.address:
            clarification = clarification.model_copy(
                update={
                    "questions_vi": [
                        dialogue_state.address_as(q, chat.address) for q in clarification.questions_vi
                    ]
                }
            )
        notes = chat.notes_vi(self._kb)
        if message != response.message_vi or clarification is not response.clarification or notes:
            response = response.model_copy(
                update={"message_vi": message, "clarification": clarification, "notes_vi": notes}
            )
        return response

    def _other_device_asked(
        self,
        chat: Conversation,
        text: str,
        photographed: Sequence[Optional[Detection]] = (),
        has_photos: bool = False,
    ) -> Optional[str]:
        """The other appliance of the visit this message is about, if any.

        In order: named outright ("còn máy giặt thì sao"); shown in the
        photograph sent with it; pointed at by its place among the photographs
        ("cái thứ hai", "ảnh 3"); the next one asked for ("xem tiếp"); or, when
        the message names nothing, the appliance the last answer was about, so
        "nó kêu to nữa" after the washing machine stays on the washing machine.

        An appliance not yet in the visit joins it with a conversation of its
        own when a photograph shows it or the message adds it ("còn cái quạt
        nữa"), instead of replacing the one already being talked through.
        """
        if not chat.device_type:
            # Nothing is being talked through yet: whatever is named is the
            # conversation's own appliance, not one added to it.
            return None
        lexicon = dialogue_state.get_lexicon(self._kb)
        accented = lexicon.normalize_accented(text)
        folded = " " + lexicon.normalize(text) + " "
        named = _strongly_named_in(accented, self._kb)
        mentioned = {d for d, _start, _end in _appliance_mentions(text, self._kb)} | (
            {named} if named else set()
        )
        # A correction is about an appliance it names. Without one, "không lấy
        # nước vào" and "không còn lạnh" are symptoms, not "không lấy máy lạnh".
        correcting = bool(mentioned) and any(
            f" {m} " in folded for m in _CORRECTION_MARKERS + _REJECTS + _ASKS_FOR
        )
        visit = [d for d in [chat.device_type, *chat.others] if d]
        if not named and not mentioned:
            named = _short_named(text, visit + [d.device_type for d in photographed if d is not None])
            if named:
                mentioned = {named}
        if named in chat.others and named != chat.device_type:
            return named
        if named and named == chat.device_type:
            return None
        seen = [d for d in photographed if d is not None]
        if seen and not correcting and len(mentioned) <= 1:
            if not named:
                # No name, but a symptom only one appliance has ("đá không
                # đông", "nóng một lúc rồi nguội"): when the detector reads the
                # photograph as something else, the words are the better witness.
                described = self._device_from_symptom(text)
                if described and all(d.device_type != described for d in seen):
                    named = described
            shown = next((d for d in seen if d.device_type == named), None) if named else seen[0]
            if shown is not None and shown.device_type != chat.device_type:
                if shown.device_type in chat.others:
                    return shown.device_type
                chat.memo.setdefault(shown.device_type, {})["uncertain"] = shown.uncertain
                return self._join_visit(chat, shown.device_type, shown.confidence, "image")
            if shown is None and named in chat.others:
                return named
            if shown is None and named and named != chat.device_type and not self._kb.confusable_with(named):
                # "Đây là bình nóng lạnh" with a photograph the detector reads
                # as something else: the appliance named joins, by its name.
                return self._join_visit(chat, named, 0.0, "description")
            return None
        if has_photos and seen:
            return None
        # A photograph the detector could not read leaves the words to decide:
        # "còn cái này nữa em, ngăn mát không lạnh" with a fridge it did not
        # recognise was answered about the air conditioner.
        added = named
        pointing_back = any(f" {p} " in folded for p in _POINTS_BACK)
        if not added and not mentioned and not pointing_back and _adds_something(text):
            # "Còn cái này nữa, quạt bật không quay": "quạt" alone names no
            # appliance (a fan is a part of several), but said as one more
            # thing to look at it is the fan most homes have. Only by that
            # name: guessed from the symptom, "với lại đọng nước dưới đế" would
            # add a water pipe to a kettle.
            added = "electric_fan" if _short_named(text, ["electric_fan"]) and "trần" not in text.lower() else None
            if added in visit:
                return added if added in chat.others else None
        if (
            added
            and added not in chat.others
            and added not in chat.queued
            and not correcting
            and len(mentioned) <= 1
            and _says_also(text)
        ):
            return self._join_visit(chat, added, 0.0, "description")
        if not chat.others:
            return None
        photos = chat.memo.get("", {}).get("photos", [])
        place = _photo_ordinal(folded)
        if place is not None and photos and not named:
            if -len(photos) <= place < len(photos):
                pointed = photos[place]
                if pointed == chat.device_type:
                    return None
                if pointed in chat.others:
                    return pointed
        if not chat.queued and any(f" {p} " in folded for p in _NEXT_ONE):
            order = list(chat.others)
            last = chat.memo.get("", {}).get("lead")
            chosen = order[(order.index(last) + 1) % len(order)] if last in order else order[0]
            chat.memo.setdefault("", {})["moving_on"] = True
            return chosen
        if correcting:
            return None
        last = chat.memo.get("", {}).get("lead")
        if not named and any(f" {p} " in folded for p in _POINTS_BACK):
            # "Mà nó chớp đèn không chạy", "nó không lấy nước vào": the light
            # and the water are in the sentence as symptoms, and "nó" is the
            # appliance the last answer was about.
            return last if last in chat.others else None
        if mentioned:
            return None
        described = self._device_from_symptom(text)
        if described == chat.device_type:
            return None
        if described in chat.others:
            return described
        if described and described not in chat.queued:
            # "Cái thứ ba thì ngăn đá không đông" when the third photograph
            # was not recognised: the words describe a fridge and nothing else,
            # so the fridge joins the visit rather than the washing machine the
            # last answer was about taking the question.
            return self._join_visit(chat, described, 0.0, "description")
        return last if last in chat.others else None

    async def _answer_other(
        self, chat: Conversation, device_type: str, request: DiagnosisRequest
    ) -> DiagnosisResponse:
        """A follow-up about another appliance, answered in its own conversation.

        The reply keeps the visit's conversation id, so the client goes on
        talking to the whole visit; only this turn is about that appliance."""
        sub_id = chat.others[device_type]
        moving_on = chat.memo.setdefault("", {}).pop("moving_on", False)
        last = chat.memo.get(device_type, {}).get("reply")
        if moving_on and last is not None:
            # "Xem tiếp" says which appliance, not what is wrong with it: its
            # latest answer is shown again, and its conversation is untouched.
            reply = last
        else:
            async with self._conversations.lock(sub_id):
                reply = await self._diagnose_one(request.model_copy(update={"session_id": sub_id}))
        if reply.session_id:
            chat.others[device_type] = reply.session_id
            self._conversations.get_or_create(reply.session_id).parent_id = chat.session_id
        chat.memo.setdefault(device_type, {})["reply"] = reply
        chat.memo.setdefault("", {})["lead"] = device_type
        reply = reply.model_copy(update={"session_id": chat.session_id})
        return self._with_devices(reply, chat, request.description, lead=device_type)

    def _ask_about_photographed(
        self, chat: Conversation, device_type: str, request: DiagnosisRequest
    ) -> DiagnosisResponse:
        """An appliance seen in a photograph and not described: ask what is wrong.

        Diagnosing it from the photograph alone would be guessing - most faults
        cannot be seen - so it gets the open question, its repair to book, and
        a conversation of its own for the answer to land in."""
        sub = self._conversations.get_or_create(None)
        memo = chat.memo.get(device_type, {})
        sub.remember_device(device_type, float(memo.get("confidence", 0.0)), "image")
        sub.parent_id = chat.session_id
        name = (self._kb.device_name_vi(device_type) or device_type).lower()
        offer = self._fallback_offer(device_type)
        question = (
            f"Dạ trong ảnh em thấy có {name}, {name} nhà mình đang bị sao ạ?"
            if offer
            else (self._not_open_note(device_type) or "")
        )
        sub.add("assistant", question)
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=sub.session_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            recommended_services=offer,
            clarification=Clarification(questions_vi=[question]) if offer else None,
            message_vi=question,
            confidence=0.0,
            model_info=self._model_info,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _answer_others(self, chat: Conversation, request: DiagnosisRequest) -> List[str]:
        """Diagnose, alongside this turn's answer, every other appliance it brought up.

        Named in the message or seen in a photograph, each is diagnosed by the
        same pipeline in a conversation of its own, all at once: the model is
        asked about each in parallel, so three appliances cost about one
        answer's time, not three. An appliance only photographed has nothing
        said about it yet, and its conversation asks what is wrong with it.
        The visit takes three appliances; any more wait in the queue."""
        waiting = [d for d in chat.queued if d != chat.device_type and d not in chat.others]
        room = max(0, 2 - len(chat.others))
        chosen = waiting[:room]
        if not chosen:
            return []

        async def one(device_type: str):
            name = self._kb.device_name_vi(device_type) or device_type
            said = (chat.queued.get(device_type) or "").strip()
            if not said:
                return device_type, self._ask_about_photographed(chat, device_type, request)
            if said and _device_named_in(said, self._kb) != device_type:
                said = f"{name} {said}"
            index = chat.memo.get(device_type, {}).get("image_index")
            images = [request.images[index]] if index is not None and index < len(request.images) else []
            own = self._conversations.get_or_create(None)
            own.remember_device(device_type, 0.0, "description")
            own.parent_id = chat.session_id
            sub = DiagnosisRequest(
                session_id=own.session_id,
                description=(said or name)[:2000],
                images=images,
                past_jobs=request.past_jobs,
                include_trace=False,
            )
            try:
                return device_type, await self._diagnose_one(sub)
            except Exception as exc:  # one appliance must not cost the others their answer
                logger.warning("Không chẩn đoán được thiết bị %s: %s", device_type, exc)
                return device_type, None

        answered = await asyncio.gather(*(one(d) for d in chosen))
        fresh = []
        for device_type, reply in answered:
            if reply is None or not reply.session_id:
                continue
            chat.queued.pop(device_type, None)
            chat.others[device_type] = reply.session_id
            self._conversations.get_or_create(reply.session_id).parent_id = chat.session_id
            chat.memo.setdefault(device_type, {})["reply"] = reply
            fresh.append(device_type)
        return fresh

    # ------------------------------------------------------------ several appliances

    def _with_devices(
        self,
        response: DiagnosisResponse,
        chat: Conversation,
        said: str,
        lead: Optional[str] = None,
        fresh: Sequence[str] = (),
    ) -> DiagnosisResponse:
        """One entry per appliance of the visit, and one service for each.

        The appliance this turn is about comes first: the conversation's own
        one, or `lead` when the turn was a follow-up about another appliance.
        Then the others, each with the last answer its own conversation gave.
        The answers to appliances diagnosed for the first time this turn
        (`fresh`) are written after the main one, appliance by appliance, so the
        customer reads every diagnosis in the same reply. Three at most:
        Backend books a visit of up to three devices.
        """
        current = chat.device_type
        if lead is None and response.device is not None:
            current = response.device.device_type
        if lead is None and current:
            for turn in chat.turns:
                if turn.role == "customer" and turn.device_type is None:
                    turn.device_type = current
            memo = chat.memo.setdefault(current, {})
            said = next((t.text_vi for t in reversed(chat.turns) if t.role == "customer"), said)
            if self._names_a_symptom(said, current) and said not in memo.get("text", ""):
                memo["text"] = f"{memo.get('text', '')} {said}".strip()
            if response.recommended_services or response.suspected_faults:
                memo["service"] = response.recommended_services[0] if response.recommended_services else None
                memo["faults"] = list(response.suspected_faults[:2])
                memo["price"] = response.price_estimate
            memo["reply"] = response
        head = lead or current
        order = list(dict.fromkeys(
            [d for d in [head, current] if d]
            + [d for d in chat.kept if d != current]
            + list(chat.others)
            + [d for d in chat.queued if d != current]
        ))
        if len(order) < 2:
            return response
        extra = len(order) - 3
        order = order[:3]
        devices = [self._device_entry(d, chat, d == head, response if d == head else None) for d in order]
        services = [
            entry.service.model_copy(update={"device_type": entry.device_type})
            for entry in devices
            if entry.service is not None
        ]
        parts = [response.message_vi] if response.message_vi else []
        for entry in devices:
            if entry.device_type in fresh and entry.message_vi:
                parts.append(f"Về {entry.name_vi.lower()}: {entry.message_vi}")
        bookable = sum(1 for entry in devices if entry.service is not None)
        # Once per change in how many can be booked, not on every turn.
        if bookable >= 2 and chat.announced_visit != bookable:
            chat.announced_visit = bookable
            parts.append(
                f"Em đã gợi ý dịch vụ cho {bookable} thiết bị, anh/chị có thể đặt chung "
                "một lượt thợ tới cho tất cả ạ."
            )
        if extra > 0:
            parts.append("Mỗi lượt đặt được tối đa 3 thiết bị, thiết bị còn lại anh/chị đặt ở lượt sau giúp em nhé.")
        urgency = response.urgency
        for entry in devices:
            if entry.urgency and _URGENCY_RANK[entry.urgency] > _URGENCY_RANK[urgency]:
                urgency = entry.urgency
        return response.model_copy(
            update={
                "devices": devices,
                "recommended_services": services,
                "message_vi": _said_once("\n\n".join(parts)) if parts else response.message_vi,
                "urgency": urgency,
            }
        )

    @staticmethod
    def _plain_finding(reply: DiagnosisResponse) -> Optional[str]:
        """The faults and price of an answer, in words, when the model wrote none."""
        if not reply.suspected_faults:
            return None
        names = " hoặc ".join(f.name_vi.lower() for f in reply.suspected_faults[:2])
        line = f"khả năng cao là {names}."
        price = reply.price_estimate
        if price and price.min:
            low = f"{price.min:,.0f}đ".replace(",", ".")
            if price.max and not price.requires_assessment:
                high = f"{price.max:,.0f}đ".replace(",", ".")
                line += f" Chi phí tham khảo {low} đến {high}."
            else:
                line += f" Chi phí tham khảo từ {low}, thợ kiểm tra rồi báo giá."
        return line[:1].upper() + line[1:]

    def _device_entry(
        self,
        device_type: str,
        chat: Conversation,
        primary: bool,
        response: Optional[DiagnosisResponse],
    ) -> DeviceSuggestion:
        memo = chat.memo.get(device_type, {})
        image_index = memo.get("image_index")
        reply = response if response is not None else memo.get("reply")
        text = (chat.queued.get(device_type) or memo.get("text") or "").strip()
        message = None
        status = None
        urgency = None
        if reply is not None:
            service = reply.recommended_services[0] if reply.recommended_services else None
            faults = list(reply.suspected_faults[:2])
            price = reply.price_estimate
            status = reply.status
            urgency = reply.urgency
            message = reply.message_vi or (
                " ".join(reply.clarification.questions_vi) if reply.clarification else None
            ) or self._plain_finding(reply)
            if device_type in chat.others:
                sub = self._conversations.peek(chat.others[device_type])
                if sub is not None:
                    text = " ".join(
                        t.text_vi for t in sub.turns
                        if t.role == "customer" and self._names_a_symptom(t.text_vi, device_type)
                    ).strip() or text
        elif memo.get("service") is not None and device_type in chat.kept:
            service, faults, price = memo.get("service"), memo.get("faults", []), memo.get("price")
        else:
            service, faults, price = self._suggest_for(device_type, text, chat)
        if service is None:
            offer = self._fallback_offer(device_type)
            service = offer[0] if offer else None
        if price is None:
            price = self._service_price(service)
        if service is not None and service.device_type != device_type:
            service = service.model_copy(update={"device_type": device_type})
        variant, questions = self._variant_for(service, faults)
        name = self._kb.device_name_vi(device_type) or device_type
        if text and _fold_vi(text) == _fold_vi(name):
            text = ""
        return DeviceSuggestion(
            device_type=device_type,
            name_vi=name,
            source=EvidenceSource.IMAGE if image_index is not None else EvidenceSource.DESCRIPTION,
            image_index=image_index,
            confidence=round(float(memo.get("confidence", 0.0)), 4) if image_index is not None else 0.0,
            is_primary=primary,
            uncertain=bool(memo.get("uncertain")) and image_index is not None,
            suspected_faults=faults,
            service=service,
            variant_code=variant,
            questions_vi=questions,
            price_estimate=price,
            description_vi=(text[:500] or None),
            note_vi=None if service is not None or self._fallback_offer(device_type) else self._not_open_note(device_type),
            status=status,
            message_vi=message,
            urgency=urgency,
        )

    def _suggest_for(self, device_type: str, text: str, chat: Conversation):
        """What retrieval alone finds for an appliance not yet talked through.

        Only faults the words point at firmly are named, and they are marked
        as coming from the description; the model has not looked at them.
        Without such words the appliance's own repair is offered, priced on
        inspection, which is what booking it then means."""
        strong = []
        if text and self._names_a_symptom(text, device_type):
            strong = [
                c for c in self._retriever.candidate_faults(text, device_type, top_k=3)
                if c.score >= settings.DEVICE_FROM_RETRIEVAL_SCORE
            ][:2]
        if strong:
            offer = self._service_to_offer(strong, device_type, chat)
            faults = [
                SuspectedFault(
                    fault_code=c.fault.fault_code,
                    name_vi=c.fault.name_vi,
                    confidence=round(min(c.score, 1.0), 4),
                    source=EvidenceSource.DESCRIPTION,
                )
                for c in strong
            ]
            assess = any(c.fault.requires_assessment for c in strong)
            price = PriceEstimate(
                min=min(c.fault.price_min for c in strong),
                max=None if assess else max(c.fault.price_max for c in strong),
                requires_assessment=assess,
            )
            return (offer[0] if offer else None), faults, price
        offer = self._fallback_offer(device_type)
        if not offer:
            return None, [], None
        return offer[0], [], self._service_price(offer[0])

    @staticmethod
    def _service_price(service: Optional[RecommendedService]) -> Optional[PriceEstimate]:
        """The catalogue's own labour range for a service: firm for a fixed
        price, "from" for a repair priced on inspection."""
        ref = service_catalog.current().ref_for(service.service_code) if service else None
        if ref is None or not ref.base_price:
            return None
        fixed = bool(ref.variant_codes) or ref.kind != "repair"
        return PriceEstimate(
            min=ref.base_price,
            max=(ref.price_max or ref.base_price) if fixed else None,
            requires_assessment=not fixed,
        )

    def _variant_for(self, service: Optional[RecommendedService], faults) -> tuple:
        """The fixed-price variant when the faults settle it, else what to ask."""
        if service is None:
            return None, []
        questions = service_catalog.questions_for(service.service_code)
        if not questions:
            return None, []
        sets = [
            set(fault.candidate_variants)
            for f in faults
            if (fault := self._kb.fault(f.fault_code)) is not None and fault.candidate_variants
        ]
        common = set.intersection(*sets) if sets else set()
        if len(common) == 1:
            return common.pop(), []
        return None, list(dict.fromkeys(q["question_vi"] for q in questions))

    def _remember_past_jobs(self, chat: Conversation, jobs) -> None:
        """Keep the customer's earlier bookings, each matched to an appliance.

        Taken once per conversation: the backend sends the same list every turn,
        and what was matched the first time stays matched.
        """
        if chat.past_jobs or not jobs:
            return
        for job in list(jobs)[:5]:
            text = f"{job.device_vi or ''} {job.service_vi}"
            hits = device_hint.devices_named_in(text, self._kb)
            chat.past_jobs.append(
                {
                    "service": job.service_vi.strip(),
                    "date": job.date,
                    "fault": (job.fault_vi or "").strip(),
                    "device": hits[0].device_type if hits else "",
                }
            )

    def _recall(self, chat: Conversation, urgent: bool) -> Optional[str]:
        """Once per appliance: "you had this one repaired on ...".

        Nothing is concluded from it. Whether it is the same fault is for the
        technician, who gets the earlier booking in the notes; the customer is
        only told it is worth mentioning. Not while something is dangerous.
        """
        job = chat.past_job()
        if urgent or not job or chat.device_type in chat.recalled:
            return None
        chat.recalled.append(chat.device_type)
        return (
            f'Em thấy ngày {day_vi(job["date"])} anh/chị đã đặt "{job["service"]}". '
            "Nếu là lỗi cũ quay lại, anh/chị cứ kể với thợ để thợ xem lại lần sửa trước ạ."
        )

    def _display_code(self, chat: Conversation, text: str, device_type: Optional[str]):
        """The code this message reports, read against the brand's table."""
        book = error_codes.get_error_code_book()
        brand = book.brand_in(text)
        if brand:
            chat.brand = brand
        following_up = bool(chat.error_codes or chat.pending_code)
        reading = book.read(text, chat.brand, device_type, following_up)
        if reading is None and brand and chat.pending_code:
            reading = book.read(f"báo {chat.pending_code}", chat.brand, device_type)
        return reading

    def _safety_steps(self, text: str, device_type: Optional[str]) -> List[str]:
        """What to do now, from the most likely urgent fault for these words."""
        for device in ([device_type] if device_type else []) + [None]:
            for scored in self._retriever.candidate_faults(text, device, 5):
                fault = scored.fault
                if str(fault.urgency).upper().endswith("HIGH") and fault.suggested_actions_vi:
                    return list(fault.suggested_actions_vi)[:3]
        return []

    def _error_code_line(self, chat: Conversation, text: str, urgent: bool) -> Optional[str]:
        """What the code on the display means, from the brand's own table.

        Once per code. A code reported before the brand is known is held, and
        read when the customer names the brand.
        """
        reading = self._display_code(chat, text, chat.device_type or _device_named_in(text, self._kb))
        if reading is None or reading.token in chat.error_codes:
            return None
        if reading.table is None:
            if chat.pending_code == reading.token:
                return None
            chat.pending_code = reading.token
        else:
            chat.pending_code = None
            chat.error_codes.append(reading.token)
            note = error_codes.note_vi(reading)
            if note and note not in chat.code_notes:
                chat.code_notes.append(note)
        return error_codes.reply_vi(reading, urgent)

    def _framed(
        self, chat: Conversation, message: Optional[str], urgent: bool, extra: Optional[str] = None
    ) -> Optional[str]:
        """Open for the mood, close with what is waiting, speak as the customer asked.

        Templated sentences only; nothing the model wrote is changed apart from
        how the customer is addressed.
        """
        if not message:
            message = None
        opener = None
        if chat.mood == "upset":
            opener = "Dạ em xin lỗi vì sự bất tiện này ạ."
        elif chat.mood == "worried" and not urgent:
            opener = "Dạ anh/chị yên tâm, em xem giúp ngay ạ."
        # Other appliances named or photographed are answered in the same reply
        # (_answer_others), so nothing is left waiting for "xem tiếp".
        closer = None
        recall = self._recall(chat, urgent) if message else None
        parts = [p for p in (opener, message, extra, recall, closer) if p]
        if not parts:
            return message
        return dialogue_state.address_as(" ".join(parts), chat.address)

    def _take_one_appliance(self, chat: Conversation, text: str) -> str:
        """The part of the message about one appliance; the rest waits its turn.

        "Máy lạnh không mát, tủ lạnh cũng chảy nước" is two problems. Searched
        as one they matched neither well, and the answer was about whichever
        appliance the session already had. Now the first is answered, the
        second is kept with what was said about it, and "xem tiếp" brings it.
        """
        chat.just_queued = []
        chat.just_seen = []
        chat.seen = []
        lexicon = dialogue_state.get_lexicon(self._kb)
        # Read the way it was typed: "tiếppp đi", "xem tieeps", "bìnhhhh nóng lạnh".
        folded = " " + lexicon.normalize(text) + " "
        if chat.queued:
            wanted = None
            if any(f" {p} " in folded for p in _NEXT_ONE):
                wanted = next(iter(chat.queued))
            else:
                named = _strongly_named_in(lexicon.normalize_accented(text), self._kb)
                if named in chat.queued:
                    wanted = named
            if wanted:
                said = chat.queued.pop(wanted)
                if chat.device_type and chat.device_type not in chat.kept:
                    chat.kept.append(chat.device_type)
                # A new appliance starts its own diagnosis. Carried over, "the
                # customer has had an answer" made the fridge reached with
                # "xem tiếp" skip its questions and be diagnosed from nothing.
                chat.answered = False
                chat.times_asked = 0
                chat.shortlist = []
                chat.pending_question = None
                # Named in the text, so the ordinary switch takes it from here
                # and searches only what was said about this appliance.
                name = self._kb.device_name_vi(wanted) or ""
                return f"{name} {said}".strip()

        # A correction is one message about one appliance: "không phải máy lạnh
        # mà là tủ lạnh" names two and means the second. The switch handles it.
        if _corrects_an_appliance(text, self._kb) or _corrects_an_appliance(
            lexicon.normalize_accented(text), self._kb
        ):
            return text
        split = _split_by_appliance(text, self._kb)
        # Typed with stretched letters or teencode the names may only be found
        # once the words are normalised ("ống nc" is "ống nước"); cut that text
        # instead when it finds more of the appliances, not only when the
        # typed text finds none.
        normalised = _split_by_appliance(lexicon.normalize_accented(text), self._kb)
        if len({d for d, _ in normalised}) > len({d for d, _ in split}):
            split = normalised
        if split:
            devices = [d for d, _ in split]
            primary = chat.device_type if chat.device_type in devices else devices[0]
            if chat.device_type is None:
                # The cut already knows which appliance this piece is about;
                # read again on its own, "ổ cắm cắm cái quạt vào cứ lủng lẳng"
                # names two and settles on neither.
                chat.remember_device(primary, 0.0, "description")
            for device, said in split:
                if device == primary:
                    continue
                chat.queued[device] = (chat.queued.get(device, "") + " " + said).strip()
                chat.just_queued.append(device)
                chat.memo.setdefault(device, {})["text"] = chat.queued[device]
            piece = dict(split)[primary]
            if _device_named_in(piece, self._kb) != primary:
                # The cut read "cái quạt trên trần nhà" as a ceiling fan; read
                # again alone, the piece says "quạt" and becomes a desk fan.
                # Named the way the others are named in _answer_others.
                piece = f"{self._kb.device_name_vi(primary) or ''} {piece}".strip()
            return piece
        # Otherwise the old cut, at punctuation and connectors.
        segments = [s.strip() for s in _SEGMENT_RE.split(text) if s and s.strip()]
        if len(segments) < 2:
            return text
        owned: List[tuple] = []
        current = None
        for segment in segments:
            named = _strongly_named_in(lexicon.normalize_accented(segment), self._kb)
            if named:
                current = named
            owned.append((current, segment))
        devices = list(dict.fromkeys(d for d, _ in owned if d))
        if len(devices) < 2:
            return text
        primary = chat.device_type if chat.device_type in devices else devices[0]
        # Segments before the first named appliance belong to it.
        first = devices[0]
        owned = [(d or first, seg) for d, seg in owned]
        for device in devices:
            if device == primary:
                continue
            said = " ".join(seg for d, seg in owned if d == device)
            chat.queued[device] = (chat.queued.get(device, "") + " " + said).strip()
            chat.just_queued.append(device)
            chat.memo.setdefault(device, {})["text"] = chat.queued[device]
        return " ".join(seg for d, seg in owned if d == primary)

    async def _diagnose_turn(self, request: DiagnosisRequest) -> DiagnosisResponse:
        trace = _Trace(request.include_trace)
        chat = self._conversations.get_or_create(request.session_id)
        self._resume(chat, request.session_id, request.history)
        self._remember_past_jobs(chat, request.past_jobs)
        mood, address = dialogue_state.mood_of(request.description, dialogue_state.get_lexicon(self._kb))
        chat.mood = mood
        chat.address = address or chat.address
        spoken = _without_fillers(request.description)
        if spoken != request.description and spoken:
            request = request.model_copy(update={"description": spoken})
        one = self._take_one_appliance(chat, request.description)
        if one != request.description:
            request = request.model_copy(update={"description": one})
            trace.add("dialogue", True, "Tin nhắn nói về nhiều thiết bị; xem từng cái", queued=list(chat.queued))
        chat.add("customer", request.description)
        reading = self._read_turn(
            chat,
            request.description,
            # Read against the appliance in question. A part named in passing
            # ("công tắc", "phích cắm") is not a new appliance, and reading
            # "không phải công tắc đâu" against sockets ruled out a socket fault
            # while the light switch the customer meant stayed in the answer.
            (
                _device_asked_for_now(request.description, self._kb, strong=True)
                if chat.device_type
                else _device_named_in(request.description, self._kb)
            )
            or chat.device_type,
            trace,
        )
        trace.add(
            "session",
            True,
            f"Lượt thứ {sum(1 for t in chat.turns if t.role == 'customer')} của phiên này",
            session_id=chat.session_id,
            remembered_device=chat.device_type,
            asked_before=len(chat.asked_symptoms),
        )

        # A sentence with no appliance, no symptom and no photograph is not a
        # fault report. Sent through, "chiến tranh thế giới xảy ra khi nào" came
        # back as three questions about what device was broken. The gate belongs
        # here rather than in a client: Backend calls this endpoint too.
        # A conversation already about an appliance stays about it. "Giờ tôi
        # nên thuê dịch vụ nào" carries no device and no symptom of its own and
        # is entirely on topic as the third message of a thread about a washing
        # machine; judging each message alone threw that away.
        if _is_not_household(request.description):
            return self._out_of_scope_response(request, chat, trace)

        # Off the subject, in the middle of a conversation that is on it: "kể
        # chuyện cười đi", "giá vàng hôm nay". The conversation being about an
        # air conditioner made the whole thread look in scope, so the joke was
        # diagnosed as an air conditioner symptom. Refused politely, and the
        # turn is kept out of everything retrieved later, so the conversation
        # picks up where it was.
        if self._is_off_topic(request.description) and not request.images:
            chat.this_turn_had_no_symptom()
            return self._out_of_scope_response(request, chat, trace)

        if _is_greeting(request.description) and chat.device_type is None:
            return self._greeting_response(request, chat, trace)

        in_scope = (
            bool(request.images)
            or chat.device_type is not None
            # Someone asking to book is in the trade by definition, whatever
            # else the sentence contains. "Cho mình đặt lịch" and "đặt luôn đi"
            # carry no appliance and no symptom, so the trade check refused them
            # as off-topic — a customer saying plainly that they want to book,
            # told the question was out of scope.
            or _wants_to_book(request.description)
            or self._is_in_the_trade(chat.customer_text())
        )
        if not in_scope:
            return self._out_of_scope_response(request, chat, trace)

        # Someone asking to book has stopped describing and started buying.
        # "Bây giờ anh muốn đặt lịch vệ sinh máy lạnh" came back as a diagnosis
        # — two possible faults, a price range, and a list of things to try
        # first — to a customer who had asked for none of it.
        if _wants_to_book(request.description) and not request.images:
            booking = self._booking_response(request, chat, trace)
            if booking is not None:
                return booking

        detection = await self._detect_images(request.images, request.description, chat)
        trace.add(
            "detector",
            detection is not None,
            (
                f"Nhận ra {detection.device_type} ({detection.confidence:.0%})"
                if detection
                else ("Không có ảnh" if not request.images else "Không nhận ra thiết bị nào")
            ),
            images=len(request.images),
            device=detection.device_type if detection else None,
            confidence=round(detection.confidence, 4) if detection else None,
            box=list(detection.box_xywh) if detection else None,
            seen=[{"image": i, "device": d, "confidence": round(c, 4)} for i, d, c in chat.seen],
            checked=detection.checked if detection else None,
            detector_said=detection.first_reading if detection else None,
        )
        detected = detection.device_type if detection else None

        # A follow-up carries no photograph, because nobody sends the same one
        # twice. Without the remembered device the answer to the question we
        # just asked arrives about no appliance in particular.
        if detected is None and chat.device_type:
            detected = chat.device_type

        # If the last turn asked which of two look-alike appliances this is,
        # this message may be the answer. Reading it before anything else means
        # "không" settles the device instead of being one more symptom.
        if chat.awaiting_confusion_about:
            settled = device_hint.resolve_confusion_answer(
                request.description, chat.awaiting_confusion_about, self._kb
            )
            if settled:
                detected = settled
                # Still "image". The photograph established it and the answer
                # only chose between the two appliances that photograph could
                # not separate, so this is better evidence than the detection
                # alone, not worse. Recording it as coming from the description
                # made _resolve_device stop reporting the device at all, and
                # the turn that finally knew the appliance was the one that
                # claimed not to.
                chat.remember_device(settled, chat.device_confidence, "image")
            # Cleared either way. An answer that settles nothing — "em không rõ
            # lắm" — has still been given, and putting the same question a
            # second time is how a support bot proves it is a form. Carry on
            # with the detector's own guess and say so through confidence.
            chat.awaiting_confusion_about = None
            chat.confusion_resolved = True

        # The photograph is ambiguous between a microwave and an oven; a
        # sentence saying "lò vi sóng" is not. Believe the words.
        if detection is None and chat.device_type and detected == chat.device_type:
            # Remembered, not seen: the words of a follow-up decide only when
            # they name another machine outright (see _DEVICE_HEADS). Letting
            # resolve() believe any mention here undid a correction one turn
            # later - "bấm công tắc không lên đèn" moved a conversation the
            # customer had just set to the light back onto sockets.
            device_type = detected
        else:
            device_type, _hint = device_hint.resolve(
                request.description, detected, self._kb
            )
            if device_type is None:
                # "điuề hoà", "máy lạnhhh": read the way the lexicon reads the
                # rest of the message before deciding no appliance was named.
                device_type, _hint = device_hint.resolve(
                    dialogue_state.get_lexicon(self._kb).normalize_accented(request.description),
                    detected,
                    self._kb,
                )
            if device_type is None:
                # "Em đang đứng ngoài cửa không vào nhà được" names no appliance
                # and describes exactly one: a smart lock.
                device_type = self._device_from_symptom(request.description)

        # A change of mind is not always phrased as an order. "Em nhầm rồi, là
        # tủ lạnh" and "bỏ máy lạnh đi, đặt tủ lạnh" carry no booking verb, so
        # they arrive here rather than on the booking path, and until this was
        # added the appliance they replaced stayed in place: measured on the
        # running service, fourteen of sixteen switch phrasings came back with
        # the air conditioning they were moving away from. The unit tests
        # passed throughout, because the understanding was never the problem -
        # only half the routes consulted it.
        switched_to = _device_asked_for_now(request.description, self._kb, strong=True)
        changed_appliance = bool(
            switched_to and chat.device_type and switched_to != chat.device_type
        )
        if switched_to and not chat.device_type and detection is None:
            # Nothing settled yet, and the sentence is a correction: "không phải
            # điều hoà mà là ổ cắm" names both, and the one asked for is the
            # second, not the longer name resolve() would pick.
            device_type = switched_to

        if detection is not None:
            chat.remember_device(detection.device_type, detection.confidence, "image")
        elif changed_appliance and switched_to:
            # Ahead of the photograph guard below, because a customer who names
            # a different appliance in words has said something the photograph
            # cannot contradict: the picture was of the old one.
            chat.remember_device(switched_to, 0.0, "description")
            device_type = switched_to
            trace.add("device", True, f"Khách đổi sang {switched_to}", device=switched_to)
        elif device_type and chat.device_source_vi != "image":
            # Only when nothing better is already known. Without the guard this
            # overwrote the appliance a photograph had established — including
            # the one the customer had just confirmed by answering the either/or
            # — and _resolve_device then stopped reporting a device at all.
            chat.remember_device(device_type, 0.0, "description")

        # Symptoms arrive one message at a time: "máy không mát", then later "à
        # mà nó còn kêu to nữa". Retrieved on its own the second is three words
        # with no subject, so the retriever sees everything said so far - minus
        # the turns that were answered by asking which appliance it was, which
        # carry no symptom and do measurable harm when joined in.
        #
        # Unless the appliance just changed. Then the accumulated symptoms
        # belong to the machine being abandoned, and searching for them under
        # the new one finds nothing: "máy lạnh không mát" retrieved against a
        # toilet matched no fault at all, and the answer fell back to a generic
        # inspection. Symptoms accumulate per appliance, not per conversation.
        # The cleaned text throughout: what the customer ruled out or said is
        # absent is not searched for, and the faults they excluded are not
        # offered back to them. See dialogue_state.py.
        searched = (
            (reading.retrieval_text or request.description)
            if changed_appliance
            else chat.symptom_text()
        )
        candidates = self._retriever.candidate_faults(
            description=searched,
            device_type=device_type,
            top_k=settings.VLM_SHORTLIST_SIZE,
            exclude=chat.state.excluded_codes(),
            penalties=chat.state.factors(),
        )
        trace.add(
            "retrieval",
            bool(candidates),
            (
                f"RAG rút {len(candidates)} bệnh khả nghi cho {device_type or 'thiết bị chưa rõ'}"
                if candidates
                else "RAG không tìm được bệnh nào khớp mô tả"
            ),
            device=device_type,
            searched_text=chat.customer_text(),
            candidates=[
                {"code": c.fault.fault_code, "score": round(c.score, 4)}
                for c in candidates
            ],
        )
        # The shortlist may span several appliances when the device is not
        # known, and the model will happily pick from across it. Retrieval's
        # own top match used to be adopted as the appliance to stop that, and
        # that guess is gone: weighting by word rarity normalises against the
        # question's own weight, so a message of common words scores 1.00
        # against whichever fault happens to use them. "Nhà em nó kêu to lắm
        # không chạy" adopted an air conditioner and answered "hỏng máy nén"
        # to someone who never said what the machine was.
        #
        # What replaces it is below: with no appliance, ask which one. The
        # case the guess was written for — a gas stove the detector missed,
        # described as "bật không lên lửa" — is now recognised by name, as is
        # every other diagnosis case in the suite.

        # One place decides what the model may know, and it is not this loop.
        # See context.py: the device and how it was learned, everything said so
        # far, what has already been asked, the shortlist with the phrases
        # customers use, the policies that bear on this device and the rows that
        # price it. Handing over a bare list of codes is what made the answers
        # read like a lookup table.
        ctx = context.build(
            kb=self._kb,
            retriever=self._retriever,
            chat=chat,
            latest_message=request.description,
            device_type=device_type,
            device_source=chat.device_source_vi,
            candidates=candidates,
            has_image=detection is not None,
        )
        trace.add(
            "context",
            True,
            f"Nhồi ngữ cảnh: {len(ctx.candidates)} bệnh, {len(ctx.price_rows)} dòng giá, "
            f"{len(ctx.policies)} chính sách, {len(ctx.history)} lượt hội thoại",
            device=ctx.device_type,
            asked_before=len(ctx.already_asked),
        )

        verdict = await self._vlm.assess_context(
            crop=detection.crop if detection else None,
            context=ctx,
            candidate_condition_codes=[
                (code, self._kb.condition_name_vi(code) or code)
                for code in self._kb.condition_codes
            ],
        )

        trace.add(
            "vlm",
            bool(verdict.fault_codes),
            (
                f"Qwen chọn {', '.join(verdict.fault_codes)} ({verdict.confidence:.0%})"
                if verdict.fault_codes
                else "Qwen không chọn được mã nào trong danh sách"
            ),
            had_image=detection is not None,
            chose=verdict.fault_codes,
            conditions=verdict.condition_codes,
            confidence=round(verdict.confidence, 4),
            reason=verdict.reasoning_vi,
        )

        # A photograph sent with "đây là cái gì" is a question about the
        # appliance, not a report that it is broken. Answer it and ask the one
        # question that follows naturally, rather than interrogating someone
        # about symptoms they never mentioned.
        if (
            detection is not None
            and _is_identification(chat.customer_text())
            and not chat.answered
        ):
            return self._identification_response(request, detection, chat, trace)

        confidence = self._combine_confidence(detection, verdict.confidence)
        shortlist = [c.fault for c in candidates]

        # Ask which of two look-alike appliances this is before committing to a
        # diagnosis, even when confidence is high — especially then. The
        # dangerous case is the detector being sure and wrong: an oven came back
        # as a microwave at 0.84, and a confident "Lò vi sóng, hỏng sò cao tần,
        # 600.000đ" about someone's oven is worse than one more turn. Asked once
        # per conversation, and never when the customer has already said.
        if (
            detection is not None
            and chat.awaiting_confusion_about is None
            and not chat.confusion_resolved
            and self._kb.confusable_with(detection.device_type)
            and not device_hint.devices_named_in(chat.customer_text(), self._kb)
        ):
            return await self._clarification_response(
                request, confidence, shortlist, detection, chat, trace
            )

        # A description that names the problem outright does not need a
        # question. "Máy nước nóng không nóng" matched one fault at 1.00 and
        # still came back as three questions, because the decision looked only
        # at the model's confidence. Retrieval being certain is evidence too,
        # and here it is the better evidence: it matched the customer's own
        # words against symptoms the team wrote.
        said = self._retriever.content_words(chat.device_text())
        # "lavabo bị tắc", "ổ cắm không lên": two words, the appliance and one
        # symptom, and one fault far ahead of the rest. That is a complete
        # report; asking "bắt đầu từ khi nào?" back was the assistant not
        # listening. A tie ("tivi bị đơ" fits three faults equally) still asks.
        clear_lead = (
            device_type is not None
            and self._names_a_symptom(chat.device_text(), device_type)
            and bool(candidates)
            and candidates[0].score >= settings.RETRIEVAL_DECISIVE_SCORE
            and (len(candidates) == 1 or candidates[0].score - candidates[1].score >= _CLEAR_LEAD)
        )
        # "máy lạnh hư rồi" is three words and says nothing about what is wrong;
        # it was answered with a remote-control battery.
        names_something = device_type is None or self._names_a_symptom(chat.device_text(), device_type)
        enough_said = (said >= settings.DECISIVE_MIN_WORDS and names_something) or (
            said == settings.DECISIVE_MIN_WORDS - 1 and clear_lead
        )
        decisive = (
            bool(candidates)
            # Never without knowing the appliance. Retrieval then searches all
            # seventeen at once, and "cái này bị sọc" — a photograph of a
            # television the detector had missed — scored a broken fan motor
            # highly enough to be answered as settled.
            and device_type is not None
            and candidates[0].score >= settings.RETRIEVAL_DECISIVE_SCORE
            # And the customer actually described something. The score divides
            # by the query's own length, so "hư rồi" matches a symptom
            # perfectly and scores 1.00 while saying nothing at all.
            and enough_said
        )

        # Too little was said for anyone to answer, the model included. The
        # same word count already guarded `decisive`, but `decisive` is only
        # the path taken when the model is unsure — nothing stopped a confident
        # one. A live run answered "hư rồi" with a refrigerator compressor,
        # "cứu em với" with a tap cartridge, and "sửa giúp em cái này" with a
        # damaged fan cord: three messages that name no appliance, describe no
        # symptom, and between them carry four content words.
        #
        # Only when nothing else is known. A photograph or an earlier message
        # settles the appliance, and then "nó không chạy" is a complete thing to
        # say about it.
        if device_type is None or not enough_said:
            return await self._clarification_response(
                request, confidence, shortlist, detection, chat, trace
            )

        if confidence < settings.AI_CONFIDENCE_THRESHOLD and not decisive:
            return await self._clarification_response(
                request, confidence, shortlist, detection, chat, trace
            )

        if decisive and not verdict.fault_codes:
            # Retrieval is sure and the model would not choose. Answer from
            # retrieval rather than asking: the customer has already said the
            # thing that settles it.
            verdict = VlmVerdict(
                fault_codes=[c.fault.fault_code for c in candidates[:2]],
                confidence=max(confidence, candidates[0].score * 0.7),
            )
            confidence = verdict.confidence
            if trace is not None:
                trace.add(
                    "fallback", True,
                    f"RAG chắc chắn ({candidates[0].score:.2f}), trả lời thẳng thay vì hỏi",
                    faults=verdict.fault_codes,
                )

        return await self._build_response(
            request, detection, verdict, confidence, shortlist, chat, trace
        )

    async def answer(self, request: ChatRequest) -> ChatResponse:
        """Advisory Q&A, grounded in retrieved policy passages.

        Kept separate from diagnosis: it may discuss maintenance intervals and
        platform policy, but it never recommends a service or a booking.
        """
        if visit_prep.asks_how_to_prepare(request.question):
            async with self._conversations.lock(request.session_id):
                chat = self._conversations.get_or_create(request.session_id)
                chat.add("customer", request.question)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=chat.session_id,
                    status=AnswerStatus.OK,
                    answer_vi=dialogue_state.address_as(self._visit_prep_text(chat, request.question), chat.address),
                    confidence=0.9,
                    disclaimer_vi=settings.AI_DISCLAIMER_VI,
                )
        known = self._conversations.peek(request.session_id) if request.session_id else None
        if known is not None and known.parent_id is None and known.others:
            # A question goes to the appliance it is about, like a description
            # does. fixhome.sbs, 25/10/2026: "cái đó sửa hết bao nhiêu tiền"
            # right after the fridge was answered with the air conditioner's
            # prices, because the web sends questions here and only the
            # diagnosis route knew about the other appliances.
            target = self._other_device_asked(known, request.question)
            priced = self._price_answer(known, target or known.device_type, request)
            if priced is not None:
                return priced
            if target in known.others:
                sub_id = known.others[target]
                async with self._conversations.lock(sub_id):
                    reply = await self._answer_locked(request.model_copy(update={"session_id": sub_id}))
                known.memo.setdefault("", {})["lead"] = target
                return reply.model_copy(update={"session_id": known.session_id})
        async with self._conversations.lock(request.session_id):
            response = await self._answer_locked(request)
        if known is not None and known.parent_id is None and known.others:
            known.memo.setdefault("", {})["lead"] = known.device_type
        return response

    def _price_answer(
        self, chat: Conversation, device_type: Optional[str], request: ChatRequest
    ) -> Optional[ChatResponse]:
        """"Cái đó sửa hết bao nhiêu" about an appliance of the visit already priced.

        The price was worked out when it was diagnosed; asked again, it is said
        again, with what it was for. Left to the model, on fixhome.sbs
        25/10/2026, the answer named the faults and no figure at all.
        """
        if not device_type or not _asks_about_money(request.question):
            return None
        if self._names_a_symptom(request.question, device_type):
            return None  # a new complaint as well: diagnose it, do not repeat
        reply = chat.memo.get(device_type, {}).get("reply")
        finding = self._plain_finding(reply) if reply is not None else None
        if not finding or not (reply.price_estimate and reply.price_estimate.min):
            return None
        name = (self._kb.device_name_vi(device_type) or device_type).lower()
        chat.memo.setdefault("", {})["lead"] = device_type
        answer = f"Dạ, với {name} nhà mình, {finding[:1].lower()}{finding[1:]}"
        if "báo giá" not in answer:
            answer += " Thợ xem tận nơi rồi mới báo giá chính xác ạ."
        return ChatResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=AnswerStatus.OK,
            answer_vi=dialogue_state.address_as(answer, chat.address),
            recommended_services=list(reply.recommended_services[:1]),
            confidence=0.8,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _answer_locked(self, request: ChatRequest) -> ChatResponse:
        chat = self._conversations.get_or_create(request.session_id)
        self._resume(chat, request.session_id, request.history)
        self._remember_past_jobs(chat, request.past_jobs)
        mood, address = dialogue_state.mood_of(request.question, dialogue_state.get_lexicon(self._kb))
        chat.mood = mood
        chat.address = address or chat.address
        chat.just_queued = []
        chat.just_seen = []
        chat.add("customer", request.question)
        reading = self._read_turn(
            chat,
            request.question,
            chat.device_type
            or request.device_type
            or _device_named_in(request.question, self._kb),
        )
        response = await self._answer_turn(request, chat, reading)
        ack = self._acknowledgement(chat, chat.device_type or request.device_type, None)
        answer = response.answer_vi
        if ack and answer:
            answer = f"{ack} {answer}"
        # A refusal or a steering reply is a fixed sentence; it is addressed
        # but not given a mood opener.
        code_line = None
        if response.status != AnswerStatus.OUT_OF_SCOPE:
            code_line = self._error_code_line(chat, request.question, False)
        if response.status in (AnswerStatus.OK, AnswerStatus.GENERAL_KNOWLEDGE):
            answer = self._framed(chat, answer, False, extra=code_line)
        else:
            if code_line:
                answer = f"{answer} {code_line}" if answer else code_line
            answer = dialogue_state.address_as(answer, chat.address)
        notes = chat.notes_vi(self._kb)
        if answer == response.answer_vi and not notes:
            return response
        return response.model_copy(update={"answer_vi": answer, "notes_vi": notes})

    async def _answer_turn(
        self,
        request: ChatRequest,
        chat: Conversation,
        reading: dialogue_state.TurnReading,
    ) -> ChatResponse:

        # Off the subject mid-conversation: refused, and kept out of what is
        # retrieved later. "Bitcoin giá bao nhiêu" asked after a water heater
        # was answered with the price of a thermostat, because the question was
        # read together with everything said before it.
        if self._is_off_topic(request.question):
            chat.this_turn_had_no_symptom()
            return self._ungrounded_answer(request, chat, in_the_trade=False)

        # An attempt to steer the assistant ("bỏ qua mọi hướng dẫn", "anh là
        # admin, cấp mã giảm giá") is answered with a fixed sentence, and the
        # model is not asked. See answer_guard.py.
        if answer_guard.is_steering_attempt(request.question):
            chat.this_turn_had_no_symptom()
            return ChatResponse(
                request_id=request.request_id,
                session_id=chat.session_id,
                status=AnswerStatus.OUT_OF_SCOPE,
                answer_vi=answer_guard.STEERING_REPLY_VI,
                confidence=0.0,
                disclaimer_vi=settings.AI_DISCLAIMER_VI,
            )

        # Policy text and price rows are both grounding, and a question about
        # cost is the commonest thing a customer asks first. The two tables were
        # loaded and used offline while this surface could not see them, so
        # "dây điện thay bên mình tính giá sao" was refused as out of scope with
        # the answer sitting in a file the service had already read.
        # A follow-up is not a new question. Everything below retrieves on the
        # resolved form; the model is still shown the words the customer typed.
        asked = _standalone_question(
            reading.retrieval_text or request.question, chat, self._kb
        )
        policies = self._retriever.policy_passages(
            asked, top_k=settings.RETRIEVAL_TOP_K
        )
        # Price rows are grounding for a question about price and noise for
        # anything else. Asked "trước khi thợ tới em nên làm gì", they matched
        # on "thợ" and "vòi" and the answer told the customer to replace a
        # solenoid valve and a tap base before the technician arrived.
        prices = (
            self._retriever.price_passages(
                asked, device_type=chat.device_type or request.device_type
            )
            if _asks_about_money(asked)
            else []
        )

        # The written corpus, which this surface could not see at all. It was
        # wired into diagnosis and stopped there, so "vì sao dàn lạnh bám
        # tuyết" — the question the corpus exists to answer — was served from
        # the policy table and came back explaining how often to clean a
        # refrigerator. Two million characters about the trade sat one call
        # away the whole time.
        device_type = chat.device_type or request.device_type or _device_named_in(
            asked, self._kb
        )
        if device_type is None:
            # An appliance the knowledge base does not cover, that Backend
            # sells a service for: say so and offer it (see _catalog_offer).
            offered = self._catalog_offer(chat.customer_text())
            if offered is not None:
                message, service = offered
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=chat.session_id,
                    status=AnswerStatus.NO_GROUNDING,
                    answer_vi=message,
                    recommended_services=[service],
                    confidence=0.0,
                    disclaimer_vi=settings.AI_DISCLAIMER_VI,
                )
        # Faults are ranked on everything the customer has said is happening,
        # not on the question alone: "vậy giờ là bị gì" names no symptom, and
        # the answer to it is the fault the earlier turns point to once the
        # ruled-out ones are taken away.
        customer_turns = sum(1 for t in chat.turns if t.role == "customer")
        candidates = (
            self._retriever.candidate_faults(
                chat.symptom_text() if customer_turns > 1 else asked,
                device_type,
                exclude=chat.state.excluded_codes(),
                penalties=chat.state.factors(),
            )
            if device_type
            else []
        )
        codes = [c.fault.fault_code for c in candidates]
        # A dangerous fault has to warn here too. Someone typing "bếp nhà em có
        # mùi gas" into the question box is in the same room as someone who
        # sent a photograph of it, and the instruction to shut the cylinder
        # valve cannot depend on which surface they happened to use.
        # Only when the dangerous fault is the *best* match, not merely among
        # the three. "Vệ sinh máy lạnh bao lâu một lần" shortlists a dirty
        # filter first and a burnt smell third, and pinning on the third turned
        # a question about cleaning intervals into a safety warning — and a
        # prompt long enough to run past the model's time budget, so the
        # customer got an error instead of an answer.
        safety = self._retriever.safety_passages(codes[:1])
        pinned = [f"{s.chunk.source_file}::{s.chunk.heading_vi}" for s in safety]
        corpus = self._retriever.corpus_passages(
            asked,
            device_type=device_type,
            fault_codes=codes,
            exclude=pinned,
            ruled_out=chat.state.excluded_codes(),
        )

        # Order by what was asked. Asked "vệ sinh máy lạnh giá bao nhiêu" with
        # policy text first, the model answered with the cleaning interval —
        # true, retrieved, and not the question. The model reads the passages
        # in order and the first relevant one wins.
        #
        # The warning goes first whatever was asked, then the price if money
        # was the question, then the trade documents, then policy.
        # The five business documents. They were written for exactly these
        # questions and the retriever had a method for them, which this path
        # never called: "bảo hành bao lâu" reached only the one-line policy row,
        # which does not say how long, so the model declined and the customer
        # was told the question was out of scope.
        business = (
            self._retriever.business_passages(asked)
            if _asks_about_the_business(asked) or not codes
            else []
        )

        # Whichever the customer actually asked about goes first. The model
        # reads the passages in order and the first relevant one wins, so
        # "bảo hành máy lạnh bao lâu" answered from the air conditioner's fault
        # documents — which are about the fault and say nothing about warranty.
        written = (
            business + corpus
            if _asks_about_the_business(asked)
            else corpus + business
        )
        chunks = safety + written
        passages = prices + policies
        if not (passages or chunks):
            return await self._reasoned_answer(request, chat)

        # The warning travels apart from the documents, because it is not one.
        # Mixed in as "[1]" it was read as reference material and summarised
        # away: a live gas-leak question came back as "Khó hiểu rõ ràng."
        passages_vi = (
            [p.policy.content_vi for p in prices]
            + [s.chunk.as_passage_vi() for s in corpus]
            + [s.chunk.as_passage_vi() for s in business]
            + [p.policy.content_vi for p in policies]
        )
        answer_vi, confidence = await self._vlm.answer(
            question=request.question,
            passages_vi=passages_vi,
            history_vi=_recent_dialogue(chat, self._kb),
            safety_vi="\n\n".join(s.chunk.as_passage_vi() for s in safety) or None,
        )
        if not answer_vi:
            return await self._reasoned_answer(request, chat)
        broken = answer_guard.violations(
            answer_vi,
            "\n".join(passages_vi + [s.chunk.as_passage_vi() for s in safety]),
        ) + answer_guard.ruled_out_named(answer_vi, self._ruled_out_names(chat))
        if broken:
            # Said something only the business may say, or recited its notes.
            # Discarded, not edited; the answer is written from the facts.
            logger.warning("Grounded answer discarded: %s", "; ".join(broken))
            composed = self._composed_answer(codes, device_type, chat)
            if composed is None:
                return self._ungrounded_answer(request, chat)
            answer_vi, confidence = composed, 0.5

        chat.add("assistant", answer_vi)
        return ChatResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=AnswerStatus.OK,
            answer_vi=answer_vi,
            recommended_services=self._services_for_answer(codes, device_type, chat),
            # Only what the answer could have come from. Sending ten candidate
            # rows and citing all ten put three refrigerator boards under an
            # answer about a gas stove igniter: the figure was right and the
            # sources read as though it had been made up.
            citations=(
                [
                    Citation(
                        doc_id=s.chunk.doc_id,
                        title_vi=s.chunk.heading_vi,
                        score=round(min(s.score, 1.0), 4),
                    )
                    for s in chunks[:2]
                ]
                + [
                    Citation(
                        doc_id=p.policy.doc_id,
                        title_vi=p.policy.title_vi,
                        score=round(min(p.score, 1.0), 4),
                    )
                    for p in passages[:2]
                ]
            )[:3],
            confidence=confidence,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _composed_answer(
        self, codes: List[str], device_type: Optional[str], chat: Conversation
    ) -> Optional[str]:
        """An answer written from the facts alone, for when the model's is unusable.

        Plain and short: what the conversation points to, and what to book. It
        repeats nothing the customer ruled out, because the shortlist it is
        built from already left those out.
        """
        names = []
        for code in codes[:2]:
            fault = self._kb.fault(code)
            if fault is not None and code not in chat.state.excluded:
                names.append(fault.name_vi.lower())
        if not names:
            return None
        services = self._services_for_answer(codes, device_type, chat)
        text = "Dạ với những gì anh/chị kể, khả năng cao là " + " hoặc ".join(names) + "."
        if services:
            text += f' Anh/chị đặt dịch vụ "{services[0].name_vi}" để thợ kiểm tra tận nơi giúp em ạ.'
        else:
            text += " Thợ xem tận nơi sẽ chốt được chính xác ạ."
        return text

    def _ruled_out_names(self, chat: Optional[Conversation]) -> List[str]:
        """Names of the faults the customer has ruled out, for the guard."""
        if chat is None:
            return []
        names = []
        for code in chat.state.excluded:
            fault = self._kb.fault(code)
            if fault is not None:
                names.append(fault.name_vi)
        return names

    async def _reasoned_answer(
        self, request: ChatRequest, chat: Conversation
    ) -> ChatResponse:
        """Nothing retrieved. Let the model answer from the trade, or decline.

        Refusing everything outside the tables made the assistant useless past
        its own catalogue: someone asking why an evaporator ices up got the same
        sentence as someone asking about the weather, and every customer got the
        same sentence as every other.

        The model may explain, diagnose tentatively and say what to do before a
        technician arrives. It may not put a number on anything, quote a
        warranty term, or state a fault as settled — those belong to the tables
        and to the person who turns up, and a customer holds the business to
        whatever they were told. The client drops any answer containing money
        even when the instruction said not to, because an instruction is not a
        guarantee.
        """
        # The model was told to answer NGOAI_PHAM_VI outside the trade and does
        # not reliably: asked "bitcoin giá bao nhiêu" it explained cryptocurrency
        # exchanges. An instruction is not a gate, so the gate is here, and it
        # fails closed — a question with no device and no repair word in it is
        # refused without the model being asked at all.
        if not self._is_in_the_trade(request.question):
            offer = self._catalog_offer(chat.customer_text() if chat else request.question)
            if offer is not None:
                message, service = offer
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=chat.session_id if chat else None,
                    status=AnswerStatus.NO_GROUNDING,
                    answer_vi=message,
                    recommended_services=[service],
                    confidence=0.0,
                    disclaimer_vi=settings.AI_DISCLAIMER_VI,
                )
            return self._ungrounded_answer(request, chat, in_the_trade=False)

        answer_vi = await self._vlm.answer_generally(
            request.question, history_vi=chat.customer_text()
        )
        if not answer_vi:
            return self._ungrounded_answer(request, chat)
        broken = answer_guard.violations(answer_vi) + answer_guard.ruled_out_named(
            answer_vi, self._ruled_out_names(chat)
        )
        if broken:
            logger.warning("General answer discarded: %s", "; ".join(broken))
            return self._ungrounded_answer(request, chat)

        chat.add("assistant", answer_vi)
        device_type = chat.device_type or _device_named_in(request.question, self._kb)
        return ChatResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            # Not OK: there are no citations behind this, and a caller that
            # treats a cited answer and an uncited one alike has lost the
            # distinction the citations exist for.
            status=AnswerStatus.GENERAL_KNOWLEDGE,
            answer_vi=answer_vi,
            # Nothing was retrieved, so there is no shortlist to name a service
            # from — but the appliance is known and it is broken enough to ask
            # about, and its repair is booked on inspection anyway.
            recommended_services=self._fallback_offer(device_type),
            confidence=0.4,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _narrate(
        self,
        device: Optional[DetectedDevice],
        faults: List[SuspectedFault],
        price_min: Optional[int],
        price_max: Optional[int],
        actions: List[str],
        services: List[RecommendedService],
        ruled_out: Sequence[str] = (),
    ) -> Optional[str]:
        """Hand the finished answer to the model to phrase, nothing more.

        Every fact is decided before this runs and none of it may change. The
        client checks that no number appeared which was not supplied, and an
        answer that grew one is discarded rather than corrected.
        """
        money = lambda v: f"{v:,}".replace(",", ".")  # noqa: E731
        lines = []
        # Short data, not sentences. Labels written as sentences were sent back
        # word for word by the served model ("Có thể hỏng: ... Chi phí tham
        # khảo: ..."), and labels in the old register were copied into the
        # answer ("Việc khách nên làm ngay" as "khách", "ngay lập tức").
        if device:
            lines.append(f"- máy: {device.name_vi.lower()}")
        lines.append("- lỗi: " + " | ".join(f.name_vi.lower() for f in faults))
        if price_min is not None and price_max is not None and price_max != price_min:
            lines.append(f"- giá: {money(price_min)}đ - {money(price_max)}đ")
        elif price_min is not None and price_max == price_min:
            lines.append(f"- giá: {money(price_min)}đ")
        elif price_min is not None:
            lines.append(f"- giá: từ {money(price_min)}đ, thợ xem tận nơi rồi báo giá")
        if actions:
            lines.append("- làm trước: " + " | ".join(a.rstrip(".").lower() for a in actions))
        if services:
            lines.append("- dịch vụ: " + " | ".join(s.name_vi for s in services))

        allowed = [
            str(v) for v in (price_min, price_max) if v is not None
        ] + [money(v) for v in (price_min, price_max) if v is not None]
        try:
            narrated = await self._vlm.narrate("\n".join(lines), allowed) or None
        except Exception:  # pragma: no cover - narration is never load-bearing
            logger.warning("narration_failed")
            return None
        broken = answer_guard.violations(narrated or "", "\n".join(lines)) + answer_guard.ruled_out_named(
            narrated or "", list(ruled_out)
        )
        if broken:
            logger.warning("Narration discarded: %s", "; ".join(broken))
            return None
        return narrated

    def _identification_response(
        self,
        request: DiagnosisRequest,
        detection: Detection,
        chat: Conversation,
        trace: "_Trace",
    ) -> DiagnosisResponse:
        """Name the appliance, then ask the only question that follows."""
        name = self._kb.device_name_vi(detection.device_type) or detection.device_type
        question = f"Dạ nhà mình đang gặp vấn đề gì với {name.lower()} ạ?"
        chat.remember_questions([question])
        chat.add("assistant", question)
        trace.add("scope", True, f"Khách hỏi đây là thiết bị gì — trả lời {name}")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(detection, chat),
            confidence=round(detection.confidence, 4),
            is_low_confidence=False,
            clarification=Clarification(
                questions_vi=[question],
                service_group_codes=self._kb.all_service_groups(),
            ),
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _booking_response(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace"
    ) -> Optional[DiagnosisResponse]:
        """Hand over the service, not a diagnosis.

        Returns None when the appliance is still unknown, because "cho mình
        đặt lịch" on its own does not say what to book and the ordinary path
        already asks that well.
        """
        # This turn first, because a customer who says "đổi sang thợ điện
        # nước" has changed the subject and the pinned booking has to follow
        # them. The session's appliance is the fallback, not the authority:
        # holding on to it meant every way of asking to switch came back with
        # the service they were trying to move away from.
        changed_to = _device_asked_for_now(request.description, self._kb)
        device_type = (
            changed_to
            or chat.device_type
            or _device_named_in(chat.customer_text(), self._kb)
        )
        if device_type is None:
            return self._booking_needs_the_appliance(request, chat, trace)

        if changed_to and changed_to != chat.device_type:
            # Remembered, or the next bare follow-up would snap back to the
            # appliance they had just replaced.
            chat.remember_device(changed_to, 0.0, "description")
            trace.add(
                "device",
                True,
                f"Khách đổi sang {changed_to}",
                device=changed_to,
            )

        # Which service, from the faults that fit what they have said. A
        # cleaning and a repair are different services at different prices, and
        # "đặt lịch vệ sinh máy lạnh" names the cheaper one outright.
        #
        # After a switch, only this turn. The accumulated symptoms belong to
        # the appliance being abandoned, and searching for them under the new
        # one matches nothing in particular: "máy lạnh không mát" against a
        # water pipe found no fault worth the name, and which service came back
        # then depended on how ties broke - so the same sentence gave a pipe
        # repair on one machine and a generic inspection on another, and CI and
        # a developer's laptop disagreed about it.
        candidates = self._retriever.candidate_faults(
            request.description if changed_to else chat.symptom_text(),
            device_type,
            top_k=settings.VLM_SHORTLIST_SIZE,
            exclude=chat.state.excluded_codes(),
            penalties=chat.state.factors(),
        )
        services: List[RecommendedService] = []
        # The catalogue's own price, kept beside the service it belongs to. The
        # fault's floor is a number from our labour table and named 100.000đ
        # under "Sửa tủ lạnh" — a different row from the one being booked.
        base: Optional[int] = None
        # A service the customer has in effect already had goes last, not first:
        # booking a cleaning straight after "mới vệ sinh rồi" is the repeat the
        # customer complained about, in the one place they act on it.
        spent = self._spent_services(chat)
        if spent:
            candidates = sorted(
                candidates,
                key=lambda c: all(
                    ref.service_code in spent
                    for ref in self._kb.services_for_fault(c.fault.fault_code)
                )
                and bool(self._kb.services_for_fault(c.fault.fault_code)),
            )
        for scored in candidates:
            # Only what Backend sells. Before catalogue V2 a fault with no
            # service fell back to its labour row's code, which Backend never
            # knew; now an empty list means the service is not open yet.
            refs = self._kb.services_for_fault(scored.fault.fault_code)
            for ref in refs:
                if all(s.service_code != ref.service_code for s in services):
                    if not services:
                        base = ref.base_price or scored.fault.price_min
                    services.append(
                        RecommendedService(
                            service_code=ref.service_code, name_vi=ref.name_vi
                        )
                    )
        if not services:
            # Booking intent with an appliance and no symptom, which is the
            # commonest way a customer asks: "cho em một bạn thợ tới xem máy
            # giặt" names the machine and describes nothing. Retrieval finds no
            # fault, so there was no service and the turn fell through to a
            # clarification with nothing to press — the one outcome this whole
            # path exists to prevent. The appliance alone is enough: derive the
            # service from its own faults instead of from symptoms it has none
            # of. "Đặt thợ sửa máy giặt" only ever worked because "sửa" happens
            # to appear in the symptom lists.
            services = self._services_for_device(device_type)
        if not services:
            services = self._fallback_offer(device_type)
        if not services:
            return self._not_open_response(request, chat, trace, device_type)

        name = self._kb.device_name_vi(device_type) or device_type
        price = (
            " Giá dịch vụ từ {:,.0f}đ.".format(base).replace(",", ".")
            if base
            else ""
        )
        message = (
            f"Dạ vâng ạ, bên em nhận đặt dịch vụ {services[0].name_vi} "
            f"cho {name.lower()}.{price} Anh/chị bấm Đặt thợ ngay giúp em, "
            "thợ FixHome sẽ gọi xác nhận giờ và sang tận nơi ạ."
        )
        chat.add("assistant", message)
        trace.add(
            "scope",
            True,
            f"Khách muốn đặt lịch — đưa thẳng dịch vụ {services[0].service_code}",
        )
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.OK,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(None, chat),
            recommended_services=services[:1],
            message_vi=message,
            confidence=0.0,
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _not_open_note(self, device_type: Optional[str]) -> Optional[str]:
        """Said when the appliance is known and Backend sells nothing for it yet.

        Microwave, TV and dishwasher repair are in the catalogue but not open.
        Before catalogue V2 they fell back to a generic call-out; that service
        is gone, and a button that books something Backend refuses is worse
        than saying so."""
        if not device_type:
            return None
        name = (self._kb.device_name_vi(device_type) or "").lower()
        if not name:
            return None
        return (
            f"Hiện FixHome chưa mở dịch vụ sửa {name} nên em chưa đặt thợ cho "
            "thiết bị này được ạ. Anh/chị cần sửa thiết bị khác thì nhắn em nhé."
        )

    def _not_open_response(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace", device_type: str
    ) -> DiagnosisResponse:
        message = "Dạ " + (self._not_open_note(device_type) or "")
        chat.add("assistant", message)
        trace.add("scope", True, f"Khách muốn đặt {device_type}, backend chưa mở dịch vụ này")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.OK,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(None, chat),
            recommended_services=[],
            message_vi=message,
            confidence=0.0,
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _services_for_device(self, device_type: str) -> List[RecommendedService]:
        """The service this appliance is most often booked for.

        Counted across the appliance's own faults rather than chosen by hand, so
        a device added to the catalogue is covered without touching this.
        """
        counts: dict = {}
        names: dict = {}
        for fault in self._kb.faults_for_device(device_type):
            for ref in self._kb.services_for_fault(fault.fault_code):
                counts[ref.service_code] = counts.get(ref.service_code, 0) + 1
                names[ref.service_code] = ref.name_vi
        if not counts:
            return []
        code = max(counts, key=lambda c: counts[c])
        return [RecommendedService(service_code=code, name_vi=names[code])]

    def _booking_needs_the_appliance(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace"
    ) -> DiagnosisResponse:
        """They want to book and have not said what. Ask, and still offer.

        "Cho mình đặt lịch" and "đặt luôn đi" name nothing, so the appliance has
        to be asked for. What must not happen is what used to: falling through
        to the ordinary clarification, which for a message carrying no symptom
        either had nothing to offer, so a customer who said plainly that they
        wanted to book was left with no way to do it.
        """
        question = (
            "Dạ vâng ạ, anh/chị muốn đặt dịch vụ cho thiết bị nào ạ? "
            "Ví dụ máy lạnh, máy giặt, tủ lạnh, bếp, bồn cầu hay đường nước."
        )
        chat.add("assistant", question)
        trace.add("scope", True, "Khách muốn đặt lịch nhưng chưa nói thiết bị")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(None, chat),
            # The appliance is what is missing, and every service is for one.
            recommended_services=[],
            clarification=Clarification(questions_vi=[question]),
            message_vi=question,
            confidence=0.0,
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _greeting_response(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace"
    ) -> DiagnosisResponse:
        """Say hello back and ask what is wrong.

        Not a refusal and not a diagnosis. "Alo" answered with "em chỉ hỗ trợ
        các vấn đề về điện nước" is the assistant explaining its job to someone
        who was being polite.
        """
        question = settings.GREETING_MESSAGE_VI
        chat.add("assistant", question)
        trace.add("scope", True, "Khách chào hỏi, chưa có thông tin sự cố")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            confidence=0.0,
            is_low_confidence=True,
            clarification=Clarification(
                questions_vi=[question],
                service_group_codes=self._kb.all_service_groups(),
            ),
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _catalog_offer(self, text: str):
        """A service Backend sells for an appliance the knowledge base does not
        cover, when the customer named that appliance.

        Before Backend's catalogue was followed live, "máy hút mùi kêu to" was
        refused as not a household repair while the app sold "Vệ sinh & sửa
        motor máy hút mùi". There is nothing to diagnose it from, and the
        answer says so; but the customer is pointed at the service instead of
        being turned away."""
        service = service_catalog.current().service_named_in(text, self._kb)
        if service is None:
            return None
        message = (
            "Em chưa có dữ liệu để chẩn đoán thiết bị này, nhưng FixHome có dịch vụ "
            f"\"{service.name_vi}\". Anh/chị đặt dịch vụ này để thợ tới kiểm tra "
            "và báo giá tại chỗ ạ."
        )
        return message, RecommendedService(service_code=service.code, name_vi=service.name_vi)

    def _offer_response(
        self, request: DiagnosisRequest, chat: Optional[Conversation], trace: "_Trace", message: str, service
    ) -> DiagnosisResponse:
        trace.add("scope", True, f"Thiết bị ngoài kho tri thức, Backend có dịch vụ {service.service_code}")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id if chat else None,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            confidence=0.0,
            is_low_confidence=True,
            recommended_services=[service],
            clarification=Clarification(
                questions_vi=[message],
                service_group_codes=self._kb.all_service_groups(),
            ),
            message_vi=message,
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _out_of_scope_response(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace"
    ) -> DiagnosisResponse:
        """Say plainly that this is not what FixHome does, and offer the way back.

        Not an error: the customer did nothing wrong, they asked a repair app
        about something else. Answering with questions about their appliance
        pretends not to have read it.
        """
        offer = self._catalog_offer(chat.customer_text())
        if offer is not None:
            return self._offer_response(request, chat, trace, *offer)
        trace.add("scope", False, "Câu hỏi không thuộc phạm vi sửa chữa gia dụng")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            confidence=0.0,
            is_low_confidence=True,
            clarification=Clarification(
                questions_vi=[settings.OUT_OF_SCOPE_MESSAGE_VI],
                service_group_codes=self._kb.all_service_groups(),
            ),
            model_info=self._model_info,
            trace=trace.stages,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _is_off_topic(self, text: str) -> bool:
        """A subject FixHome has nothing to say on, and nothing about the trade.

        The trade check runs on what is left once the off-topic subject is taken
        out: "đá bóng" holds "bóng", and a football question was let through as
        a question about light bulbs.
        """
        lexicon = dialogue_state.get_lexicon(self._kb)
        if not dialogue_state.is_off_topic(text, lexicon):
            return False
        rest = " " + lexicon.normalize(text) + " "
        for term in lexicon.off_topic_terms:
            rest = rest.replace(f" {term} ", " ")
        return not self._is_in_the_trade(rest)

    def _names_a_symptom(self, text: str, device_type: str) -> bool:
        """Whether, beyond the appliance's name, the text says what is wrong."""
        tokens = re.findall(r"[a-z0-9]+", _fold_vi(text))
        padded = f" {' '.join(tokens)} "
        # Only the appliance's own name is taken out, and the shortest form of
        # it that was used: some aliases carry a symptom ("nghẹt bồn cầu"), and
        # removing those words took "nghẹt" out of "bồn cầu bị nghẹt".
        present = [
            words for words in (re.findall(r"[a-z0-9]+", _fold_vi(a)) for a in self._kb.aliases_vi(device_type))
            if words and f" {' '.join(words)} " in padded
        ]
        name = set(min(present, key=len)) if present else set()
        lexicon = dialogue_state.get_lexicon()
        # "Tủ lạnh k lạnh", "máy lạnh không lạnh": the word negated is part of
        # the name, and the complaint is the negation. Read on the text with
        # shorthand expanded ("k" is "không"), name and all; "không được",
        # "không ổn", "không bình thường" negate nothing in particular.
        normalized = lexicon.normalize(text)
        if self._retriever.names_a_symptom_pair(normalized, device_type, ignore=_VAGUE_NEGATED):
            return True
        # The appliance's own name is never the complaint, in any of its forms:
        # "lò" was left over from "lò vi sóng" and counted as a symptom word.
        own = set(re.findall(r"[a-z0-9]+", _fold_vi(self._kb.device_name_vi(device_type) or "")))
        own = (own - _SUPPLY_WORDS) | self._retriever.name_only_words(device_type)
        # Words as the reader of the conversation sees them, slips mended:
        # "chháu", "quaaa", "khoong", "k", "j", "dc" are the conversation, not
        # the complaint, and read raw they looked like neither.
        tokens = [t for clause in lexicon.clauses(text) for t in clause]
        # "Máy lọc nước ... không có nước": the second "nước" is the complaint,
        # the first one the name. A supply word counts once it is said more
        # often than the name says it.
        said = [t.f for t in tokens]
        repeated = {w for w in _SUPPLY_WORDS if w in name and said.count(w) > 1}
        for token in _without_framing_tokens(tokens, lexicon):
            folded = token.f
            if (folded in name and folded not in repeated) or folded in own or not folded:
                continue
            # Typed with accents, the accents decide: "lõi" is a part, "lỗi" is
            # a vague word. Without them, "loi" could be either, and counts as vague.
            if token.a is not None and token.a not in _VAGUE_ACCENTED:
                return True
            if token.a is None and folded not in _VAGUE_WORDS:
                return True
        return False

    def _symptom_index(self) -> dict:
        """Every knowledge-base symptom of three words or more, folded, with the
        appliances it belongs to."""
        cached = getattr(self, "_symptom_index_cache", None)
        if cached is None:
            cached = {}
            for device in self._kb.device_types:
                for fault in self._kb.faults_for_device(device):
                    for symptom in fault.symptoms_vi:
                        words = re.findall(r"[a-z0-9]+", _fold_vi(symptom))
                        if len(words) >= 3:
                            cached.setdefault(f" {' '.join(words)} ", set()).add(device)
            self._symptom_index_cache = cached
        return cached

    def _symptom_phrases(self) -> List[str]:
        return list(self._symptom_index())

    def _device_from_symptom(self, text: str) -> Optional[str]:
        """The appliance a message describes word for word, when only one fits."""
        padded = " " + " ".join(re.findall(r"[a-z0-9]+", _fold_vi(text))) + " "
        devices = set()
        for phrase, owners in self._symptom_index().items():
            if len(phrase.split()) >= 4 and phrase in padded:
                devices |= owners
        return devices.pop() if len(devices) == 1 else None

    def _is_in_the_trade(self, question: str) -> bool:
        """Whether this is about a household appliance, plumbing or electrics.

        Deliberately coarse and deliberately strict. Letting through one
        borderline question costs a mediocre answer; letting through every
        question costs the model answering about anything at all in the voice
        of a repair company.
        """
        if device_hint.devices_named_in(question, self._kb):
            return True
        # _fold_vi, not a local copy of it. The copy that was here normalised and
        # stripped combining marks but never mapped đ to d, and the tokeniser
        # that follows keeps only [a-z0-9] — so every đ was deleted rather than
        # folded. "Bị rò điện" arrived as "bi ro ien" and "bóng đèn" as "bong
        # en", which means a message about electricity or lighting — two of the
        # four things FixHome repairs — matched no trade word at all and was
        # refused as off-topic whenever it did not also name an appliance.
        folded = _fold_vi(question)
        # Whole words. Substring matching on folded text let three off-topic
        # questions through in a live run, each on a word that is not there:
        # "2 cộng 2 bằng mấy" contains "ong " and was read as a pipe, "trời đẹp
        # không" contains "hong" and was read as broken, "thời tiết" contains
        # "tho" and was read as a technician. Vietnamese without tone marks is
        # short and collides constantly, which is why the trailing spaces on
        # some of these entries were there in the first place.
        words = re.findall(r"[a-z0-9]+", folded)
        padded = f" {' '.join(words)} "
        # "Em đang đứng ngoài cửa không vào nhà được" names no appliance and no
        # trade word, and is word for word a symptom of a smart lock that has
        # locked its owner out. A symptom the knowledge base lists, three words
        # or longer, is in the trade.
        if any(phrase in padded for phrase in self._symptom_phrases()):
            return True
        for phrase in _TRADE_WORDS:
            phrase = phrase.strip()
            if " " in phrase:
                if f" {phrase} " in padded:
                    return True
            elif phrase in words:
                return True
        return False

    def _ungrounded_answer(
        self,
        request: ChatRequest,
        chat: Optional[Conversation] = None,
        in_the_trade: bool = True,
    ) -> ChatResponse:
        """Nothing to answer from. What to say depends on why.

        Inside the trade, the honest thing is that this is not written down,
        and the technician who rings before the visit can say. Outside it,
        inviting somebody to book a repair because they asked about the weather
        is worse than the sentence it replaced.
        """
        return ChatResponse(
            request_id=request.request_id,
            session_id=chat.session_id if chat else None,
            status=AnswerStatus.NO_GROUNDING,
            answer_vi=(
                settings.NO_GROUNDING_MESSAGE_VI
                if in_the_trade
                else settings.OUT_OF_SCOPE_MESSAGE_VI
            ),
            confidence=0.0,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _detect_one(self, image: str) -> Optional[Detection]:
        key = hashlib.sha1(image.encode("ascii", "ignore")).hexdigest()
        if key in self._seen_photos:
            self._seen_photos.move_to_end(key)
            return self._seen_photos[key]
        payload: ImagePayload = load_base64_image(image)
        detections = await self._detector.detect(payload)
        raw = detections[0] if detections else None
        best = raw
        if best is not None and best.confidence < settings.DETECTOR_CONFIDENCE_THRESHOLD:
            best = None
        if raw is None or raw.confidence < settings.PHOTO_CHECK_BELOW:
            best = await self._second_look(payload, raw, best)
        # The router reads a photograph to know which appliance it shows, and
        # the conversation it is routed to reads it again for the diagnosis.
        self._seen_photos[key] = best
        while len(self._seen_photos) > 24:
            self._seen_photos.popitem(last=False)
        return best

    async def _detect_images(
        self, images: List[str], description: str, chat: Conversation
    ) -> Optional[Detection]:
        """Every photograph, up to three, each read for its own appliance.

        Only the first used to be looked at, so a customer who photographed
        the air conditioner, the washing machine and the fridge was answered
        about the air conditioner alone. Now each is detected (concurrently),
        the one the message is about leads, and the others join the visit as
        appliances waiting their turn (`chat.queued`), so the reply can offer a
        service for each and "xem tiếp" goes through them.

        The first image is validated as before: a broken one is the caller's
        error. A broken second or third one is skipped, not fatal, because the
        customer still has an answer to get about the first.
        """
        if not images:
            return None
        first = asyncio.ensure_future(self._detect_one(images[0]))
        rest = [asyncio.ensure_future(self._safe_detect(i)) for i in images[1:3]]
        found = [await first] + [await task for task in rest]
        seen = [(i, d) for i, d in enumerate(found) if d is not None]
        if not seen:
            return None
        named = _device_named_in(description, self._kb)
        shown = [d.device_type for _, d in seen]
        if named is None:
            # "Máy giặt không cấp nước" also names a water pipe in "nước", and a
            # name that is not unique used to mean none, so the first
            # photograph led. Among the appliances photographed, it is unique.
            spoken = {m[0] for m in _appliance_mentions(description, self._kb)}
            spoken |= {n.device_type for n in device_hint.devices_named_in(description, self._kb)}
            in_photos = [d for d in shown if d in spoken]
            named = in_photos[0] if len(set(in_photos)) == 1 else _short_named(description, shown)
        lead = next((d for _, d in seen if d.device_type == named), None)
        machine = _strongly_named_in(dialogue_state.get_lexicon(self._kb).normalize_accented(description), self._kb)
        if machine is None and named is None and len(images) == 1:
            # The same with a symptom only one appliance has, and no name.
            machine = named = self._device_from_symptom(description)
        if (
            lead is None and len(images) == 1 and machine and machine == named
            and seen[0][1].device_type not in self._kb.confusable_with(machine)
        ):
            # One photograph and the appliance named outright, and the detector
            # sees another: the words are what the customer means. On the
            # served model, 25/10/2026, "máy lạnh không mát" with a photograph
            # of an air conditioner read as a fan was answered about a fan, and
            # "đây là bình nóng lạnh" about a smart lock.
            chat.seen = []
            return None
        if lead is None and not (named and len(images) > 1):
            lead = seen[0][1]
        # With several photographs and an appliance named that none of them
        # shows, the words lead and every photographed appliance waits its
        # turn. Taking the first photograph instead answered "máy lạnh không
        # mát" about the fan in the second picture, and the air conditioner the
        # customer was talking about was not in the reply at all. One photograph
        # keeps the old rule: it is the appliance in question, and the words
        # and the detector are reconciled by device_hint.resolve as before.
        by_device: dict = {}
        for index, d in seen:
            by_device.setdefault(d.device_type, (index, d))
        chat.seen = [(i, d.device_type, d.confidence) for i, d in by_device.values()]
        for index, d in by_device.values():
            memo = chat.memo.setdefault(d.device_type, {})
            memo["image_index"] = index
            memo["confidence"] = d.confidence
            memo["uncertain"] = d.uncertain
            if (lead is not None and d.device_type == lead.device_type) or d.device_type == chat.device_type:
                continue
            if d.device_type not in chat.queued:
                chat.queued[d.device_type] = memo.get("text", "")
                chat.just_seen.append(d.device_type)
        return lead

    async def _second_look(
        self, payload: ImagePayload, raw: Optional[Detection], best: Optional[Detection]
    ) -> Optional[Detection]:
        """What a photograph shows when the detector is unsure: asked of the VLM.

        On the served detector, 25/10/2026, washing machines were read as a
        sink or a smart lock and water heaters as a fridge, at confidences a
        threshold of 0.45 let through, and the reply followed the photograph.
        Below PHOTO_CHECK_BELOW the vision-language model, which reads the
        whole photograph, is asked which appliance it is. The same answer
        confirms the detector; another answer replaces it, marked as a guess;
        no answer leaves the detector's reading, marked as a guess when it was
        weak. A guess is said in the reply and can be corrected ("ảnh 2 là
        tủ lạnh"), so a wrong one costs a tap, not a wrong diagnosis.
        """
        identify = getattr(self._vlm, "identify", None)
        seen = None
        if identify is not None:
            choices = [(d, self._kb.device_name_vi(d) or d) for d in self._kb.device_types]
            try:
                seen = await identify(payload, choices)
            except Exception as exc:  # pragma: no cover - a second look is never load-bearing
                logger.warning("photo_second_look_failed: %s", type(exc).__name__)
        if seen not in self._kb.device_types:
            seen = None
        whole = (0, 0, payload.width, payload.height)
        said = raw.device_type if raw is not None else ""
        if seen is not None and raw is not None and seen == raw.device_type:
            return dataclasses.replace(
                raw, confidence=max(raw.confidence, settings.PHOTO_CHECK_BELOW), checked="agreed", first_reading=said
            )
        if seen is not None:
            return Detection(
                device_type=seen, confidence=settings.PHOTO_CHECK_TRUST, box_xywh=whole, crop=payload,
                checked="model", first_reading=said,
            )
        if best is not None:
            return dataclasses.replace(best, checked="unsure", first_reading=said)
        return None

    async def _safe_detect(self, image: str) -> Optional[Detection]:
        try:
            return await self._detect_one(image)
        except Exception as exc:  # one unreadable extra photo must not cost the answer
            logger.warning("Bỏ qua một ảnh không đọc được: %s", exc)
            return None

    @staticmethod
    def _combine_confidence(
        detection: Optional[Detection], vlm_confidence: float
    ) -> float:
        """Text-only requests are not penalised for having no detector signal."""
        if detection is None:
            return round(vlm_confidence, 4)
        return round((detection.confidence + vlm_confidence) / 2, 4)

    async def _clarification_response(
        self,
        request: DiagnosisRequest,
        confidence: float,
        shortlist: Optional[List] = None,
        detection: Optional[Detection] = None,
        chat: Optional[Conversation] = None,
        trace: Optional["_Trace"] = None,
    ) -> DiagnosisResponse:
        """Never guess. Ask the question that narrows it down.

        Questions come from the shortlist when there is one, so they separate
        the candidates actually under consideration rather than restating a
        form. Only when nothing was retrieved do they fall back to generic
        ones, and even then knowing the device from the photo removes the
        pointless question about what the device is.
        """
        device_name = (
            self._kb.device_name_vi(detection.device_type) if detection else None
        )
        # Everything said so far, not just this message, so a question already
        # answered two turns ago is not put again.
        said = chat.customer_text() if chat else request.description
        # With no appliance settled, the shortlist spans every device the words
        # happened to touch, and a symptom taken from it is a question about
        # somebody else's machine. "Hỏng" was answered with "Thiết bị có hiện
        # tượng block không lên không?" — a compressor, in trade slang, to
        # someone who had typed one word. "Sửa đi" got "Thiết bị có hiện tượng
        # Quạt bò không?", which is not a sentence.
        #
        # Ask which appliance instead. That is the thing actually missing, and
        # it is a question anybody can answer.
        settled = bool(detection) or bool(chat and chat.device_type)
        if not settled and trace is not None:
            # "Thiết bị gặp sự cố là loại nào?" to someone who said "máy hút
            # mùi": they did name it, it is just not an appliance the knowledge
            # base covers. If Backend sells a service for it, point there.
            offered = self._catalog_offer(said)
            if offered is not None:
                return self._offer_response(request, chat, trace, *offered)
        if not settled and chat is not None:
            # Nothing in this turn named an appliance, so nothing in it can be
            # a symptom either - it is "nhà em có cái máy bị hỏng" or shorter.
            # Keep it in the thread, keep it out of the retrieval query: joined
            # with a real symptom later it out-scores it, because every word in
            # it is a word the symptom lists also use.
            chat.this_turn_had_no_symptom()
        questions = (
            clarifier.texts(
                clarifier.build_questions(
                    shortlist or [],
                    said,
                    discriminators=self._kb.discriminators_for_device(
                        detection.device_type if detection else None
                    ),
                )
            )
            if settled
            else []
        ) or clarifier.device_questions(device_name)

        # One question about which device it is, and only when the customer has
        # not already said. Asking what was just written is how a support bot
        # starts feeling like it is not listening.
        confusion = device_hint.confusion_question(
            detection.device_type if detection else None,
            said,
            self._kb,
        )
        if confusion and confusion not in questions:
            questions = [confusion, *questions][: clarifier.MAX_QUESTIONS]
            if chat is not None and detection is not None:
                chat.awaiting_confusion_about = detection.device_type

        if chat is not None:
            # Drop anything already put to this customer, then record what is
            # left. Repeating a question reads as not having listened, which
            # costs more trust than the answer would have been worth.
            questions = [q for q in questions if q not in chat.asked_symptoms]

        if chat is not None and chat.times_asked >= settings.MAX_CLARIFYING_TURNS and shortlist:
            # Asked enough. A customer who has answered two rounds of questions
            # and is asked a third has stopped being helped and started filling
            # in a form. Commit to the shortlist and let confidence say how sure
            # that is; a technician settles it on site regardless.
            return await self._best_effort_response(
                request, confidence, shortlist, detection, chat, trace
            )

        if chat is not None and chat.answered and shortlist:
            # This customer has already been given a diagnosis. Going back to
            # questions retracts it, and from their side the assistant simply
            # forgot. Refine instead: keep answering, and let confidence carry
            # the doubt.
            return await self._best_effort_response(
                request, confidence, shortlist, detection, chat, trace
            )

        if not questions:
            # Nothing left to ask. Returning a clarification with no question is
            # a dead end: the customer is told more information is needed and
            # given no way to supply it, which is how the second turn of a real
            # conversation ended. Commit to what retrieval ranked first instead
            # and let the confidence say how sure that is.
            return await self._best_effort_response(request, confidence, shortlist, detection, chat, trace)

        if chat is not None:
            chat.times_asked += 1
            chat.remember_questions(questions)
            chat.pending_question = questions[0] if questions else None
            for question in questions:
                chat.add("assistant", question)

        if trace is not None:
            trace.add(
                "knowledge_base",
                True,
                f"Hỏi lại khách {len(questions)} câu thay vì đoán",
                questions=questions,
            )

        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id if chat else None,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(detection, chat),
            confidence=confidence,
            is_low_confidence=True,
            clarification=Clarification(
                questions_vi=questions,
                service_group_codes=self._kb.all_service_groups(),
            ),
            # Asking and offering are not exclusive. The customer still has to
            # answer the question, but they no longer have to wait for the
            # answer before they can book anybody.
            recommended_services=self._service_to_offer(
                shortlist, chat.device_type if chat else None, chat
            ),
            # Asking which appliance it is does not make a burning smell less
            # urgent. "Cháy khét" is two words and settles nothing, so it is
            # right to ask — and wrong to hand the client a LOW beside the
            # question, because the client decides from this field how loudly
            # to show the reply.
            urgency=self._highest_urgency(shortlist),
            model_info=self._model_info,
            trace=trace.stages if trace else [],
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _services_for_answer(
        self, codes: List[str], device_type: Optional[str], chat: Optional[Conversation] = None
    ) -> List[RecommendedService]:
        """What a chat answer leaves the customer able to book.

        Empty when the question was not about a broken appliance. Somebody
        asking how long the warranty lasts does not want a button, and putting
        one there turns every answer into a sales pitch.
        """
        if device_type is None or not codes:
            return []
        faults = [self._kb.fault(code) for code in codes]
        return self._service_to_offer([f for f in faults if f], device_type, chat)

    def _spent_services(self, chat: Optional[Conversation]) -> set:
        """Services the customer has, in effect, already had.

        "Mới vệ sinh rồi" rules out the dirty filter, and with it the cleaning
        service: offering to book a cleaning to someone who just had one is the
        same mistake as naming the dirty filter again, one field over. Only
        exclusions of the kind "done" spend a service; a cause the customer
        denies says nothing about what they have paid for.
        """
        if chat is None:
            return set()
        spent = set()
        for code, exclusion in chat.state.excluded.items():
            if exclusion.kind == "done":
                spent.update(ref.service_code for ref in self._kb.services_for_fault(code))
        return spent

    def _service_to_offer(
        self,
        shortlist: Optional[List],
        device_type: Optional[str],
        chat: Optional[Conversation] = None,
    ) -> List[RecommendedService]:
        """One service the customer could book right now, even mid-question.

        A question with no way forward attached is where conversations died:
        the customer answered, the assistant asked again, and nobody ever
        arrived at a booking. Naming a service alongside the question costs the
        customer nothing and gives the app something to put a button on.

        Never a confident cleaning when the fault is still open. If the faults
        under consideration all book the same service, that is the one; where
        they disagree, the appliance's repair, which is priced on inspection:
        literally what is being proposed — somebody comes and looks.
        """
        # Nothing until the appliance is settled. Without this guard "hư rồi"
        # — two words naming nothing — was offered a refrigerator repair,
        # because the shortlist it retrieved happened to be all one device.
        # Unless the word used covers appliances that are all booked the same
        # way: "quạt" is a ceiling or a standing fan, and both are "Sửa quạt
        # điện", so the question which one can come with the button.
        if device_type is None:
            return self._family_offer(chat.customer_text() if chat is not None else "")

        codes = []
        for entry in shortlist or []:
            fault = getattr(entry, "fault", entry)
            for ref in self._kb.services_for_fault(getattr(fault, "fault_code", "")):
                if ref.service_code not in codes:
                    codes.append(ref.service_code)
        spent = self._spent_services(chat)
        if spent and any(code not in spent for code in codes):
            codes = [code for code in codes if code not in spent]
        if len(codes) == 1:
            ref = next(
                r
                for entry in shortlist
                for r in self._kb.services_for_fault(
                    getattr(getattr(entry, "fault", entry), "fault_code", "")
                )
                if r.service_code == codes[0]
            )
            return [
                RecommendedService(service_code=ref.service_code, name_vi=ref.name_vi)
            ]

        return self._fallback_offer(device_type)

    _FAMILY_GENERIC = frozenset({"cai", "cho", "thay", "may", "nuoc", "binh"})

    def _family_offer(self, text: str) -> List[RecommendedService]:
        """The one repair every appliance a word can mean is booked under.

        Read from the knowledge base's own names: the appliances whose names
        start with a word the customer used ("quạt", "bồn", "công tắc"), and
        only when they all share the same repair service. "Lò" (microwave or
        oven) and "bếp" (gas or induction) are booked differently, so they
        get the question alone."""
        words = set(re.findall(r"[a-z0-9]+", _fold_vi(text)))
        if not words:
            return []
        for head in sorted(words - self._FAMILY_GENERIC):
            devices = {
                d for d in self._kb.device_types
                if any(_fold_vi(a).split()[:1] == [head] for a in self._kb.aliases_vi(d))
            }
            if len(devices) < 2:
                continue
            codes = {self._kb.default_service_code(d) for d in devices}
            if len(codes) != 1:
                continue
            offer = self._fallback_offer(next(iter(devices)))
            if offer:
                return offer
        return []

    def _fallback_offer(self, device_type: Optional[str]) -> List[RecommendedService]:
        """The appliance's own repair, in Backend's code so the app can book it.

        Nothing for an unknown appliance or one whose repair is not open."""
        ref = self._kb.fallback_service(device_type)
        return (
            [RecommendedService(service_code=ref.service_code, name_vi=ref.name_vi)]
            if ref
            else []
        )

    def _highest_urgency(self, shortlist: Optional[List]) -> UrgencyLevel:
        """The most urgent fault still under consideration."""
        urgency = UrgencyLevel.LOW
        for entry in shortlist or []:
            # Callers pass faults here and scored faults there; taking either
            # is cheaper than making them agree, and reading the wrong one
            # silently returns LOW for a burning smell.
            fault = getattr(entry, "fault", entry)
            if not hasattr(fault, "urgency"):
                continue
            level = UrgencyLevel(fault.urgency)
            if _URGENCY_RANK[level] > _URGENCY_RANK[urgency]:
                urgency = level
        return urgency

    async def _best_effort_response(
        self,
        request: DiagnosisRequest,
        confidence: float,
        shortlist: Optional[List],
        detection: Optional[Detection],
        chat: Optional[Conversation],
        trace: Optional["_Trace"],
    ) -> DiagnosisResponse:
        """Answer with retrieval's own ranking when there is nothing left to ask.

        The model declining to choose is not the same as there being nothing to
        say: retrieval put WH_INSTANT_NO_HOT at the top for "máy nước nóng
        không nóng", which is the right answer, and the customer got a dead end
        instead. Confidence is reported as retrieval's alone, so a client can
        see this was not a model verdict.
        """
        if not shortlist:
            return self._no_answer_response(request, confidence, detection, chat, trace)

        if chat is not None and chat.device_type is None:
            # Committing to retrieval's ranking is only safe once the appliance
            # is known. Without one it searches all seventeen at once: a
            # photograph of a television the detector missed, described as "bị
            # sọc", came back as a broken fan motor and a faulty thermostat,
            # stated with confidence. Ask which appliance instead — that
            # question is never one the customer has already answered.
            return self._no_answer_response(request, confidence, detection, chat, trace)

        verdict = VlmVerdict(
            fault_codes=[f.fault_code for f in shortlist[:2]],
            confidence=min(confidence, 0.5),
        )
        if trace is not None:
            trace.add(
                "fallback",
                True,
                "Hết câu để hỏi, dùng thẳng thứ hạng của RAG thay vì bỏ lửng",
                faults=verdict.fault_codes,
            )
        return await self._build_response(
            request, detection, verdict, verdict.confidence, shortlist, chat, trace,
            source=EvidenceSource.KNOWLEDGE_BASE,
        )

    def _no_answer_response(
        self,
        request: DiagnosisRequest,
        confidence: float,
        detection: Optional[Detection],
        chat: Optional[Conversation],
        trace: Optional["_Trace"],
    ) -> DiagnosisResponse:
        """Nothing retrieved and nothing left to ask: say so and let Backend on.

        Rare, and the honest end of the road. The generic questions are better
        than silence because at least one of them can be answered.
        """
        questions = clarifier.device_questions(
            self._kb.device_name_vi(detection.device_type) if detection else None
        )
        if trace is not None:
            trace.add("fallback", False, "Không còn gì để hỏi và cũng không có bệnh nào")
        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id if chat else None,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(detection, chat),
            confidence=confidence,
            is_low_confidence=True,
            clarification=Clarification(
                questions_vi=questions,
                service_group_codes=self._kb.all_service_groups(),
            ),
            model_info=self._model_info,
            trace=trace.stages if trace else [],
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _build_response(
        self,
        request: DiagnosisRequest,
        detection: Optional[Detection],
        verdict: VlmVerdict,
        confidence: float,
        shortlist: Optional[List] = None,
        chat: Optional[Conversation] = None,
        trace: Optional["_Trace"] = None,
        source: EvidenceSource = EvidenceSource.DESCRIPTION,
    ) -> DiagnosisResponse:
        device = self._resolve_device(detection, chat)

        faults: List[SuspectedFault] = []
        services: List[RecommendedService] = []
        actions: List[str] = []
        price_min: Optional[int] = None
        price_max: Optional[int] = None
        needs_assessment = False
        urgency = UrgencyLevel.LOW

        for code in _ranked_by_retrieval(
            verdict.fault_codes,
            shortlist,
            # The model leads only when the photograph showed it something:
            # damage it reported (a burn mark, water under the machine). A plain
            # photo of an air conditioner says nothing about its compressor,
            # and on fixhome.sbs 25/10/2026 "chạy cả ngày mà phòng vẫn nóng"
            # with one came back as a failed compressor at 2.249.000đ instead
            # of retrieval's low refrigerant.
            saw_a_photograph=detection is not None and bool(verdict.condition_codes),
            excluded=chat.state.excluded_codes() if chat is not None else None,
        ):
            fault = self._kb.fault(code)
            if fault is None:
                continue  # model named a code outside the catalog; drop it
            faults.append(
                SuspectedFault(
                    fault_code=fault.fault_code,
                    name_vi=fault.name_vi,
                    confidence=verdict.confidence,
                    source=source,
                )
            )
            refs = self._kb.services_for_fault(fault.fault_code)
            for ref in refs:
                if all(s.service_code != ref.service_code for s in services):
                    services.append(
                        RecommendedService(
                            service_code=ref.service_code, name_vi=ref.name_vi
                        )
                    )
            for action in fault.suggested_actions_vi:
                if action not in actions:
                    actions.append(action)
            price_min = (
                fault.price_min if price_min is None else min(price_min, fault.price_min)
            )
            price_max = (
                fault.price_max if price_max is None else max(price_max, fault.price_max)
            )
            needs_assessment = needs_assessment or fault.requires_assessment
            fault_urgency = UrgencyLevel(fault.urgency)
            if _URGENCY_RANK[fault_urgency] > _URGENCY_RANK[urgency]:
                urgency = fault_urgency

        if not faults:
            return await self._clarification_response(
                request, confidence, shortlist, detection, chat, trace
            )

        if trace is not None:
            trace.add(
                "knowledge_base",
                True,
                f"Dịch {len(faults)} mã sang tiếng Việt, kèm giá và việc nên làm",
                faults=[f.fault_code for f in faults],
                price_min=price_min,
                price_max=None if needs_assessment else price_max,
                requires_assessment=needs_assessment,
            )

        if chat is not None:
            chat.shortlist = [f.fault_code for f in faults]
            chat.answered = True
            chat.add("assistant", ", ".join(f.name_vi for f in faults))

        message_vi = await self._narrate(
            device, faults, price_min, None if needs_assessment else price_max,
            actions, services,
            ruled_out=self._ruled_out_names(chat) if chat is not None else (),
        )
        if not services:
            note = self._not_open_note(faults and self._kb.fault(faults[0].fault_code).device_type)
            if note:
                message_vi = f"{message_vi} {note}" if message_vi else note

        return DiagnosisResponse(
            request_id=request.request_id,
            session_id=chat.session_id if chat else None,
            message_vi=message_vi,
            status=DiagnosisStatus.OK,
            engine=Engine.LOCAL_PIPELINE,
            device=device,
            visible_conditions=self._resolve_conditions(verdict),
            suspected_faults=faults,
            recommended_services=services,
            suggested_actions_vi=actions,
            # A ceiling is only worth showing when every suspected fault has one.
            # If any of them needs a technician to look, taking the highest
            # ceiling among the others would put a firm number on a case nobody
            # can price yet, and it is the low one that the customer would read
            # as the whole cost.
            price_estimate=PriceEstimate(
                min=price_min or 0,
                max=None if needs_assessment else (price_max or 0),
                requires_assessment=needs_assessment,
            ),
            urgency=urgency,
            confidence=confidence,
            is_low_confidence=False,
            model_info=self._model_info,
            trace=trace.stages if trace else [],
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _resolve_device(
        self,
        detection: Optional[Detection],
        chat: Optional[Conversation] = None,
    ) -> Optional[DetectedDevice]:
        if detection is None:
            # A follow-up has no photograph, but the appliance has not changed.
            # Reporting nothing makes the client show "unknown device" on every
            # turn after the first, which looks like the photo was forgotten.
            #
            # Only a device an earlier photograph established is reported.
            # One merely inferred from the customer's words is remembered for
            # retrieval but not announced as detected: the pipeline has not
            # looked at the appliance, and putting a confidence on a sentence
            # would mean inventing one.
            if chat is not None and chat.device_type and chat.device_source_vi == "image":
                remembered = self._kb.device_name_vi(chat.device_type)
                if remembered is not None:
                    return DetectedDevice(
                        device_type=chat.device_type,
                        name_vi=remembered,
                        confidence=chat.device_confidence,
                        source=EvidenceSource.IMAGE,
                        # No box: this turn had no image to draw one on.
                        bounding_box=None,
                    )
            return None
        name_vi = self._kb.device_name_vi(detection.device_type)
        if name_vi is None:
            return None
        x, y, w, h = detection.box_xywh
        return DetectedDevice(
            device_type=detection.device_type,
            name_vi=name_vi,
            confidence=detection.confidence,
            source=EvidenceSource.IMAGE,
            bounding_box=BoundingBox(x=x, y=y, width=w, height=h),
            uncertain=detection.uncertain,
        )

    def _resolve_conditions(self, verdict: VlmVerdict) -> List[VisibleCondition]:
        if not settings.VLM_REPORT_VISIBLE_CONDITIONS:
            # Still computed and still logged upstream, so the measurement can
            # be made; simply not told to the customer. See the setting for why.
            return []
        conditions: List[VisibleCondition] = []
        for code in verdict.condition_codes:
            name_vi = self._kb.condition_name_vi(code)
            if name_vi is None:
                continue  # outside the curated condition catalog
            conditions.append(
                VisibleCondition(
                    code=code,
                    name_vi=name_vi,
                    confidence=verdict.confidence,
                    source=EvidenceSource.IMAGE,
                )
            )
        return conditions
