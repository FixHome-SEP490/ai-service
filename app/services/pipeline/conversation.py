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

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

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


@dataclass
class Turn:
    role: str
    """"customer" or "assistant"."""

    text_vi: str
    at: float = field(default_factory=time.time)


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

    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._sessions: Dict[str, Conversation] = {}

    def get_or_create(self, session_id: Optional[str]) -> Conversation:
        """Return the named conversation, or start one.

        An unknown id starts a fresh conversation under that same id rather
        than raising. A client whose session expired mid-chat should carry on
        with a shorter memory, not receive an error in place of an answer.
        """
        self._evict_expired()
        if session_id:
            existing = self._sessions.get(session_id)
            if existing is not None:
                return existing
        new_id = session_id or uuid.uuid4().hex
        conversation = Conversation(session_id=new_id)
        self._sessions[new_id] = conversation
        return conversation

    def _evict_expired(self) -> None:
        cutoff = time.time() - self._ttl
        for key in [k for k, v in self._sessions.items() if v.updated_at < cutoff]:
            del self._sessions[key]

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._sessions)


_STORE: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    global _STORE
    if _STORE is None:
        _STORE = ConversationStore()
    return _STORE
