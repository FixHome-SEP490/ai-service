# app/services/pipeline/conversation.py
"""What the service remembers between turns of one conversation.

Without this every message is a stranger. A customer sends a photo of their air
conditioner, gets asked whether it was cleaned recently, answers "mới vệ sinh
tháng trước", and the second message arrives with no photo and three words of
text — so the device is unknown again and the answer means nothing. Asking a
question you cannot receive the answer to is worse than not asking.

So a session carries three things forward:

    the device, once a photograph has identified it, because the customer will
    not send the same photo again

    everything the customer has said, joined, because symptoms arrive spread
    across messages and the retriever needs them together

    which questions have already been asked, because repeating one reads as not
    having listened, and that costs more trust than the answer is worth

Deliberately in memory and per-process. A restart loses every conversation,
and two workers do not share one. That is the wrong design for production and
the right one for now: the alternative is a Redis dependency to run the service
at all, and the shape below is what a Redis-backed store would implement.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.pipeline.dialogue_state import DialogueState, TurnReading

SESSION_TTL_SECONDS = 60 * 60
"""How long a conversation survives without a message.

An hour is long enough that a customer can put their phone down, find the
model number and come back, and short enough that a service left running does
not accumulate every conversation it has ever had.
"""

MAX_TURNS = 40
"""Kept per conversation. Beyond this the oldest go.

A support conversation that runs past forty turns has gone wrong in a way more
history will not fix, and an unbounded list is a memory leak with extra steps.
"""

MAX_SESSIONS = 5000
"""Conversations kept at once. Beyond this the least recently used go.

The same argument as MAX_TURNS, which was applied to the list inside a
conversation and not to the dictionary holding them. Turns were bounded and
conversations were not, so anything that produced sessions faster than the
hour-long expiry removed them grew without limit: a crawler, a health check
that sends an id, or simply a busy day.

Five thousand conversations of forty turns is on the order of a hundred
megabytes, which is a ceiling worth having on a box whose memory is mostly
spoken for by the model.
"""


@dataclass
class Turn:
    role: str
    """"customer" or "assistant"."""

    text_vi: str
    at: float = field(default_factory=time.time)

    retrieval_vi: Optional[str] = None
    """The clauses of this turn that describe what is happening, normalised.

    Set by `Conversation.observe`. None means the turn was never read, and the
    raw text is used as before. An empty string means the turn said only what is
    *not* the case - "mới vệ sinh rồi", "không phải đâu" - and contributes
    nothing to retrieval, where its words would have counted as a match for the
    very thing being denied."""

    carried_a_symptom: bool = True
    """Whether this turn said anything the retriever could work with.

    Set False for a turn the service answered by asking what the appliance was,
    because such a turn has no symptom in it by definition. It stays in the
    thread the model is shown - the conversation has to read like one - but it
    is kept out of the retrieval query, where it does damage.

    "nhà em có cái máy bị hỏng" is the case that found this. On its own it says
    nothing, yet every word of it is a word the symptom lists use, so joined
    with a later real symptom it out-scored it: the same sentence that
    retrieves a gas shortage in a fresh conversation retrieved a broken remote
    control two turns into one, and the advice came back as "thử thay pin".
    """


@dataclass
class Conversation:
    session_id: str
    turns: List[Turn] = field(default_factory=list)

    device_type: Optional[str] = None
    """Carried from whichever turn had a photograph.

    Cleared only by a later photograph showing something else, never by a
    message that happens to have no image attached."""

    device_confidence: float = 0.0
    device_source_vi: Optional[str] = None

    asked_symptoms: List[str] = field(default_factory=list)
    """Symptoms already put to the customer, so none is asked twice."""

    awaiting_confusion_about: Optional[str] = None
    """Which device the outstanding either/or question was asked about.

    A bare "không" means nothing on its own. It only resolves the appliance
    against the question it answers, so the question has to outlive the turn
    that asked it."""

    times_asked: int = 0
    """How many turns have come back as questions instead of an answer.

    Capped, because a third round of questions is not diligence, it is a form
    wearing a conversation's clothes. Past the cap the service commits to what
    it has and says how sure it is."""

    answered: bool = False
    """A diagnosis has already been shown to this customer.

    Adding detail must never take the answer away again. Someone who is told
    what is probably wrong, adds a confirming detail, and is then asked three
    questions instead has been made worse off for co-operating."""

    confusion_resolved: bool = False
    """The either/or has been settled, or asked and not answered usefully.

    Either way it is not asked again. A customer who could not answer it the
    first time will not answer it the second, and asking twice is how a support
    bot proves it is a form."""

    shortlist: List[str] = field(default_factory=list)
    """Fault codes still in play, narrowed as answers come in."""

    queued: Dict[str, str] = field(default_factory=dict)
    """Other appliances named in the same message, with what was said about
    each, waiting for "xem tiếp". One message, one appliance at a time."""

    just_queued: List[str] = field(default_factory=list)
    """Appliances queued by the turn being answered, for the sentence that says so."""

    address: Optional[str] = None
    """How the customer names themself ("bác", "cô"...), used in place of
    "anh/chị" for the rest of the conversation."""

    mood: Optional[str] = None
    """"upset" or "worried" for the turn being answered, None otherwise."""

    pending_question: Optional[str] = None
    """The question the assistant asked last, until the customer replies, so a
    bare "không" can be read as the answer to it."""

    past_jobs: List[Dict[str, str]] = field(default_factory=list)
    """The customer's earlier bookings, as the backend sent them, each with the
    appliance code it was matched to ("device", empty when none matched)."""

    recalled: List[str] = field(default_factory=list)

    brand: Optional[str] = None
    """The appliance's brand, once the customer names it ("máy lạnh Daikin")."""

    error_codes: List[str] = field(default_factory=list)
    """Codes already explained, so each is explained once."""

    pending_code: Optional[str] = None
    """A code reported before the brand was known; read once the brand is named."""

    code_notes: List[str] = field(default_factory=list)
    """What each reported code means per the brand, for the technician."""
    """Appliances whose earlier booking was already mentioned, so it is said once."""

    state: DialogueState = field(default_factory=DialogueState)
    """What the customer has ruled out or said is absent. See dialogue_state.py."""

    updated_at: float = field(default_factory=time.time)

    def add(self, role: str, text_vi: str) -> None:
        self.turns.append(Turn(role=role, text_vi=text_vi))
        if len(self.turns) > MAX_TURNS:
            del self.turns[: len(self.turns) - MAX_TURNS]
        self.updated_at = time.time()

    def customer_text(self) -> str:
        """Everything the customer has said, oldest first.

        Symptoms arrive one message at a time — "máy không mát", then later "à
        mà nó còn kêu to nữa" — and each alone retrieves the wrong faults. The
        retriever is given the lot.
        """
        return " ".join(t.text_vi for t in self.turns if t.role == "customer")

    def symptom_text(self) -> str:
        """The same, minus the turns that carried no symptom.

        For retrieval only. Everything else — the prompt, the scope check, the
        device hint — still sees the whole conversation, because a turn with no
        symptom in it can still name the appliance, and because the model has
        to see what was actually said.

        Falls back to the full text when every turn has been marked, so a
        conversation that is all questions still retrieves something rather
        than searching for the empty string.
        """
        kept = [
            turn.text_vi if turn.retrieval_vi is None else turn.retrieval_vi
            for turn in self.turns
            if turn.role == "customer" and turn.carried_a_symptom
        ]
        kept = [text for text in kept if text]
        return " ".join(kept) if kept else self.customer_text()

    def observe(self, reading: TurnReading, never_exclude) -> None:
        """Record what the newest customer turn established."""
        for turn in reversed(self.turns):
            if turn.role == "customer":
                turn.retrieval_vi = reading.retrieval_text
                break
        self.state.apply(reading, set(never_exclude))
        self.updated_at = time.time()

    def past_job(self) -> Optional[Dict[str, str]]:
        """The newest earlier booking for the appliance being talked about."""
        if not self.device_type:
            return None
        return next((job for job in self.past_jobs if job.get("device") == self.device_type), None)

    def notes_vi(self, kb) -> List[str]:
        """What the customer told us beyond the symptom, one short line each.

        Written for the technician who takes the job: "Khách đã vệ sinh rồi"
        saves a visit spent on a cleaning, and "Khách nghi thiếu gas" is where
        they will start. Curated phrases and fault names only.
        """
        def name(code: str) -> str:
            fault = kb.fault(code)
            return (fault.name_vi if fault else "").lower()

        lines: List[str] = []
        for code, exclusion in self.state.excluded.items():
            fault = name(code)
            if not fault:
                continue
            if exclusion.kind == "done":
                lines.append(f"Khách đã {exclusion.phrase_vi} rồi, đã loại {fault}.")
            elif exclusion.kind == "cause":
                lines.append(f"Khách cho biết không phải do {exclusion.phrase_vi} ({fault}).")
            elif exclusion.kind == "absent":
                lines.append(f"Khách cho biết {exclusion.phrase_vi}, đã loại {fault}.")
            else:
                lines.append(f"Khách bác khả năng {fault}.")
        for code, factor in self.state.boosts.items():
            if factor > 1.0 and code not in self.state.excluded and name(code):
                lines.append(f"Khách nghi {name(code)}.")
        tail: List[str] = list(self.code_notes[-2:])
        job = self.past_job()
        if job:
            line = f'Khách từng đặt "{job["service"]}" ngày {day_vi(job["date"])}'
            if job.get("fault"):
                line += f', khi đó trợ lý nghi {job["fault"].lower()}'
            tail.append(line + ".")
        if self.state.danger:
            tail.append("Khách có tả dấu hiệu nguy hiểm (khói, khét, chập, giật hoặc mùi gas).")
        return lines[: 6 - len(tail)] + tail

    def plain_facts_vi(self, kb) -> str:
        """The same facts as one plain sentence, with no codes and no headings.

        For the advisory prompt, where the facts sit beside the conversation:
        on the served model the coded lines ("ĐÃ LOẠI KETTLE_THERMOSTAT — ...")
        were copied into the customer's answer word for word. A sentence the
        model can follow is a sentence it has no reason to recite.
        """
        def name(code: str) -> str:
            fault = kb.fault(code)
            return (fault.name_vi if fault else "").lower()

        ruled = [name(c) for c in self.state.excluded if name(c)]
        suspected = [
            name(c) for c, f in self.state.boosts.items()
            if f > 1.0 and c not in self.state.excluded and name(c)
        ]
        nexts = [name(c) for c in self.state.persist if c not in self.state.excluded and name(c)]
        parts = []
        if ruled:
            parts.append("khách đã loại " + ", ".join(ruled[:4]))
        if suspected:
            parts.append("khách đang nghi " + ", ".join(suspected[:2]))
        if nexts:
            parts.append("nên nghĩ tới " + ", ".join(nexts[:3]))
        return ("Lưu ý: " + "; ".join(parts) + ".") if parts else ""

    def facts_vi(self, kb) -> List[str]:
        """What the whole conversation has established, for the model to read.

        The thread is shown to the model too, but a 3B model reading twelve
        turns does not reliably notice that turn three ruled something out. These
        lines say it once, plainly, next to the list it chooses from.
        """
        def name(code: str) -> str:
            fault = kb.fault(code)
            return fault.name_vi if fault else code

        lines: List[str] = []
        for code, exclusion in self.state.excluded.items():
            how = {
                "done": f"khách đã {exclusion.phrase_vi}",
                "cause": f"khách khẳng định không phải do {exclusion.phrase_vi}",
                "absent": f"khách nói {exclusion.phrase_vi}",
                "previous": "khách bác câu trả lời trước",
            }.get(exclusion.kind, "khách đã loại")
            lines.append(f"ĐÃ LOẠI {code} — {name(code)} ({how})")
        for code, factor in self.state.boosts.items():
            if factor > 1.0 and code not in self.state.excluded:
                lines.append(f"KHÁCH TỰ NGHI {code} — {name(code)}")
        for code, factor in self.state.persist.items():
            if code not in self.state.excluded:
                lines.append(f"NÊN KIỂM TRA TIẾP {code} — {name(code)} (cách sửa trước không ăn thua)")
        for code in self.state.from_codes:
            if code not in self.state.excluded:
                lines.append(f"MÁY BÁO MÃ LỖI chỉ tới {code} — {name(code)} (theo bảng mã của hãng)")
        for code, factor in self.state.penalties.items():
            if factor < 1.0 and code not in self.state.excluded:
                lines.append(f"ÍT KHẢ NĂNG {code} — {name(code)} (khách nói không có triệu chứng của nó)")
        return lines

    def this_turn_had_no_symptom(self) -> None:
        """Mark the newest customer turn as contributing nothing to retrieval."""
        for turn in reversed(self.turns):
            if turn.role == "customer":
                turn.carried_a_symptom = False
                return

    def remember_device(self, device_type: str, confidence: float, source_vi: str) -> None:
        self.device_type = device_type
        self.device_confidence = confidence
        self.device_source_vi = source_vi
        self.updated_at = time.time()

    def remember_questions(self, symptoms: List[str]) -> None:
        for symptom in symptoms:
            if symptom and symptom not in self.asked_symptoms:
                self.asked_symptoms.append(symptom)
        self.updated_at = time.time()


class ConversationStore:
    """In-memory sessions with a time-to-live."""

    def __init__(
        self,
        ttl_seconds: int = SESSION_TTL_SECONDS,
        max_sessions: int = MAX_SESSIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_sessions
        self._sessions: Dict[str, Conversation] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def get_or_create(self, session_id: Optional[str]) -> Conversation:
        """Return the conversation this id names, or start one and name it.

        An id the store does not know starts a fresh conversation — under a new
        id of the store's own making, never under the one that was sent. A
        client whose session expired mid-chat carries on with a shorter memory
        rather than receiving an error, which is the point; it just carries on
        under the id the reply hands back.

        Adopting the id that arrived was the obvious thing and it was wrong.
        The field is any string up to sixty-four characters, so two clients
        that both send "guest", or "1", or a user id the service has no way to
        authenticate, were handed the same conversation: one customer's
        appliance, symptoms and shortlist shown to another. Nothing today sends
        its own id — the web client starts at null and echoes back whatever it
        is given — so the cost of refusing is nothing and the risk of accepting
        does not scale down.

        Anything wiring a new client to this service should do the same: send
        no id on the first message, then send back whatever the reply carried.
        """
        self._evict_expired()
        if session_id:
            existing = self._sessions.get(session_id)
            if existing is not None:
                return existing

        new_id = uuid.uuid4().hex
        conversation = Conversation(session_id=new_id)
        self._sessions[new_id] = conversation
        self._evict_overflow()
        return conversation

    def lock(self, session_id: Optional[str]) -> asyncio.Lock:
        """One turn at a time per conversation.

        A double-tapped send, or a photo and a message fired together, would
        otherwise run two turns over the same conversation at once: both read
        the state, both append, and whichever finishes second decides what the
        conversation believes. A turn with no id yet has nobody to race with
        and gets a lock of its own.
        """
        if not session_id:
            return asyncio.Lock()
        existing = self._locks.get(session_id)
        if existing is None:
            existing = asyncio.Lock()
            self._locks[session_id] = existing
        return existing

    def resumed(self, conversation: Conversation, requested_id: Optional[str]) -> bool:
        """Whether this conversation was just started in place of one the
        client named and the store no longer holds."""
        return bool(requested_id) and requested_id != conversation.session_id and not conversation.turns

    def _evict_expired(self) -> None:
        cutoff = time.time() - self._ttl
        for key in [k for k, v in self._sessions.items() if v.updated_at < cutoff]:
            del self._sessions[key]
        self._drop_idle_locks()

    def _drop_idle_locks(self) -> None:
        for key in [k for k, lock in self._locks.items() if k not in self._sessions and not lock.locked()]:
            del self._locks[key]

    def _evict_overflow(self) -> None:
        """Drop the least recently used until the store is back within its cap.

        Losing a live conversation is bad; running the box out of memory takes
        every conversation at once, along with the model. So the oldest go, and
        their owners carry on with a shorter memory the same way an expiry
        leaves them.
        """
        if len(self._sessions) <= self._max:
            return
        by_age = sorted(self._sessions.items(), key=lambda kv: kv[1].updated_at)
        for key, _ in by_age[: len(self._sessions) - self._max]:
            del self._sessions[key]
        self._drop_idle_locks()

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._sessions)


_STORE: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    global _STORE
    if _STORE is None:
        _STORE = ConversationStore()
    return _STORE


def day_vi(iso_day: str) -> str:
    """2026-08-03 -> 03/08/2026, the way a Vietnamese customer writes a date."""
    parts = (iso_day or "").split("-")
    if len(parts) != 3:
        return iso_day
    year, month, day = parts
    return f"{day}/{month}/{year}"
