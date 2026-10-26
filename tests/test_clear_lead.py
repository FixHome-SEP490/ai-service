"""A report with one fault well ahead is diagnosed, whatever confidence the model reports.

On the served model, 26/10/2026, sixteen chat-suite reports such as "quạt
điện quạt khô dầu" were asked back: retrieval had one fault far ahead, short
of the decisive score, and the model reported a confidence under the
threshold.
"""

import asyncio

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm, VlmVerdict

KB = get_knowledge_base()


class _Unsure(StubVlm):
    """Chooses the first candidate, at a confidence under the threshold."""

    async def assess(self, crop, description, device_type, candidates, candidate_condition_codes):
        return VlmVerdict(fault_codes=[candidates[0].code] if candidates else [], confidence=0.35)

    async def assess_context(self, crop, context, candidate_condition_codes):
        return VlmVerdict(fault_codes=[context.candidates[0].fault.fault_code] if context.candidates else [], confidence=0.35)


class _NoDetector:
    async def detect(self, image):
        return []


def _diagnose(text):
    sc.install(sc.LiveCatalog())
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=_Unsure(), retriever=Retriever(KB), kb=KB)
    return asyncio.run(pipeline.diagnose(DiagnosisRequest(description=text)))


def test_one_fault_well_ahead_is_diagnosed():
    for text, code in (
        ("quạt điện quạt khô dầu", "FAN_WORN_BEARING"),
        ("quạt điện quạt không tuốc năng", "FAN_OSCILLATION_FAULT"),
        ("quạt điện quạt phải lấy tay quay mới chạy", "FAN_CAPACITOR"),
        ("bóng đèn cái nút bật đèn liệt rồi", "LIGHT_SWITCH_FAULT"),
    ):
        reply = _diagnose(text)
        assert reply.status.value == "ok", text
        assert reply.suspected_faults and reply.suspected_faults[0].fault_code == code, text


def test_a_tie_is_still_asked():
    reply = _diagnose("tivi bị đơ")
    assert reply.status.value == "needs_clarification"
