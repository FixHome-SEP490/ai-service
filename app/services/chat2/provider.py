"""The chat brain behind the existing endpoints, without changing what Backend receives.

/diagnosis/analyze and /chat/ask keep their request and response schemas. The
detector still reads every photograph and names the appliance; the chat model
never sees an image. Conversation turns live here per session and travel in
`diagnostic_state`, so Backend, which already stores that field, can hand a
conversation back after a restart.

A question about price, warranty or how FixHome works is answered from the
policy passages, shortly and with citations. Everything about an appliance goes
through the brain, whichever endpoint it arrived on, because the client cannot
tell a question from a report ("máy lạnh chảy nước là sao vậy?").
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.exceptions import AITimeoutException, VlmException
from app.schemas.chat import AnswerStatus, ChatRequest, ChatResponse, Citation
from app.schemas.diagnosis import (
    Clarification,
    DetectedDevice,
    DeviceSuggestion,
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    EvidenceSource,
    ModelInfo,
    PhotoReading,
    RecommendedService,
    SuspectedFault,
    UrgencyLevel,
)
from app.services.ai_provider import AIProvider
from app.services.chat2.brain import ChatBrain, Turn, Verdict
from app.services.chat2.menu import devices, menu_for
from app.services.pipeline import pricing

logger = logging.getLogger(__name__)

STATE_VERSION = "chat2.1"
MAX_TURNS = 40
MAX_SESSIONS = 5000
IDLE_SECONDS = 3600


@dataclass
class Session:
    session_id: str
    turns: List[Turn] = field(default_factory=list)
    photo_device: Optional[str] = None
    photo_confidence: float = 0.0
    device: Optional[str] = None
    """The appliance the conversation settled on, by photograph or by name."""
    version: int = 0
    seen: float = field(default_factory=time.time)

    def export(self) -> dict:
        return {
            "engine": STATE_VERSION,
            "turns": [{"role": t.role, "text": t.text} for t in self.turns[-MAX_TURNS:]],
            "photo_device": self.photo_device,
            "photo_confidence": self.photo_confidence,
            "device": self.device,
            # Backend keeps a state only over an older version, so the count
            # must survive a restart or every later state is thrown away.
            "version": self.version,
        }


class Sessions:
    """Server-issued ids only: a client sending "guest" never joins someone else's chat."""

    def __init__(self) -> None:
        self._items: "OrderedDict[str, Session]" = OrderedDict()

    def get(self, session_id: Optional[str], state: Optional[dict], history: List[str]) -> Session:
        now = time.time()
        for sid in [k for k, v in self._items.items() if now - v.seen > IDLE_SECONDS]:
            del self._items[sid]
        if session_id and session_id in self._items:
            session = self._items.pop(session_id)
        else:
            session = Session(session_id or uuid.uuid4().hex)
            if state and state.get("engine") == STATE_VERSION:
                session.turns = [Turn(t["role"], t["text"]) for t in state.get("turns") or [] if t.get("text")]
                photo = state.get("photo_device")
                session.photo_device = photo if photo in devices() else None
                session.photo_confidence = float(state.get("photo_confidence") or 0.0)
                session.version = int(state.get("version") or len(session.turns))
                known = state.get("device")
                session.device = known if known in devices() else session.photo_device
            elif history:
                session.turns = [Turn("user", h) for h in history if h.strip()]
        session.seen = now
        self._items[session.session_id] = session
        while len(self._items) > MAX_SESSIONS:
            self._items.popitem(last=False)
        return session


ANSWER_SYSTEM = """Bạn là trợ lý của FixHome (dịch vụ sửa chữa, vệ sinh, lắp đặt đồ gia dụng tại nhà). Xưng "em", gọi khách là "anh/chị".
Trả lời câu hỏi của khách CHỈ dựa vào các đoạn chính sách dưới đây, tối đa hai câu ngắn. Không có trong các đoạn thì nói em chưa có thông tin đó và mời khách nhắn tổng đài. Không bịa số tiền, thời hạn hay điều khoản.

{passages}"""


def _base_url() -> str:
    base = settings.VLM_BASE_URL.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def _extra_body() -> dict:
    # Qwen3.x thinks out loud by default; for a chat reply that is seconds of
    # latency spent on text nobody reads.
    return {"chat_template_kwargs": {"enable_thinking": False}} if settings.CHAT_DISABLE_THINKING else {}


class Chat2Provider(AIProvider):
    def __init__(self, detector=None, brain: Optional[ChatBrain] = None, transport=None) -> None:
        from app.services.pipeline.detector import StubDetector, YoloDetector
        from app.services.pipeline.knowledge_base import get_knowledge_base
        from app.services.pipeline.retriever import Retriever

        self._kb = get_knowledge_base()
        self._detector = detector or (
            YoloDetector(
                weights_path=settings.YOLO_WEIGHTS_PATH,
                kb=self._kb,
                min_confidence=settings.DETECTOR_CONFIDENCE_THRESHOLD,
            )
            if settings.YOLO_WEIGHTS_PATH
            else StubDetector(kb=self._kb)
        )
        self._brain = brain or ChatBrain(
            _base_url(),
            settings.VLM_MODEL_NAME,
            settings.VLM_API_KEY or "EMPTY",
            timeout_s=settings.CHAT_TIMEOUT_SECONDS,
            extra_body=_extra_body(),
        )
        self._retriever = Retriever(self._kb)
        self._sessions = Sessions()
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport) if self._transport else httpx.AsyncClient()

    async def _photos(self, images: List[str]) -> List[Tuple[Optional[str], float, bool]]:
        from app.services.pipeline.images import load_base64_image

        readings = []
        for image in images[:3]:
            try:
                found = await self._detector.detect(load_base64_image(image))
            except Exception:  # an unreadable photo is skipped; the words still count
                logger.warning("photo not read", exc_info=True)
                found = []
            top = found[0] if found else None
            readings.append((top.device_type if top else None, top.confidence if top else 0.0, bool(top and top.uncertain)))
        return readings

    async def _think(self, session: Session, also: List[str]) -> Verdict:
        try:
            async with self._client() as client:
                # A reply like "Chảy nước" names no appliance; the one already
                # settled stands in for the photograph it may have come from.
                verdict = await self._brain.turn(client, session.turns, session.photo_device or session.device, also)
        except httpx.TimeoutException as exc:
            raise AITimeoutException(str(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise VlmException(f"{type(exc).__name__}: {exc}") from exc
        if verdict.device_type:
            session.device = verdict.device_type
        return verdict

    async def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        session = self._sessions.get(request.session_id, request.diagnostic_state, list(request.history or []))
        readings = await self._photos(list(request.images or []))
        seen = [r for r in readings if r[0]]
        if seen:
            session.photo_device, session.photo_confidence = seen[0][0], seen[0][1]
            session.device = seen[0][0]
        session.turns.append(Turn("user", request.description))
        verdict = await self._think(session, [r[0] for r in seen[1:]])
        session.turns.append(Turn("assistant", verdict.reply_vi))
        session.version += 1
        response = _diagnosis_response(request.request_id, session, verdict)
        photos = [
            PhotoReading(index=i, device_type=d, name_vi=devices().get(d) if d else None, uncertain=u)
            for i, (d, _, u) in enumerate(readings)
        ]
        return response.model_copy(update={"photos": photos})

    async def answer(self, request: ChatRequest) -> ChatResponse:
        session = self._sessions.get(request.session_id, None, list(request.history or []))
        if request.device_type in devices() and not session.device:
            session.device = request.device_type
        session.turns.append(Turn("user", request.question))
        async with self._client() as client:
            try:
                routed = await self._brain.route(client, session.turns[-1:])
            except httpx.HTTPError as exc:
                raise VlmException(str(exc)) from exc
            if routed.get("intent") == "question" and not routed.get("devices"):
                reply = await self._policy_answer(client, request.question)
                session.turns.append(Turn("assistant", reply.answer_vi))
                return reply.model_copy(update={"request_id": request.request_id, "session_id": session.session_id})
        verdict = await self._think(session, [])
        session.turns.append(Turn("assistant", verdict.reply_vi))
        status = AnswerStatus.OUT_OF_SCOPE if verdict.decision == "not_repair" else AnswerStatus.OK
        return ChatResponse(
            request_id=request.request_id,
            session_id=session.session_id,
            status=status,
            answer_vi=verdict.reply_vi,
            confidence=min(max(verdict.confidence, 0.0), 1.0),
            recommended_services=_services(verdict),
            notes_vi=_notes(verdict),
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )

    async def _policy_answer(self, client: httpx.AsyncClient, question: str) -> ChatResponse:
        found = self._retriever.policy_passages(question, top_k=3)
        if not found:
            return ChatResponse(
                status=AnswerStatus.NO_GROUNDING,
                answer_vi="Dạ câu này em chưa có thông tin chính xác, anh/chị nhắn tổng đài FixHome giúp em nhé.",
                disclaimer_vi=settings.AI_DISCLAIMER_VI,
            )
        passages = "\n\n".join(f"[{p.policy.title_vi}]\n{p.policy.content_vi}" for p in found)
        body = {
            "model": settings.VLM_MODEL_NAME,
            "messages": [
                {"role": "system", "content": ANSWER_SYSTEM.format(passages=passages)},
                {"role": "user", "content": question},
            ],
            "temperature": 0.0,
            "max_tokens": 160,
            **_extra_body(),
        }
        try:
            r = await client.post(
                _base_url() + "/chat/completions", json=body,
                headers={"Authorization": f"Bearer {settings.VLM_API_KEY or 'EMPTY'}"},
                timeout=settings.CHAT_TIMEOUT_SECONDS,
            )
            r.raise_for_status()
            text = " ".join(r.json()["choices"][0]["message"]["content"].split())
        except httpx.HTTPError as exc:
            raise VlmException(str(exc)) from exc
        return ChatResponse(
            status=AnswerStatus.OK,
            answer_vi=text[:400],
            citations=[Citation(doc_id=p.policy.doc_id, title_vi=p.policy.title_vi, score=min(p.score, 1.0)) for p in found],
            confidence=min(found[0].score, 1.0),
            disclaimer_vi=settings.AI_DISCLAIMER_VI,
        )


def _urgency(verdict: Verdict) -> UrgencyLevel:
    menu = menu_for(verdict.device_type) if verdict.device_type else None
    fault = menu.fault(verdict.fault_code) if menu else None
    return UrgencyLevel(fault.urgency) if fault and fault.urgency in UrgencyLevel.__members__ else UrgencyLevel.LOW


def _faults(verdict: Verdict) -> List[SuspectedFault]:
    menu = menu_for(verdict.device_type) if verdict.device_type else None
    fault = menu.fault(verdict.fault_code) if menu else None
    if fault is None:
        return []
    return [SuspectedFault(fault_code=fault.code, name_vi=fault.name_vi, confidence=min(max(verdict.confidence, 0.0), 1.0))]


def _services(verdict: Verdict) -> List[RecommendedService]:
    out = []
    for v in [verdict, *verdict.others]:
        menu = menu_for(v.device_type) if v.device_type else None
        service = menu.service(v.service_code) if menu else None
        if service and v.decision == "conclude":
            out.append(RecommendedService(service_code=service.code, name_vi=service.name_vi, device_type=v.device_type))
    return out


def _notes(verdict: Verdict) -> List[str]:
    """What the technician reads on the booking, from the customer's own account."""
    notes = []
    for v in [verdict, *verdict.others]:
        if v.need_vi:
            name = devices().get(v.device_type, "") if v.device_type else ""
            notes.append(f"{name}: khách cho biết {v.need_vi}".strip(": "))
        if v.code_note_vi:
            notes.append(v.code_note_vi)
    return notes


def _device_entry(v: Verdict, primary: bool, session: Session) -> DeviceSuggestion:
    menu = menu_for(v.device_type)
    service = menu.service(v.service_code) if menu else None
    from_photo = v.device_type == session.photo_device
    return DeviceSuggestion(
        device_type=v.device_type,
        name_vi=devices()[v.device_type],
        source=EvidenceSource.IMAGE if from_photo else EvidenceSource.DESCRIPTION,
        confidence=session.photo_confidence if from_photo else 0.9,
        is_primary=primary,
        suspected_faults=_faults(v),
        service=RecommendedService(service_code=service.code, name_vi=service.name_vi, device_type=v.device_type) if service else None,
        questions_vi=[v.question_vi] if v.question_vi else [],
        price_estimate=pricing.estimate(v.service_code, [v.fault_code] if v.fault_code else [], v.device_type) if service else None,
        description_vi=v.need_vi or None,
        status=DiagnosisStatus.NEEDS_CLARIFICATION if v.decision == "ask" else DiagnosisStatus.OK,
        message_vi=v.reply_vi,
        urgency=_urgency(v),
    )


def _diagnosis_response(request_id: Optional[str], session: Session, verdict: Verdict) -> DiagnosisResponse:
    device = None
    if verdict.device_type:
        from_photo = verdict.device_type == session.photo_device
        device = DetectedDevice(
            device_type=verdict.device_type,
            name_vi=devices()[verdict.device_type],
            confidence=session.photo_confidence if from_photo else 0.9,
            source=EvidenceSource.IMAGE if from_photo else EvidenceSource.DESCRIPTION,
        )
    asking = verdict.decision == "ask"
    price = (
        pricing.estimate(verdict.service_code, [verdict.fault_code] if verdict.fault_code else [], verdict.device_type)
        if verdict.service_code and not asking
        else None
    )
    several = [verdict, *verdict.others] if verdict.others else []
    return DiagnosisResponse(
        request_id=request_id,
        session_id=session.session_id,
        status=DiagnosisStatus.NEEDS_CLARIFICATION if asking else DiagnosisStatus.OK,
        device=device,
        suspected_faults=_faults(verdict),
        recommended_services=[] if asking else _services(verdict),
        # Not sent: the client lists them under the reply, and the one that
        # matters (the safe step for a dangerous fault) already opens it.
        suggested_actions_vi=[],
        price_estimate=price,
        urgency=_urgency(verdict),
        confidence=min(max(verdict.confidence, 0.0), 1.0),
        is_low_confidence=asking,
        clarification=Clarification(
            questions_vi=[verdict.question_vi or verdict.reply_vi], answer_options_vi=verdict.options_vi
        ) if asking else None,
        # A question travels in `clarification`, where the client shows it with
        # its answer buttons; repeated here it would appear twice.
        message_vi=None if asking else verdict.reply_vi,
        model_info=ModelInfo(
            detector="yolo11s" if settings.YOLO_WEIGHTS_PATH else "stub",
            vlm=settings.VLM_MODEL_NAME,
        ),
        notes_vi=_notes(verdict),
        devices=[_device_entry(v, i == 0, session) for i, v in enumerate(several) if v.device_type][:3],
        diagnostic_state=session.export(),
        state_version=session.version,
        disclaimer_vi=settings.AI_DISCLAIMER_VI,
    )
