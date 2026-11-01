# app/services/pipeline/diagnostic_state.py
"""The conversation's diagnostic state, as Backend stores it between turns.

PO 01/11/2026 (audit approved): the state of a diagnosis lived only in this
process's memory. A restart, a second worker or an hour's pause lost it, and
Backend could only send back what the customer had typed, so a resumed
conversation forgot what had been asked, answered and ruled out. Backend's
Postgres is now the record: every reply carries the state, Backend saves it
under `state_version`, and sends it back with the next message.

Two parts:

    canonical   what was established, in a versioned schema
                (docs/diagnostic-state.schema.json): appliances and photos,
                what the customer said and when, answers to questions, the
                faults still in play and how, corrections, the diagnosis
                status, the service. For Backend, the technician and tests.
    engine      everything this service needs to carry on exactly where it
                stopped, as plain JSON. Only the classes listed in
                `_DATACLASSES` and `_MODELS` are ever rebuilt from it.

Nothing the model writes goes in here unchecked: the faults are codes the
pipeline already validated, prices and services come from the catalogue, and
no status says "confirmed" — only a technician can confirm a fault.
"""

from __future__ import annotations

import dataclasses
import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.schemas import diagnosis as _schemas
from app.services.pipeline import conversation as _conversation
from app.services.pipeline import dialogue_state as _dialogue

SCHEMA_VERSION = 1


# -- the canonical part ------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StateStatement(_Model):
    """Something the customer said, kept in their words with when it was said."""

    text_vi: str
    turn: int
    source: Literal["USER_REPORTED", "IMAGE_OBSERVED", "AI_INFERRED", "TECHNICIAN"] = "USER_REPORTED"


class StateImage(_Model):
    image_index: int
    device_type: Optional[str] = None
    confidence: Optional[float] = None
    uncertain: bool = False


class StateHypothesis(_Model):
    fault_code: str
    name_vi: str
    status: Literal["POSSIBLE", "LESS_LIKELY", "RULED_OUT"]
    """POSSIBLE: still in play. LESS_LIKELY: the customer answered no to one of
    its symptoms. RULED_OUT: the customer said so. Never CONFIRMED here: only a
    technician on site confirms a fault."""
    reason_vi: Optional[str] = None
    rank: Optional[int] = None
    """Its place in the last answer, 1 first. A rank, not a probability: no
    calibration data exists to turn retrieval scores into percentages."""


class StateService(_Model):
    service_code: str
    name_vi: str


class StateDevice(_Model):
    device_type: str
    name_vi: Optional[str] = None
    recognised_from: Optional[str] = None
    confidence: Optional[float] = None
    brand: Optional[str] = None
    error_codes: List[str] = []
    images: List[StateImage] = []
    statements: List[StateStatement] = []
    hypotheses: List[StateHypothesis] = []
    service: Optional[StateService] = None


class StateQa(_Model):
    question_vi: str
    asked_turn: int
    source: str
    answer_vi: Optional[str] = None
    answered_turn: Optional[int] = None
    status: Literal["PENDING", "ANSWERED", "UNANSWERED"]


class CanonicalState(_Model):
    schema_version: int = SCHEMA_VERSION
    state_version: int
    session_id: str
    updated_at: float
    diagnosis_status: Literal[
        "UNKNOWN", "COLLECTING_INFORMATION", "POSSIBLE", "LIKELY", "NEED_TECHNICIAN"
    ]
    """LIKELY: one fault left in play. POSSIBLE: several. COLLECTING_INFORMATION:
    a question is waiting for its answer. NEED_TECHNICIAN: the customer
    described danger (smoke, burning, gas). CONFIRMED does not exist here."""
    devices: List[StateDevice] = []
    qa: List[StateQa] = []
    danger: bool = False
    turns: int = 0


def json_schema() -> Dict[str, Any]:
    """The contract, as published in docs/diagnostic-state.schema.json."""
    schema = CanonicalState.model_json_schema(by_alias=True)
    schema["$id"] = f"https://fixhome.sbs/schemas/diagnostic-state/v{SCHEMA_VERSION}.json"
    schema["title"] = "FixHome diagnostic state"
    return schema


def _device_of(chat, kb, device_type: str, turns_offset: int = 0) -> StateDevice:
    memo = chat.memo.get(device_type, {})
    excluded = chat.state.excluded
    penalties = chat.state.penalties
    hypotheses: List[StateHypothesis] = []
    held = chat.hypotheses if chat.hypotheses_device == device_type else []
    for rank, code in enumerate(held, start=1):
        fault = kb.fault(code)
        status = "LESS_LIKELY" if penalties.get(code, 1.0) < 1.0 else "POSSIBLE"
        hypotheses.append(StateHypothesis(fault_code=code, name_vi=fault.name_vi if fault else code, status=status, rank=rank))
    for code, exclusion in excluded.items():
        fault = kb.fault(code)
        if fault is None or fault.device_type != device_type:
            continue
        hypotheses.append(
            StateHypothesis(
                fault_code=code, name_vi=fault.name_vi, status="RULED_OUT",
                reason_vi=f"{exclusion.kind}: {exclusion.phrase_vi}" if exclusion.phrase_vi else exclusion.kind,
            )
        )
    statements = []
    number = 0
    for turn in chat.turns:
        if turn.role != "customer":
            continue
        number += 1
        if turn.device_type in (None, device_type):
            statements.append(StateStatement(text_vi=turn.text_vi, turn=number + turns_offset))
    service = memo.get("service")
    images = []
    if memo.get("image_index") is not None:
        images.append(
            StateImage(
                image_index=int(memo["image_index"]), device_type=device_type,
                confidence=memo.get("confidence"), uncertain=bool(memo.get("uncertain")),
            )
        )
    return StateDevice(
        device_type=device_type,
        name_vi=kb.device_name_vi(device_type),
        recognised_from=chat.device_source_vi if chat.device_type == device_type else None,
        confidence=chat.device_confidence if chat.device_type == device_type else None,
        brand=chat.brand if chat.device_type == device_type else None,
        error_codes=list(chat.error_codes) if chat.device_type == device_type else [],
        images=images,
        statements=statements,
        hypotheses=hypotheses,
        service=StateService(service_code=service.service_code, name_vi=service.name_vi) if service is not None else None,
    )


def canonical(chat, store, kb) -> CanonicalState:
    devices: List[StateDevice] = []
    main = chat.device_type or chat.hypotheses_device
    if main:
        devices.append(_device_of(chat, kb, main))
    for device_type, child_id in chat.others.items():
        child = store.peek(child_id)
        if child is not None and device_type != main:
            devices.append(_device_of(child, kb, device_type))
    current = chat.customer_turns()
    qa = [
        StateQa(
            question_vi=e.question_vi, asked_turn=e.asked_turn, source=e.source,
            answer_vi=e.answer_vi, answered_turn=e.answered_turn,
            status="ANSWERED" if e.answer_vi else ("PENDING" if e.asked_turn == current else "UNANSWERED"),
        )
        for e in chat.qa
    ]
    in_play = [h for d in devices[:1] for h in d.hypotheses if h.status != "RULED_OUT"]
    if chat.state.danger:
        status = "NEED_TECHNICIAN"
    elif any(q.status == "PENDING" for q in qa):
        status = "COLLECTING_INFORMATION"
    elif len(in_play) == 1:
        status = "LIKELY"
    elif in_play:
        status = "POSSIBLE"
    else:
        status = "UNKNOWN"
    return CanonicalState(
        state_version=chat.state_version,
        session_id=chat.session_id,
        updated_at=chat.updated_at,
        diagnosis_status=status,
        devices=devices,
        qa=qa,
        danger=chat.state.danger,
        turns=current,
    )


# -- the engine part ---------------------------------------------------------

_DATACLASSES = {
    "Conversation": _conversation.Conversation,
    "Turn": _conversation.Turn,
    "QaEntry": _conversation.QaEntry,
    "DialogueState": _dialogue.DialogueState,
    "Exclusion": _dialogue.Exclusion,
}
_MODELS = {
    name: getattr(_schemas, name)
    for name in dir(_schemas)
    if isinstance(getattr(_schemas, name), type) and issubclass(getattr(_schemas, name), BaseModel)
}


def _encode(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        name = type(value).__name__
        if name not in _DATACLASSES:
            raise TypeError(f"not storable: {name}")
        return {"__dc__": name, **{f.name: _encode(getattr(value, f.name)) for f in dataclasses.fields(value)}}
    if isinstance(value, BaseModel):
        return {"__pm__": type(value).__name__, "data": value.model_dump(mode="json")}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return {"__tuple__": [_encode(v) for v in value]}
    if isinstance(value, (set, frozenset)):
        return {"__set__": [_encode(v) for v in sorted(value, key=str)]}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"not storable: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if "__dc__" in value:
        cls = _DATACLASSES.get(value["__dc__"])
        if cls is None:
            raise ValueError(f"unknown class {value['__dc__']!r}")
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: _decode(v) for k, v in value.items() if k in names})
    if "__pm__" in value:
        cls = _MODELS.get(value["__pm__"])
        if cls is None:
            raise ValueError(f"unknown model {value['__pm__']!r}")
        return cls.model_validate(value["data"])
    if "__tuple__" in value:
        return tuple(_decode(v) for v in value["__tuple__"])
    if "__set__" in value:
        return {_decode(v) for v in value["__set__"]}
    return {k: _decode(v) for k, v in value.items()}


def export(chat, store, kb) -> Dict[str, Any]:
    """The whole state of this conversation and its appliances' conversations."""
    children = {}
    for child_id in chat.others.values():
        child = store.peek(child_id)
        if child is not None:
            children[child_id] = _encode(child)
    return {
        "canonical": canonical(chat, store, kb).model_dump(mode="json", by_alias=True),
        "engine": {"schemaVersion": SCHEMA_VERSION, "conversation": _encode(chat), "children": children},
    }


def restore(state: Dict[str, Any], store, session_id: str) -> Optional[Any]:
    """Put a stored conversation back in the store under its own id.

    Only when the state is for exactly this session, and only when this
    process does not already hold a newer one. Returns the conversation, or
    None when nothing was restored."""
    engine = (state or {}).get("engine") or {}
    if engine.get("schemaVersion") != SCHEMA_VERSION:
        return None
    try:
        chat = _decode(engine.get("conversation"))
        children = {cid: _decode(c) for cid, c in (engine.get("children") or {}).items()}
    except (TypeError, ValueError, KeyError):
        return None
    if not isinstance(chat, _conversation.Conversation) or chat.session_id != session_id:
        return None
    held = store.peek(session_id)
    if held is not None and held.state_version >= chat.state_version:
        return None
    chat.updated_at = time.time()
    store.adopt(chat)
    for child in children.values():
        if isinstance(child, _conversation.Conversation):
            child.updated_at = time.time()
            store.adopt(child)
    return chat
