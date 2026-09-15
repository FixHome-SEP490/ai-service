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
from typing import List, Optional

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
