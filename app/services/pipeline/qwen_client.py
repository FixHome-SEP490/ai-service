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
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.pipeline.images import ImagePayload
from app.services.pipeline.vlm import FaultCandidate, VlmVerdict

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_ASSESS_SYSTEM = (
    # The first two sentences are not politeness. Asked "ổ cắm có bị cháy đen
    # không?" the model replied "tôi không thể xem hình ảnh của bạn", then in
    # the next breath answered "màu trắng" when asked the colour of the same
    # socket. It can see; a question shaped as judging a condition is what it
    # declines. Saying outright that it is looking at a photograph, and asking
    # it to describe rather than to assess, stopped the refusals: it went on to
    # count four sockets, report their surfaces as clean, and pick the right
    # code from a closed list, all of which it had refused a moment earlier.
    "Bạn là bộ phận thị giác của hệ thống FixHome. Bạn LUÔN nhìn thấy bức ảnh "
    "được gửi kèm. Hãy mô tả những gì quan sát được trong ảnh, không đưa lời "
    "khuyên và không hướng dẫn cách xử lý.\n"
    "Nhiệm vụ duy nhất của bạn là chọn mã "
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
        # Accept the address with or without the /v1 suffix. vLLM prints its
        # own address as ".../v1", so that is what an operator copies, and
        # appending another produced /v1/v1/chat/completions and a 404. The
        # pipeline treats a failed call as low confidence rather than an error,
        # which is right for a model that is merely down and wrong here: a
        # misconfigured address looked exactly like an inconclusive photograph.
        root = base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[: -len("/v1")]
        self._url = root + "/v1/chat/completions"
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
        candidates: List[FaultCandidate],
        candidate_condition_codes: List[Tuple[str, str]],
    ) -> VlmVerdict:
        if not candidates:
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
        content.append(
            {
                "type": "text",
                "text": _build_assess_prompt(
                    description,
                    device_type,
                    candidates,
                    candidate_condition_codes,
                    has_image=crop is not None,
                ),
            }
        )

        raw = await self._chat(
            [
                {"role": "system", "content": _ASSESS_SYSTEM},
                {"role": "user", "content": content},
            ]
        )
        if raw is None:
            return VlmVerdict()
        return _parse_verdict(
            raw,
            [c.code for c in candidates],
            [code for code, _ in candidate_condition_codes],
            has_image=crop is not None,
        )

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
    candidates: List[FaultCandidate],
    condition_codes: List[Tuple[str, str]],
    has_image: bool = True,
) -> str:
    """Give the model something to reason with, not a list of identifiers.

    Each candidate arrives with its Vietnamese name and the symptoms customers
    use to describe it, so the model can compare those against what this
    customer actually wrote. Retrieval's own score comes too: it says what the
    text alone suggested, which the photograph is there to confirm or overturn.
    """
    # The device can be known without an image: carried from an earlier turn,
    # or read from what the customer wrote. Saying "nhận diện từ ảnh" on a call
    # that carries no image is a claim the model then acts on — asked about an
    # oven with no photograph attached it answered "bề mặt thiết bị có vết nứt
    # và trầy xước", describing damage in a picture nobody sent.
    if device_type and has_image:
        device_line = f"Thiết bị đã được nhận diện từ ảnh: {device_type}"
    elif device_type:
        device_line = (
            f"Thiết bị: {device_type}. Lượt này KHÔNG có ảnh — chỉ có lời khách kể. "
            "Để condition_codes rỗng, vì không có gì để nhìn."
        )
    else:
        device_line = "Không có ảnh, chỉ có mô tả của khách hàng."

    lines = [
        device_line,
        "",
        # Two closed vocabularies, and the model has put a member of one into
        # the other's field. They are told apart by case, which is worth saying
        # outright rather than leaving to be inferred from the examples.
        "Có hai danh sách mã riêng biệt. Mã hư hỏng VIẾT HOA và chỉ đặt vào"
        " fault_codes. Mã dấu hiệu nhìn thấy viết thường và chỉ đặt vào"
        " condition_codes.",
        "",
        f'Khách hàng mô tả: "{description}"',
        "",
        "Các khả năng hư hỏng đang cân nhắc, kèm những cách khách hàng thường mô tả:",
        "",
    ]
    for index, candidate in enumerate(candidates, start=1):
        lines.append(f"{index}. {candidate.code} — {candidate.name_vi}")
        lines.append(f"   Triệu chứng thường gặp: {', '.join(candidate.symptoms_vi)}")
        if candidate.retrieval_score:
            lines.append(
                f"   Mức khớp với mô tả theo từ khoá: {candidate.retrieval_score:.2f}"
            )
        lines.append("")

    lines += [
        "Dấu hiệu hư hại nhìn thấy được. Đây là danh sách RIÊNG, các mã này"
        " viết thường và chỉ được đặt vào condition_codes, không bao giờ đặt vào"
        " fault_codes:",
        "",
    ]
    lines += [f"- {code} — {name_vi}" for code, name_vi in condition_codes]
    lines += [
        "",
        "Nhiệm vụ:",
        # "Ghi lại dấu hiệu hư hại" asks for a verdict, and a verdict is what
        # the model declines to give about a photograph. Asking what the
        # surface looks like, then which code that appearance matches, is the
        # same question in two steps it will actually answer.
        "1. Quan sát bề mặt thiết bị trong ảnh: màu sắc, vết bẩn, vết đen, vết"
        " nứt, vết rỉ, lớp tuyết bám. Mã nào trong danh sách trên mô tả đúng"
        " cái đang nhìn thấy thì chọn mã đó. Bề mặt bình thường thì để mảng"
        " rỗng, và đừng suy ra dấu hiệu từ lời khách kể.",
        "2. Đối chiếu mô tả của khách với triệu chứng của từng khả năng ở trên,"
        " chọn tối đa ba mã, xếp theo mức khả năng giảm dần.",
        "3. Đặt confidence theo mức chắc chắn thật. Mô tả mơ hồ hoặc nhiều khả"
        " năng ngang nhau thì để thấp, đừng làm tròn lên.",
        "",
        "Chỉ trả về JSON, không giải thích thêm.",
    ]
    return "\n".join(lines)


def _parse_verdict(
    raw: str,
    allowed_faults: List[str],
    allowed_conditions: List[str],
    has_image: bool = True,
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

    named_faults = _as_str_list(data.get("fault_codes"))
    named_conditions = _as_str_list(data.get("condition_codes"))
    if not has_image:
        # Nothing was looked at, so nothing was seen. The model returned
        # ["crack", "scratch", "rust"] for a text-only call, which is not a
        # judgement call to weigh — it is a description of a photograph that
        # does not exist.
        named_conditions = []

    # A code from our own vocabulary put in the wrong field is a slotting
    # mistake, not an invention, and dropping it throws away a correct answer.
    # Asked about a socket described as "cháy đen, có mùi khét" the model
    # returned {"fault_codes": ["burn_mark"], "condition_codes": []}: burn_mark
    # is a real visible-condition code, and discarding it left the most urgent
    # case in the catalogue with an empty diagnosis. Anything in neither list
    # is still refused.
    misplaced_conditions = [c for c in named_faults if c in allowed_condition_set]
    misplaced_faults = [c for c in named_conditions if c in allowed_fault_set]
    if misplaced_conditions or misplaced_faults:
        logger.info(
            "qwen_codes_in_wrong_field",
            extra={
                "conditions_in_faults": misplaced_conditions,
                "faults_in_conditions": misplaced_faults,
            },
        )

    faults = [c for c in [*named_faults, *misplaced_faults] if c in allowed_fault_set][:3]
    conditions = [
        c
        for c in [*named_conditions, *misplaced_conditions]
        if c in allowed_condition_set
    ]

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(max(confidence, 0.0), 1.0)

    if not faults:
        # Every fault it named was outside the shortlist, so there is nothing to
        # diagnose even if it sounded certain. What it saw on the surface is
        # kept: that observation is real, and the clarification turn can use it
        # rather than starting from nothing.
        return VlmVerdict(condition_codes=conditions, confidence=0.0)

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
