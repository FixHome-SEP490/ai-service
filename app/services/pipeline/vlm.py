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
from typing import List, Optional, Protocol


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
        crop_ref: Optional[str],
        description: str,
        device_type: Optional[str],
        candidate_fault_codes: List[str],
        candidate_condition_codes: List[str],
    ) -> VlmVerdict:
        ...

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        """Answer a grounded advisory question from retrieved passages."""
        ...


class StubVlm:
    """Picks the top retrieved candidate. Deterministic, no weights needed."""

    async def assess(
        self,
        crop_ref: Optional[str],
        description: str,
        device_type: Optional[str],
        candidate_fault_codes: List[str],
        candidate_condition_codes: List[str],
    ) -> VlmVerdict:
        return VlmVerdict(
            fault_codes=candidate_fault_codes[:2],
            condition_codes=[],
            confidence=0.72 if candidate_fault_codes else 0.0,
        )

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        if not passages_vi:
            return "", 0.0
        return passages_vi[0], 0.6


class QwenVlm:
    """Qwen2.5-VL-3B-Instruct AWQ served through vLLM.

    Sampling is deterministic (temperature 0) so the same photo and description
    always produce the same result, which is what makes the fixed regression set
    meaningful. Generation is constrained to the candidate codes supplied by the
    caller, so the model cannot name a device or fault outside the catalog.
    """

    def __init__(self, base_url: str, model_name: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds

    async def assess(
        self,
        crop_ref: Optional[str],
        description: str,
        device_type: Optional[str],
        candidate_fault_codes: List[str],
        candidate_condition_codes: List[str],
    ) -> VlmVerdict:
        raise NotImplementedError(
            "QwenVlm requires a running vLLM endpoint; see docs/AI-TECHNICAL-GUIDE.md"
        )

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        raise NotImplementedError(
            "QwenVlm requires a running vLLM endpoint; see docs/AI-TECHNICAL-GUIDE.md"
        )
