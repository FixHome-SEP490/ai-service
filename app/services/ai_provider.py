# app/services/ai_provider.py
"""Provider contract and factory.

The abstraction is kept for the reason it was introduced: endpoints depend on a
stable async contract, never on how a diagnosis is produced. What changed is the
set of implementations. The service no longer calls hosted Gemini or OpenAI
models; the self-hosted YOLOv8n plus Qwen2.5-VL pipeline is the only engine, and
a deterministic mock stands in for tests and CI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings
from app.schemas.chat import AnswerStatus, ChatRequest, ChatResponse
from app.schemas.diagnosis import (
    DetectedDevice,
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    Engine,
    EvidenceSource,
    PriceEstimate,
    RecommendedService,
    SuspectedFault,
    UrgencyLevel,
)


class AIProvider(ABC):
    """Every engine returns the same normalized contract."""

    @abstractmethod
    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        """Preliminary diagnosis from a description and optional images."""

    @abstractmethod
    async def answer(self, request: ChatRequest) -> ChatResponse:
        """Grounded advisory answer. Never a booking recommendation."""


class MockAIProvider(AIProvider):
    """Fixed output for deterministic tests and offline local runs."""

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        return DiagnosisResponse(
            request_id=request.request_id,
            status=DiagnosisStatus.OK,
            engine=Engine.MOCK,
            device=DetectedDevice(
                device_type="electric_fan",
                name_vi="Quạt điện",
                confidence=0.9,
                source=EvidenceSource.IMAGE,
            ),
            suspected_faults=[
                SuspectedFault(
                    fault_code="FAN_WORN_BEARING",
                    name_vi="Khô bạc đạn, mòn bạc trục",
                    confidence=0.72,
                    source=EvidenceSource.DESCRIPTION,
                )
            ],
            recommended_services=[
                RecommendedService(
                    service_code="SVC_FAN_BEARING",
                    name_vi="Tra dầu và thay bạc đạn",
                )
            ],
            suggested_actions_vi=["Ngưng dùng để tránh kẹt trục làm cháy mô tơ"],
            price_estimate=PriceEstimate(min=120000, max=250000),
            urgency=UrgencyLevel.LOW,
            confidence=0.81,
            is_low_confidence=False,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def answer(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            request_id=request.request_id,
            status=AnswerStatus.OK,
            answer_vi="Nội dung trả lời giả lập dùng cho kiểm thử.",
            confidence=0.7,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )


class LocalPipelineProvider(AIProvider):
    """Adapter exposing the self-hosted pipeline through the provider contract."""

    def __init__(self) -> None:
        from app.services.pipeline.detector import StubDetector, YoloDetector
        from app.services.pipeline.knowledge_base import get_knowledge_base
        from app.services.pipeline.local_pipeline import LocalPipeline
        from app.services.pipeline.retriever import Retriever
        from app.services.pipeline.vlm import QwenVlm, StubVlm

        kb = get_knowledge_base()
        detector = (
            YoloDetector(
                weights_path=settings.YOLO_WEIGHTS_PATH,
                kb=kb,
                min_confidence=settings.DETECTOR_CONFIDENCE_THRESHOLD,
            )
            if settings.YOLO_WEIGHTS_PATH
            else StubDetector(kb=kb)
        )
        vlm = (
            QwenVlm(
                base_url=settings.VLM_BASE_URL,
                model_name=settings.VLM_MODEL_NAME,
                timeout_seconds=settings.VLM_TIMEOUT_SECONDS,
                api_key=settings.VLM_API_KEY or None,
            )
            if settings.VLM_BASE_URL
            else StubVlm()
        )
        self._pipeline = LocalPipeline(
            detector=detector,
            vlm=vlm,
            retriever=Retriever(kb),
            kb=kb,
        )

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        return await self._pipeline.diagnose(request)

    async def answer(self, request: ChatRequest) -> ChatResponse:
        return await self._pipeline.answer(request)


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Cached so model handles and the knowledge base load once per process."""
    if settings.AI_ENGINE.lower() == "mock":
        return MockAIProvider()
    return LocalPipelineProvider()
