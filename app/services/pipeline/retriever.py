# app/services/pipeline/retriever.py
"""Retrieval over the knowledge base.

Two jobs. For diagnosis it narrows the candidate faults handed to the VLM, so
the model chooses from a short grounded list instead of inventing one. For the
advisory chatbot it retrieves policy passages that answers must cite.

The default implementation is lexical and dependency-free so CI stays fast and
deterministic. Swapping in sentence embeddings means implementing the same two
methods; nothing else in the pipeline changes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.core.config import settings
from app.services.pipeline.knowledge_base import Fault, KnowledgeBase, Policy

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Vietnamese function words, written without diacritics because tokens are
# stripped before matching. Without this, "hư rồi" scores half a point against
# "kêu to rồi tắt" purely on the filler word, and a customer writing "máy lạnh
# hư rồi không biết sao" gets a confident diagnosis built on nothing.
_STOPWORDS = frozenset(
    """
    la co khong chua da dang se bi duoc cua va voi thi ma nhung nen roi
    o tai tu den cho khi luc nay do kia ay nao gi sao vay the nhu
    toi minh em anh chi ban nha a oi u um vang da
    mot hai ba cac nhung moi tung deu ca het rat qua lam hoi
    ra vao len xuong di ve lai nua con chi moi vua
    xin nho giup hoi sua kiem tra xem nao
    """.split()
)


def _content_tokens(tokens: List[str]) -> List[str]:
    """Drop filler words, but never return an empty list.

    A query made entirely of stopwords still has to score something rather than
    crash or match everything; returning the original tokens leaves the caller
    to decide, and zero-overlap filtering handles it downstream.
    """
    kept = [t for t in tokens if t not in _STOPWORDS]
    return kept or tokens


def _normalize(text: str) -> List[str]:
    """Lowercase, strip Vietnamese diacritics, tokenize.

    Diacritics are dropped so that a customer typing without tone marks still
    matches the curated symptom phrasing.
    """
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    stripped = stripped.replace("\u0111", "d")
    return _TOKEN_RE.findall(stripped)


@dataclass(frozen=True)
class ScoredFault:
    fault: Fault
    score: float


@dataclass(frozen=True)
class ScoredPolicy:
    policy: Policy
    score: float


def _overlap_score(query_tokens: List[str], target: str) -> float:
    target_tokens = set(_content_tokens(_normalize(target)))
    query_tokens = _content_tokens(query_tokens)
    if not target_tokens or not query_tokens:
        return 0.0
    hits = sum(1 for t in set(query_tokens) if t in target_tokens)
    return hits / len(set(query_tokens))


_PRICE_NOISE = {
    "gia", "tien", "bao", "nhieu", "tinh", "het", "cost", "ban", "minh", "sao",
    "the", "nao", "khoang", "chi", "phi", "ben",
}
"""Words in every price question, which match nothing and dilute everything.

"dây điện thay bên mình tính giá sao" is eight tokens of which two say what is
being asked about. Dividing by all eight put the right row under any usable
threshold."""


def _price_score(
    query_tokens: List[str], row_name: str, alias_tokens: Sequence[str] = ()
) -> float:
    """Balance how much of the row the question covers against how much of the
    question the row explains.

    Each direction alone picks a different wrong answer. Dividing by the
    question, as policy retrieval does, buries every short row under a long
    sentence. Dividing by the row rewards the shortest rows: expanded with the
    device's aliases, "thay ổ cắm hết bao nhiêu tiền" covered every word of
    "Công tắc cửa" and scored it a perfect match.
    """
    target = set(_content_tokens(_normalize(row_name)))
    query = {t for t in _content_tokens(query_tokens) if t not in _PRICE_NOISE}
    if not target or not query:
        return 0.0

    # Aliases widen what counts as a hit without widening the question. They
    # are the team's words for a device, not the customer's, so charging the
    # question for their length punishes it for a synonym it never used:
    # "thay block máy lạnh" fell below the floor once six air-conditioner
    # aliases had been added to its denominator.
    alias = {t for t in _content_tokens(list(alias_tokens))} - query

    # The customer's own words count double. Six aliases of "máy lạnh" made
    # every air-conditioner part match as strongly as the cleaning service the
    # question actually named, and "công tắc ổ cắm" — a legitimate alias of a
    # socket — put a door switch above the socket row.
    hits = sum(1 for t in target if t in query) + 0.5 * sum(
        1 for t in target if t in alias
    )
    if not hits:
        return 0.0

    # Recall, deliberately. Tuning this into a precise ranker meant chasing one
    # wrong answer after another: dividing by the question buried short rows,
    # dividing by the row crowned the shortest ones, and balancing the two put
    # "Công tắc cửa" at the top for a question about a socket. Lexical overlap
    # on two-word names cannot tell a near miss from a match.
    #
    # So it gathers candidates rather than choosing one, and Qwen chooses among
    # them — the same division of labour as the fault shortlist, where it
    # works. Nothing outside these rows can reach the customer either way.
    return hits / len(target)


def _device_alias_tokens(question: str, kb: KnowledgeBase) -> List[str]:
    """Add what the team calls a device to what the customer calls it.

    The labour table says "điều hòa" and customers say "máy lạnh", so "vệ sinh
    máy lạnh giá bao nhiêu" matched the water heater row and not one of the
    three air-conditioner cleaning rows sitting right there.
    """
    from app.services.pipeline import device_hint

    extra: List[str] = []
    for hint in device_hint.devices_named_in(question, kb):
        for alias in kb.aliases_vi(hint.device_type):
            extra.extend(_normalize(alias))
        name = kb.device_name_vi(hint.device_type)
        if name:
            extra.extend(_normalize(name))
    return extra


class Retriever:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def candidate_faults(
        self,
        description: str,
        device_type: Optional[str],
        top_k: int = 5,
    ) -> List[ScoredFault]:
        """Rank faults by symptom overlap, restricted to the detected device.

        Restricting by device is what makes the detector worth its cost: it cuts
        the candidate space before the VLM ever sees it.
        """
        pool = (
            self._kb.faults_for_device(device_type)
            if device_type
            else [f for d in self._kb.device_types for f in self._kb.faults_for_device(d)]
        )
        tokens = _normalize(description)
        scored = [
            ScoredFault(fault=f, score=_overlap_score(tokens, " ".join(f.symptoms_vi)))
            for f in pool
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        # Drop zero-overlap faults. Handing the VLM every fault of a device
        # whenever the description says nothing useful invites a confident
        # guess; an empty shortlist correctly ends in a clarification instead.
        return [s for s in scored[:top_k] if s.score > 0.0]

    def content_words(self, text: str) -> int:
        """How many words carry meaning, once function words are dropped.

        A high retrieval score means nothing on its own: the score divides by
        the query's own length, so "hư rồi" matches some symptom perfectly and
        scores 1.00. Counting what the customer actually described separates a
        precise sentence from a shrug.
        """
        return len(_content_tokens(_normalize(text)))

    def price_passages(self, question: str, top_k: int = 10) -> List[ScoredPolicy]:
        """Lines from the labour and parts tables that match what was asked.

        Returned as passages so they travel the same path as policy text: the
        model may restate them and nothing else, which keeps a figure on screen
        traceable to a row somebody in the team owns.

        A lower floor than policy text on purpose. A price row is one short
        line — "Thay ổ cắm điện, tiền công" — so a question shares far less of
        it than of a paragraph, and the policy threshold hid every one of them.
        """
        tokens = _normalize(question)
        if not tokens:
            return []

        # Narrow to the device first, exactly as the fault shortlist does.
        # Ranking all 809 rows at once was the mistake: their names share so
        # much vocabulary that "vệ sinh máy lạnh giá bao nhiêu" ranked a relay,
        # a fridge hinge and refrigeration oil above the air-conditioner
        # cleaning service it had named outright. Within one device the
        # remaining rows are few and the overlap means something again.
        from app.services.pipeline import device_hint

        named = device_hint.devices_named_in(question, self._kb)
        wanted = {hint.device_type for hint in named}
        rows = self._kb.price_rows
        if wanted:
            narrowed = [r for r in rows if wanted & set(r.device_types)]
            if narrowed:
                rows = narrowed

        aliases = _device_alias_tokens(question, self._kb)
        scored = [
            ScoredPolicy(
                policy=Policy(
                    doc_id=row.code, title_vi=row.name_vi, content_vi=row.as_text_vi()
                ),
                score=_price_score(tokens, row.name_vi, aliases),
            )
            for row in rows
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= settings.PRICE_MIN_SCORE]

    def policy_passages(
        self, question: str, top_k: int = 3, min_score: Optional[float] = None
    ) -> List[ScoredPolicy]:
        """Passages that actually cover the question, or nothing.

        The floor is the whole point. Lexical overlap scores every question
        against every passage, so a question about the weather still retrieves
        the air-conditioner maintenance policy on the word it shares. Returning
        that leaves the model as the only thing preventing an invented answer.
        """
        threshold = settings.POLICY_MIN_SCORE if min_score is None else min_score
        tokens = _normalize(question)
        scored = [
            ScoredPolicy(
                policy=p,
                score=_overlap_score(tokens, f"{p.title_vi} {p.content_vi}"),
            )
            for p in self._kb.policies
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= threshold]
