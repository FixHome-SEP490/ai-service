# app/services/pipeline/local_pipeline.py
"""Orchestrates detector, retrieval, VLM and knowledge-base lookup."""

from __future__ import annotations

from typing import List, Optional

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
    EvidenceSource,
    PriceEstimate,
    RecommendedService,
    SuspectedFault,
    UrgencyLevel,
    VisibleCondition,
)
from app.services.pipeline import clarifier
from app.services.pipeline import device_hint
from app.services.pipeline.detector import Detection, Detector
from app.services.pipeline.images import ImagePayload, load_base64_image
from app.services.pipeline.knowledge_base import KnowledgeBase
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import FaultCandidate, VisionLanguageModel, VlmVerdict

_URGENCY_RANK = {UrgencyLevel.LOW: 0, UrgencyLevel.MEDIUM: 1, UrgencyLevel.HIGH: 2}


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

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        detection = await self._detect_primary(request.images)
        detected = detection.device_type if detection else None
        # The photograph is ambiguous between a microwave and an oven; a
        # sentence saying "lò vi sóng" is not. Believe the words.
        device_type, _hint = device_hint.resolve(
            request.description, detected, self._kb
        )

        candidates = self._retriever.candidate_faults(
            description=request.description,
            device_type=device_type,
            top_k=settings.RETRIEVAL_TOP_K,
        )
        verdict = await self._vlm.assess(
            crop=detection.crop if detection else None,
            description=request.description,
            device_type=device_type,
            candidates=[
                FaultCandidate(
                    code=c.fault.fault_code,
                    name_vi=c.fault.name_vi,
                    symptoms_vi=c.fault.symptoms_vi,
                    retrieval_score=c.score,
                )
                for c in candidates
            ],
            candidate_condition_codes=[
                (code, self._kb.condition_name_vi(code) or code)
                for code in self._kb.condition_codes
            ],
        )

        confidence = self._combine_confidence(detection, verdict.confidence)
        shortlist = [c.fault for c in candidates]
        if confidence < settings.AI_CONFIDENCE_THRESHOLD:
            return self._clarification_response(
                request, confidence, shortlist, detection
            )

        return self._build_response(
            request, detection, verdict, confidence, shortlist
        )

    async def answer(self, request: ChatRequest) -> ChatResponse:
        """Advisory Q&A, grounded in retrieved policy passages.

        Kept separate from diagnosis: it may discuss maintenance intervals and
        platform policy, but it never recommends a service or a booking.
        """
        passages = self._retriever.policy_passages(
            request.question, top_k=settings.RETRIEVAL_TOP_K
        )
        if not passages:
            return self._ungrounded_answer(request)

        answer_vi, confidence = await self._vlm.answer(
            question=request.question,
            passages_vi=[p.policy.content_vi for p in passages],
        )
        if not answer_vi:
            return self._ungrounded_answer(request)

        return ChatResponse(
            request_id=request.request_id,
            status=AnswerStatus.OK,
            answer_vi=answer_vi,
            citations=[
                Citation(
                    doc_id=p.policy.doc_id,
                    title_vi=p.policy.title_vi,
                    score=round(min(p.score, 1.0), 4),
                )
                for p in passages
            ],
            confidence=confidence,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _ungrounded_answer(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            request_id=request.request_id,
            status=AnswerStatus.NO_GROUNDING,
            answer_vi=settings.NO_GROUNDING_MESSAGE_VI,
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

    def _clarification_response(
        self,
        request: DiagnosisRequest,
        confidence: float,
        shortlist: Optional[List] = None,
        detection: Optional[Detection] = None,
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
        questions = clarifier.texts(
            clarifier.build_questions(
                shortlist or [],
                request.description,
                discriminators=self._kb.discriminators_for_device(
                    detection.device_type if detection else None
                ),
            )
        ) or clarifier.device_questions(device_name)

        # One question about which device it is, and only when the customer has
        # not already said. Asking what was just written is how a support bot
        # starts feeling like it is not listening.
        confusion = device_hint.confusion_question(
            detection.device_type if detection else None,
            request.description,
            self._kb,
        )
        if confusion and confusion not in questions:
            questions = [confusion, *questions][: clarifier.MAX_QUESTIONS]

        return DiagnosisResponse(
            request_id=request.request_id,
            status=DiagnosisStatus.NEEDS_CLARIFICATION,
            engine=Engine.LOCAL_PIPELINE,
            device=self._resolve_device(detection),
            confidence=confidence,
            is_low_confidence=True,
            clarification=Clarification(
                questions_vi=questions,
                service_group_codes=self._kb.all_service_groups(),
            ),
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _build_response(
        self,
        request: DiagnosisRequest,
        detection: Optional[Detection],
        verdict: VlmVerdict,
        confidence: float,
        shortlist: Optional[List] = None,
    ) -> DiagnosisResponse:
        device = self._resolve_device(detection)

        faults: List[SuspectedFault] = []
        services: List[RecommendedService] = []
        actions: List[str] = []
        price_min: Optional[int] = None
        price_max: Optional[int] = None
        urgency = UrgencyLevel.LOW

        for code in verdict.fault_codes:
            fault = self._kb.fault(code)
            if fault is None:
                continue  # model named a code outside the catalog; drop it
            faults.append(
                SuspectedFault(
                    fault_code=fault.fault_code,
                    name_vi=fault.name_vi,
                    confidence=verdict.confidence,
                    source=EvidenceSource.DESCRIPTION,
                )
            )
            for ref in self._kb.services_for_fault(fault.fault_code):
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
            fault_urgency = UrgencyLevel(fault.urgency)
            if _URGENCY_RANK[fault_urgency] > _URGENCY_RANK[urgency]:
                urgency = fault_urgency

        if not faults:
            return self._clarification_response(
                request, confidence, shortlist, detection
            )

        return DiagnosisResponse(
            request_id=request.request_id,
            status=DiagnosisStatus.OK,
            engine=Engine.LOCAL_PIPELINE,
            device=device,
            visible_conditions=self._resolve_conditions(verdict),
            suspected_faults=faults,
            recommended_services=services,
            suggested_actions_vi=actions,
            price_estimate=PriceEstimate(min=price_min or 0, max=price_max or 0),
            urgency=urgency,
            confidence=confidence,
            is_low_confidence=False,
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    def _resolve_device(self, detection: Optional[Detection]) -> Optional[DetectedDevice]:
        if detection is None:
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
