# app/services/pipeline/local_pipeline.py
"""Orchestrates detector, retrieval, VLM and knowledge-base lookup."""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, List, Optional, Sequence

import logging

from app.core.config import settings
from app.schemas.chat import AnswerStatus, ChatRequest, ChatResponse, Citation
from app.schemas.diagnosis import (
    BoundingBox,
    Clarification,
    DetectedDevice,
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    Engine,
    ModelInfo,
    EvidenceSource,
    PriceEstimate,
    RecommendedService,
    SuspectedFault,
    TraceStage,
    UrgencyLevel,
    VisibleCondition,
)
from app.services.pipeline import clarifier
from app.services.pipeline import context
from app.services.pipeline import device_hint
from app.services.pipeline.conversation import Conversation, get_conversation_store
from app.services.pipeline.detector import Detection, Detector
from app.services.pipeline.images import ImagePayload, load_base64_image
from app.services.pipeline.knowledge_base import KnowledgeBase, ServiceRef
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


def _recent_dialogue(chat: Conversation) -> str:
    """The last few turns, labelled, oldest first.

    customer_text() joins only what the customer said, which is right for
    retrieval and wrong for a prompt: the model needs to see what it already
    answered, or it answers it again.
    """
    lines = [
        ("Khách" if t.role == "customer" else "Bạn") + f": {t.text_vi}"
        for t in chat.turns[-_DIALOGUE_TURNS:]
    ]
    return "\n".join(lines)


def _standalone_question(question: str, chat: Conversation, kb: KnowledgeBase) -> str:
    """The question with enough of the thread in front of it to mean something.

    "Chi phí thay aptomat máy giặt", then "giá bao nhiêu". The second message
    retrieved on three words that name no appliance and no part, matched a
    policy line about fixed-price services, and the customer was told something
    true about a different subject. It is not a new question; it is the end of
    the previous one.
    """
    earlier = [t.text_vi for t in chat.turns if t.role == "customer"][:-1]
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


_ASKS_FOR = ("doi sang", "doi qua", "doi thanh", "chuyen sang", "chuyen qua", "doi lai thanh")
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


def _device_asked_for_now(latest: str, kb: KnowledgeBase) -> Optional[str]:
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
        left = [d for d in named if d not in refused]
        if len(left) == 1:
            return left[0]

    # No marker at all. A turn that names one appliance on its own still
    # changes the subject - "tủ lạnh cũng hỏng nữa" is about the fridge now -
    # and a turn naming none leaves the session's appliance alone.
    return _device_named_in(latest, kb)


def _ranked_by_retrieval(
    chosen: Sequence[str],
    shortlist: Optional[Sequence[Any]],
    *,
    saw_a_photograph: bool,
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
    if saw_a_photograph:
        return list(chosen)
    ranked = [getattr(f, "fault_code", None) for f in (shortlist or [])]
    ranked = [code for code in ranked if code]
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
        kb_version = getattr(kb, "version", None)
        self._model_info = ModelInfo(
            # Path rather than a name, because the name is always "best.pt" and
            # the run it came from is the only thing that identifies it.
            detector=settings.YOLO_WEIGHTS_PATH or None,
            vlm=settings.VLM_MODEL_NAME if settings.VLM_BASE_URL else None,
            knowledge_base_version=kb_version,
        )

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        trace = _Trace(request.include_trace)
        chat = self._conversations.get_or_create(request.session_id)
        chat.add("customer", request.description)
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

        detection = await self._detect_primary(request.images)
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
        device_type, _hint = device_hint.resolve(
            request.description, detected, self._kb
        )

        # A change of mind is not always phrased as an order. "Em nhầm rồi, là
        # tủ lạnh" and "bỏ máy lạnh đi, đặt tủ lạnh" carry no booking verb, so
        # they arrive here rather than on the booking path, and until this was
        # added the appliance they replaced stayed in place: measured on the
        # running service, fourteen of sixteen switch phrasings came back with
        # the air conditioning they were moving away from. The unit tests
        # passed throughout, because the understanding was never the problem -
        # only half the routes consulted it.
        switched_to = _device_asked_for_now(request.description, self._kb)
        changed_appliance = bool(
            switched_to and chat.device_type and switched_to != chat.device_type
        )

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
        searched = request.description if changed_appliance else chat.symptom_text()
        candidates = self._retriever.candidate_faults(
            description=searched,
            device_type=device_type,
            top_k=settings.VLM_SHORTLIST_SIZE,
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
            and self._retriever.content_words(chat.customer_text())
            >= settings.DECISIVE_MIN_WORDS
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
        if device_type is None or (
            self._retriever.content_words(chat.customer_text())
            < settings.DECISIVE_MIN_WORDS
        ):
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
        chat = self._conversations.get_or_create(request.session_id)
        chat.add("customer", request.question)

        # Policy text and price rows are both grounding, and a question about
        # cost is the commonest thing a customer asks first. The two tables were
        # loaded and used offline while this surface could not see them, so
        # "dây điện thay bên mình tính giá sao" was refused as out of scope with
        # the answer sitting in a file the service had already read.
        # A follow-up is not a new question. Everything below retrieves on the
        # resolved form; the model is still shown the words the customer typed.
        asked = _standalone_question(request.question, chat, self._kb)
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
        candidates = (
            self._retriever.candidate_faults(asked, device_type)
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
            history_vi=_recent_dialogue(chat),
            safety_vi="\n\n".join(s.chunk.as_passage_vi() for s in safety) or None,
        )
        if not answer_vi:
            return await self._reasoned_answer(request, chat)

        chat.add("assistant", answer_vi)
        return ChatResponse(
            request_id=request.request_id,
            session_id=chat.session_id,
            status=AnswerStatus.OK,
            answer_vi=answer_vi,
            recommended_services=self._services_for_answer(codes, device_type),
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
            return self._ungrounded_answer(request, chat, in_the_trade=False)

        answer_vi = await self._vlm.answer_generally(
            request.question, history_vi=chat.customer_text()
        )
        if not answer_vi:
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
            # about, and the inspection is always bookable.
            recommended_services=(
                self._fallback_offer() if device_type else []
            ),
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
    ) -> Optional[str]:
        """Hand the finished answer to the model to phrase, nothing more.

        Every fact is decided before this runs and none of it may change. The
        client checks that no number appeared which was not supplied, and an
        answer that grew one is discarded rather than corrected.
        """
        money = lambda v: f"{v:,}".replace(",", ".")  # noqa: E731
        lines = []
        if device:
            lines.append(f"Thiết bị: {device.name_vi}")
        lines.append("Khả năng hư hỏng: " + ", ".join(f.name_vi for f in faults))
        if price_min is not None and price_max is not None and price_max != price_min:
            lines.append(f"Chi phí dự kiến: {money(price_min)}đ tới {money(price_max)}đ")
        elif price_min is not None and price_max == price_min:
            lines.append(f"Chi phí dự kiến: {money(price_min)}đ")
        elif price_min is not None:
            lines.append(
                f"Chi phí: từ {money(price_min)}đ, phần còn lại kỹ thuật viên "
                "phải xem tận nơi mới tính được"
            )
        if actions:
            lines.append("Việc khách nên làm ngay: " + "; ".join(actions))
        if services:
            lines.append("Dịch vụ nên đặt: " + ", ".join(s.name_vi for s in services))

        allowed = [
            str(v) for v in (price_min, price_max) if v is not None
        ] + [money(v) for v in (price_min, price_max) if v is not None]
        try:
            return await self._vlm.narrate("\n".join(lines), allowed) or None
        except Exception:  # pragma: no cover - narration is never load-bearing
            logger.warning("narration_failed")
            return None

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
        candidates = self._retriever.candidate_faults(
            chat.symptom_text(), device_type, top_k=settings.VLM_SHORTLIST_SIZE
        )
        services: List[RecommendedService] = []
        # The catalogue's own price, kept beside the service it belongs to. The
        # fault's floor is a number from our labour table and named 100.000đ
        # under "Sửa tủ lạnh" — a different row from the one being booked.
        base: Optional[int] = None
        for scored in candidates:
            refs = self._kb.services_for_fault(scored.fault.fault_code)
            if not refs:
                # Same fallback the diagnosis path uses: every fault names the
                # labour row its floor price came from, so the service is known
                # even where Backend has not issued a code for it.
                labour = self._kb.labour_row(scored.fault.labour_code)
                if labour is None:
                    continue
                refs = [
                    ServiceRef(
                        service_code=labour.code,
                        name_vi=labour.name_vi,
                        base_price=labour.price_min,
                    )
                ]
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
            services = self._fallback_offer()
        if not services:
            return None

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

    def _services_for_device(self, device_type: str) -> List[RecommendedService]:
        """The service this appliance is most often booked for.

        Counted across the appliance's own faults rather than chosen by hand, so
        a device added to the catalogue is covered without touching this. The
        inspection fallback is set aside while counting: it is the answer for a
        fault that cannot be priced unseen, not the answer for "book someone to
        look at my washing machine".
        """
        counts: dict = {}
        names: dict = {}
        fallback = self._kb.fallback_service()
        for fault in self._kb.faults_for_device(device_type):
            for ref in self._kb.services_for_fault(fault.fault_code):
                if fallback and ref.service_code == fallback.service_code:
                    continue
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
            recommended_services=self._fallback_offer(),
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

    def _out_of_scope_response(
        self, request: DiagnosisRequest, chat: Conversation, trace: "_Trace"
    ) -> DiagnosisResponse:
        """Say plainly that this is not what FixHome does, and offer the way back.

        Not an error: the customer did nothing wrong, they asked a repair app
        about something else. Answering with questions about their appliance
        pretends not to have read it.
        """
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

    async def _detect_primary(self, images: List[str]) -> Optional[Detection]:
        """Only the first image is analysed; extras are accepted but unused."""
        if not images:
            return None
        payload: ImagePayload = load_base64_image(images[0])
        detections = await self._detector.detect(payload)
        if not detections:
            return None
        best = detections[0]
        if best.confidence < settings.DETECTOR_CONFIDENCE_THRESHOLD:
            return None
        return best

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
                shortlist, chat.device_type if chat else None
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
        self, codes: List[str], device_type: Optional[str]
    ) -> List[RecommendedService]:
        """What a chat answer leaves the customer able to book.

        Empty when the question was not about a broken appliance. Somebody
        asking how long the warranty lasts does not want a button, and putting
        one there turns every answer into a sales pitch.
        """
        if device_type is None or not codes:
            return []
        faults = [self._kb.fault(code) for code in codes]
        return self._service_to_offer([f for f in faults if f], device_type)

    def _service_to_offer(
        self, shortlist: Optional[List], device_type: Optional[str]
    ) -> List[RecommendedService]:
        """One service the customer could book right now, even mid-question.

        A question with no way forward attached is where conversations died:
        the customer answered, the assistant asked again, and nobody ever
        arrived at a booking. Naming a service alongside the question costs the
        customer nothing and gives the app something to put a button on.

        Never a confident repair when the fault is still open. If the faults
        under consideration all book the same service, that is the one; where
        they disagree, the honest offer is the call-out, because that is
        literally what is being proposed — somebody comes and looks.
        """
        # The specific service only once the appliance is settled. Without this
        # guard "hư rồi" — two words naming nothing — was offered a
        # refrigerator repair, because the shortlist it retrieved happened to be
        # all one device.
        if device_type is None:
            return self._fallback_offer()

        codes = []
        for entry in shortlist or []:
            fault = getattr(entry, "fault", entry)
            for ref in self._kb.services_for_fault(getattr(fault, "fault_code", "")):
                if ref.service_code not in codes:
                    codes.append(ref.service_code)
        if len(codes) == 1:
            ref = next(
                r
                for entry in shortlist
                for r in self._kb.services_for_fault(
                    getattr(getattr(entry, "fault", entry), "fault_code", "")
                )
            )
            return [
                RecommendedService(service_code=ref.service_code, name_vi=ref.name_vi)
            ]

        return self._fallback_offer()

    def _fallback_offer(self) -> List[RecommendedService]:
        """The on-site inspection, in Backend's code so the app can book it."""
        ref = self._kb.fallback_service()
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
            verdict.fault_codes, shortlist, saw_a_photograph=detection is not None
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
            if not refs:
                # Backend has not agreed a service catalogue, and waiting for it
                # meant answering "giờ tôi nên thuê dịch vụ nào" with nothing at
                # all. Every fault already names the labour row its floor price
                # came from, so the service is known — only its Backend code is
                # not, and that is the part Backend owns.
                labour = self._kb.labour_row(fault.labour_code)
                if labour is not None:
                    refs = [ServiceRef(service_code=labour.code, name_vi=labour.name_vi)]
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
        )

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
