# app/services/pipeline/qwen_client.py
"""Talks to Qwen2.5-VL served by vLLM over its OpenAI-compatible API.

Two calls, both deliberately narrow.

`assess` shows the model the cropped device and the customer's description, and
asks it to choose from a shortlist of codes that retrieval has already
assembled. It is a multiple-choice question, not an open one. The model never
writes anything a customer sees: every Vietnamese string comes from the
knowledge base afterwards, so a fluent-sounding invention has nowhere to enter.

`answer` is the advisory chatbot. It may only restate retrieved passages, and
is told to decline when they do not cover the question, because a plausible
answer about a warranty term nobody wrote is worse than no answer.

Everything is validated on the way back. A code outside the shortlist, a
confidence outside 0..1, malformed JSON, a timeout — each produces an empty
verdict rather than an exception, and an empty verdict ends in a clarification
request. The pipeline degrades into asking the customer a question, which is
the behaviour the business rules ask for.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.services.pipeline.images import ImagePayload
from app.services.pipeline.vlm import VlmVerdict

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_ASSESS_SYSTEM = (
    "Bạn là trợ lý kỹ thuật của FixHome. Nhiệm vụ duy nhất của bạn là chọn mã "
    "trong danh sách được cung cấp. Tuyệt đối không tạo ra mã mới, không giải "
    "thích dài dòng, không viết nội dung cho khách hàng.\n"
    "Chỉ trả về JSON đúng định dạng:\n"
    '{"fault_codes": [...], "condition_codes": [...], "confidence": 0.0, "reason": "..."}\n'
    "fault_codes: tối đa 3 mã, xếp theo mức độ khả năng giảm dần, chỉ lấy từ danh sách.\n"
    "condition_codes: dấu hiệu hư hại NHÌN THẤY ĐƯỢC trên ảnh, chỉ lấy từ danh sách. "
    "Không thấy gì rõ ràng thì để mảng rỗng.\n"
    "confidence: từ 0 tới 1, phản ánh mức chắc chắn thật sự. "
    "Mô tả mơ hồ thì để thấp.\n"
    "reason: một câu ngắn bằng tiếng Việt, chỉ dùng cho nhật ký nội bộ."
)

_ANSWER_SYSTEM = (
    "Bạn là trợ lý của FixHome, nền tảng sửa chữa thiết bị gia đình.\n"
    "Chỉ được trả lời dựa trên các đoạn tài liệu được cung cấp. "
    "Không suy diễn, không thêm thông tin ngoài tài liệu.\n"
    "Nếu tài liệu không trả lời được câu hỏi, trả về đúng hai chữ: KHONG_DU_THONG_TIN\n"
    "Khi trả lời được thì viết tiếng Việt tự nhiên, ngắn gọn, tối đa bốn câu. "
    "Không bịa giá, không hứa thời gian, không thay kỹ thuật viên kết luận."
)

_INSUFFICIENT = "KHONG_DU_THONG_TIN"


class QwenClient:
    """A thin, defensive client. It owns no business rules."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        api_key: Optional[str] = None,
        max_tokens: int = 512,
    ) -> None:
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._model = model_name
        self._timeout = timeout_seconds
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._max_tokens = max_tokens

    async def _chat(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            # Deterministic on purpose: the same photo and description must give
            # the same answer, otherwise the fixed regression set measures noise.
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": self._max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._url, json=payload, headers=self._headers
                )
                response.raise_for_status()
                body = response.json()
            return body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            # Logged without the prompt: it carries the customer's description.
            logger.warning("qwen_call_failed", extra={"error": type(exc).__name__})
            return None

    async def assess(
        self,
        crop: Optional[ImagePayload],
        description: str,
        device_type: Optional[str],
        candidate_fault_codes: List[str],
        candidate_condition_codes: List[str],
    ) -> VlmVerdict:
        if not candidate_fault_codes:
            # Nothing to choose from. Asking anyway invites the model to invent
            # a code, and the answer would be discarded regardless.
            return VlmVerdict()

        content: List[Dict[str, Any]] = []
        if crop is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{crop.to_base64()}"
                    },
                }
            )
        content.append({"type": "text", "text": _build_assess_prompt(
            description, device_type, candidate_fault_codes, candidate_condition_codes
        )})

        raw = await self._chat(
            [
                {"role": "system", "content": _ASSESS_SYSTEM},
                {"role": "user", "content": content},
            ]
        )
        if raw is None:
            return VlmVerdict()
        return _parse_verdict(raw, candidate_fault_codes, candidate_condition_codes)

    async def answer(self, question: str, passages_vi: List[str]) -> tuple[str, float]:
        if not passages_vi:
            return "", 0.0

        numbered = "\n\n".join(
            f"[{i}] {p}" for i, p in enumerate(passages_vi, start=1)
        )
        prompt = (
            f"Tài liệu tham khảo:\n\n{numbered}\n\n"
            f"Câu hỏi của khách hàng: {question}\n\n"
            "Trả lời dựa trên tài liệu trên."
        )
        raw = await self._chat(
            [
                {"role": "system", "content": _ANSWER_SYSTEM},
                {"role": "user", "content": prompt},
            ]
        )
        if raw is None:
            return "", 0.0

        text = raw.strip()
        if not text or _INSUFFICIENT in text.upper():
            return "", 0.0

        # The first retrieved passage is the best match, so a longer list means
        # weaker support for any single one; this is a coarse proxy until the
        # retriever reports a calibrated score.
        confidence = 0.8 if len(passages_vi) == 1 else 0.7
        return text, confidence


def _build_assess_prompt(
    description: str,
    device_type: Optional[str],
    fault_codes: List[str],
    condition_codes: List[str],
) -> str:
    device_line = (
        f"Thiết bị đã được nhận diện từ ảnh: {device_type}"
        if device_type
        else "Không có ảnh, chỉ có mô tả."
    )
    return (
        f"{device_line}\n\n"
        f"Mô tả của khách hàng: {description}\n\n"
        f"Danh sách mã bệnh được phép chọn:\n"
        + "\n".join(f"- {c}" for c in fault_codes)
        + "\n\nDanh sách mã dấu hiệu nhìn thấy được phép chọn:\n"
        + "\n".join(f"- {c}" for c in condition_codes)
        + "\n\nChọn mã phù hợp nhất và trả về JSON."
    )


def _parse_verdict(
    raw: str, allowed_faults: List[str], allowed_conditions: List[str]
) -> VlmVerdict:
    """Extract and validate the verdict, discarding anything unexpected.

    Models wrap JSON in prose or code fences often enough that insisting on a
    clean body would fail on output that is otherwise correct, so the first
    balanced-looking block is taken. What cannot be salvaged becomes an empty
    verdict, which the pipeline turns into a clarification request.
    """
    match = _JSON_BLOCK.search(raw)
    if match is None:
        logger.warning("qwen_no_json_in_response")
        return VlmVerdict()

    try:
        data = json.loads(match.group(0))
    except ValueError:
        logger.warning("qwen_malformed_json")
        return VlmVerdict()
    if not isinstance(data, dict):
        return VlmVerdict()

    allowed_fault_set = set(allowed_faults)
    allowed_condition_set = set(allowed_conditions)

    faults = [
        code
        for code in _as_str_list(data.get("fault_codes"))
        if code in allowed_fault_set
    ][:3]
    conditions = [
        code
        for code in _as_str_list(data.get("condition_codes"))
        if code in allowed_condition_set
    ]

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(max(confidence, 0.0), 1.0)

    if not faults:
        # Every code it named was outside the shortlist, so there is nothing to
        # report even if it sounded certain.
        return VlmVerdict(confidence=0.0)

    reason = data.get("reason")
    return VlmVerdict(
        fault_codes=faults,
        condition_codes=conditions,
        confidence=confidence,
        reasoning_vi=reason if isinstance(reason, str) else None,
    )


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []
