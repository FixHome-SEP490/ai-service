# app/services/pipeline/context.py
"""Gathers everything Qwen is allowed to reason from, and nothing else.

This is the part that decides what the model knows. Qwen has no memory, no
database and no access to the photograph beyond the crop handed to it: whatever
is not assembled here does not exist as far as the answer is concerned. So the
quality of an answer is mostly the quality of this bundle, and a model that
looks stupid is usually a model that was told very little.

What went in before was a list of fault codes. That is why the assistant read
like a lookup table: it was one. A customer asking "giờ tôi nên thuê dịch vụ
nào" in the fourth message of a thread had the fourth message assembled and the
first three thrown away.

Six things go in now.

    the appliance, and how it came to be known — a photograph, the customer's
    own words, or an earlier turn

    everything the customer has said, in order, because symptoms arrive spread
    across messages

    what has already been asked, so the same question is not put twice

    the candidate faults retrieval shortlisted, with the phrases customers use
    for each, so the model is matching language against language

    the policy passages that bear on this device

    the labour and parts rows that price it

Assembly is separate from the prompt on purpose. The prompt is wording and
changes often; this is the decision about what the model may see, which is a
different thing and worth being able to read on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from app.services.pipeline.conversation import Conversation
from app.services.pipeline.knowledge_base import KnowledgeBase, PriceRow
from app.services.pipeline.retriever import (
    Retriever,
    ScoredChunk,
    ScoredFault,
    ScoredPolicy,
)

MAX_HISTORY_TURNS = 8
"""Turns of dialogue handed over.

Enough for a customer to have been asked two questions and answered them, with
room for the message that started it. Beyond that the early turns are usually
the same symptoms in weaker words, and they crowd out the shortlist.
"""

MAX_POLICIES = 2
MAX_PRICE_ROWS = 6


@dataclass(frozen=True)
class DiagnosisContext:
    """Everything the model may use for one turn."""

    device_type: Optional[str]
    device_name_vi: Optional[str]
    device_source_vi: Optional[str]
    """"ảnh", "lời khách" or "lượt trước" — so the prompt can say how it knows."""

    said_so_far: str
    latest_message: str
    history: List[str] = field(default_factory=list)
    already_asked: List[str] = field(default_factory=list)
    candidates: List[ScoredFault] = field(default_factory=list)
    policies: List[ScoredPolicy] = field(default_factory=list)
    price_rows: List[PriceRow] = field(default_factory=list)
    has_image: bool = False
    safety: List[ScoredChunk] = field(default_factory=list)
    """Sections that must be said before diagnosing. Pinned, never ranked."""

    passages: List[ScoredChunk] = field(default_factory=list)
    """Written prose about this appliance: mechanism, what to check, what to say.

    The corpus is what separates an answer from a lookup. Without it the model
    had the fault's name, the phrases customers use for it, and a price — enough
    to classify, nothing to explain with. "Vì sao dàn lạnh bám tuyết" had no
    answer in the bundle at all, so the only honest reply was a question."""

    business: List[ScoredChunk] = field(default_factory=list)
    """Booking, pricing model, warranty. Retrieved apart so a fault question
    cannot spend its budget on the booking flow, or the reverse."""

    def is_empty(self) -> bool:
        """Nothing retrieved at all: asking beats guessing."""
        return not self.candidates


_SOURCE_VI = {
    "image": "ảnh khách gửi",
    "description": "lời khách kể",
    "memory": "lượt trước trong cuộc trò chuyện",
}


def build(
    kb: KnowledgeBase,
    retriever: Retriever,
    chat: Conversation,
    latest_message: str,
    device_type: Optional[str],
    device_source: Optional[str],
    candidates: Sequence[ScoredFault],
    has_image: bool,
    top_k_policies: int = MAX_POLICIES,
) -> DiagnosisContext:
    """Assemble the bundle for this turn.

    Policies and price rows are looked up against everything said rather than
    the latest message alone. A customer who described the fault in message one
    and asked what it costs in message three needs both, and neither message
    carries the other's half.
    """
    said = chat.customer_text() or latest_message

    policies = retriever.policy_passages(said, top_k=top_k_policies)
    prices: List[PriceRow] = []
    if device_type:
        # The device narrows this far more sharply than any wording does.
        # Without it, 809 rows of similar names compete on shared words.
        by_code = {row.code: row for row in kb.price_rows}
        for candidate in candidates[:3]:
            fault = candidate.fault
            labour = kb.labour_row(fault.labour_code)
            if labour is not None and labour not in prices:
                prices.append(labour)
            for code in fault.part_codes:
                row = by_code.get(code)
                if row is not None and row not in prices:
                    prices.append(row)

    history = [
        f"{'Khách' if turn.role == 'customer' else 'Em'}: {turn.text_vi}"
        for turn in chat.turns[-MAX_HISTORY_TURNS:]
    ]

    # Written prose, in three parts that must not compete for the same budget.
    #
    # Safety first and unranked: a section that has to be said before anything
    # else cannot be asked to win on wording, and measured on the gas leak it
    # loses — it is written as instructions, so it repeats the customer's words
    # least of any section in the file.
    #
    # Then the ranked passages, told which sections were already pinned so the
    # same text is not handed over twice.
    #
    # Business last and only when the question reaches for it.
    codes = [c.fault.fault_code for c in candidates]
    safety = retriever.safety_passages(codes)
    pinned = [f"{s.chunk.source_file}::{s.chunk.heading_vi}" for s in safety]
    passages = retriever.corpus_passages(
        said, device_type=device_type, fault_codes=codes, exclude=pinned
    )
    business = retriever.business_passages(said)

    return DiagnosisContext(
        device_type=device_type,
        device_name_vi=kb.device_name_vi(device_type) if device_type else None,
        device_source_vi=_SOURCE_VI.get(device_source or "", None),
        said_so_far=said,
        latest_message=latest_message,
        history=history,
        already_asked=list(chat.asked_symptoms),
        candidates=list(candidates),
        policies=policies,
        price_rows=prices[:MAX_PRICE_ROWS],
        has_image=has_image,
        safety=safety,
        passages=passages,
        business=business,
    )
