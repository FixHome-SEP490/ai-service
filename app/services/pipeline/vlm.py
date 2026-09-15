# app/services/pipeline/vlm.py
"""Vision-language stage.

Qwen2.5-VL receives the cropped device region, the customer's Vietnamese
description, the device type the detector already settled, and a shortlist of
candidate fault codes from retrieval. It does three things the detector cannot:
reads surface damage off the image (cracks, burn marks, rust, wear), reasons
about the description in context rather than by keyword, and picks fault codes
from the shortlist.

It returns codes only. Vietnamese wording, service codes and prices are looked
up from the knowledge base afterwards, which is what keeps the output free of
invented content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Tuple

from app.services.pipeline.images import ImagePayload


@dataclass(frozen=True)
class FaultCandidate:
    """One option on the shortlist, with enough context to judge it.

    Sending bare codes made the model guess: `AC_LOW_REFRIGERANT` carries no
    information about what that fault looks like, so it had nothing to compare
    the customer's words against and was effectively picking from a list of
    opaque strings. The name and the symptoms are what make it a decision.
    """

    code: str
    name_vi: str
    symptoms_vi: List[str]
    retrieval_score: float = 0.0
    """How well the description already matched, so the model knows what
    retrieval thought before it looks at the photograph."""


@dataclass(frozen=True)
class VlmVerdict:
    fault_codes: List[str] = field(default_factory=list)
    condition_codes: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_vi: Optional[str] = None
    """Kept for logging and report analysis; never returned to customers."""


class VisionLanguageModel(Protocol):
    async def assess(
        self,
        crop: Optional[ImagePayload],
        description: str,
        device_type: Optional[str],
        candidates: List[FaultCandidate],
        candidate_condition_codes: List[Tuple[str, str]],
    ) -> VlmVerdict:
        ...

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        """Answer a grounded advisory question from retrieved passages."""
        ...


class StubVlm:
    """Picks the top retrieved candidate. Deterministic, no weights needed."""

    async def assess(
        self,
        crop: Optional[ImagePayload],
        description: str,
        device_type: Optional[str],
        candidates: List[FaultCandidate],
        candidate_condition_codes: List[Tuple[str, str]],
    ) -> VlmVerdict:
        return VlmVerdict(
            fault_codes=[c.code for c in candidates][:2],
            condition_codes=[],
            confidence=0.72 if candidates else 0.0,
        )

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        if not passages_vi:
            return "", 0.0
        return passages_vi[0], 0.6


class QwenVlm:
    """Qwen2.5-VL-3B-Instruct AWQ served through vLLM.

    A thin wrapper so the pipeline keeps depending on the protocol above rather
    than on an HTTP client. The request building, validation and failure
    handling live in `qwen_client`.
    """

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        api_key: Optional[str] = None,
    ) -> None:
        from app.services.pipeline.qwen_client import QwenClient

        self._client = QwenClient(
            base_url=base_url,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            api_key=api_key,
        )

    async def assess(
        self,
        crop: Optional[ImagePayload],
        description: str,
        device_type: Optional[str],
        candidates: List[FaultCandidate],
        candidate_condition_codes: List[Tuple[str, str]],
    ) -> VlmVerdict:
        return await self._client.assess(
            crop=crop,
            description=description,
            device_type=device_type,
            candidates=candidates,
            candidate_condition_codes=candidate_condition_codes,
        )

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        return await self._client.answer(question, passages_vi)
