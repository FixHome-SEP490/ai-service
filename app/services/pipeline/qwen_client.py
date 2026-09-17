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
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.pipeline.corpus import voice_guidance
from app.services.pipeline.images import ImagePayload
from app.services.pipeline.vlm import FaultCandidate, VlmVerdict

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

def _assess_system(has_image: bool) -> str:
    """The instructions, which differ by whether there is anything to look at.

    One prompt for both was the mistake. Fixing a refusal — the model answering
    "tôi không thể xem hình ảnh" when asked about damage — by opening with "bạn
    là bộ phận thị giác, hãy mô tả cái quan sát được" turned it into a
    describer. It then returned empty fault_codes on eight tries out of eight
    while its own reason field said "mô tả rõ ràng về hiện tượng máy giặt không
    vắt": it had understood the customer and filled in the wrong field.

    Choosing the fault is the job. Reading the photograph is a detail of the
    job, and only when a photograph exists.
    """
    lines = [
        "Bạn là trợ lý chẩn đoán của FixHome.",
        "",
        "NHIỆM VỤ CHÍNH: đọc mô tả của khách và CHỌN mã hư hỏng khớp nhất trong "
        "danh sách được đánh số. Luôn phải chọn ít nhất một mã nếu có mã nào hợp "
        "lý — danh sách đã được lọc sẵn cho đúng thiết bị rồi. Chỉ để rỗng khi "
        "thật sự không mã nào liên quan.",
        "",
    ]
    if has_image:
        # Only said when true. Told there was a photograph when there was none,
        # the model described cracks and scratches in a picture nobody sent.
        lines += [
            "Có ảnh gửi kèm và bạn NHÌN THẤY được nó. Ngoài việc chọn mã hư "
            "hỏng, hãy ghi lại dấu hiệu quan sát được trên bề mặt thiết bị, chỉ "
            "chọn trong danh sách mã dấu hiệu. Bề mặt bình thường thì để rỗng.",
            "",
        ]
    else:
        lines += [
            "Lượt này KHÔNG có ảnh, chỉ có lời khách kể. Hãy chẩn đoán từ lời "
            "kể, đừng nói rằng thiếu ảnh. Để condition_codes rỗng vì không có "
            "gì để nhìn.",
            "",
        ]
    lines += [
        "Tuyệt đối không tạo mã mới, không giải thích dài dòng, không viết nội "
        "dung cho khách hàng.",
        "Chỉ trả về JSON đúng định dạng:",
        '{"fault_codes": [...], "condition_codes": [...], "confidence": 0.0, '
        '"reason": "..."}',
        "fault_codes: tối đa 3 mã hư hỏng VIẾT HOA, xếp theo khả năng giảm dần.",
        "condition_codes: mã dấu hiệu viết thường, chỉ khi nhìn thấy trên ảnh.",
        "confidence: 0 tới 1, phản ánh mức chắc chắn thật sự.",
        "reason: một câu ngắn tiếng Việt, chỉ dùng cho nhật ký nội bộ.",
    ]
    return "\n".join(lines)


_ANSWER_SYSTEM = (
    "Bạn là trợ lý của FixHome, nền tảng sửa chữa thiết bị gia đình.\n"
    "Chỉ được trả lời dựa trên các đoạn tài liệu được cung cấp. "
    "Không suy diễn, không thêm thông tin ngoài tài liệu.\n"
    "Nếu tài liệu nói về chuyện khác hẳn, trả về đúng hai chữ: "
    "KHONG_DU_THONG_TIN\n"
    "Nhưng nếu tài liệu đang nói đúng chủ đề mà không có con số khách hỏi, thì "
    "trả lời bằng đúng những gì tài liệu nói, và nói rõ con số đó nằm ở đâu. "
    "Đừng từ chối khi câu trả lời có trong tài liệu dưới dạng khác.\n"
    "Khi trả lời được thì viết tiếng Việt tự nhiên, ngắn gọn, tối đa bốn câu. "
    "Không bịa giá, không hứa thời gian, không thay kỹ thuật viên kết luận.\n"
    "\n"
    "Mở đầu bằng 'Dạ', xưng em, gọi khách là anh/chị, kết câu bằng 'ạ' hoặc "
    "'nhé' — giọng nhân viên đang nhắn tin, không phải một dòng trích tài liệu."
)

_SAFETY_ANSWER_SYSTEM = (
    "Bạn là trợ lý của FixHome, nền tảng sửa chữa thiết bị gia đình.\n"
    "Khách đang mô tả một tình huống nguy hiểm. Việc đầu tiên và quan trọng "
    "nhất của bạn là nói lại cho khách các việc phải làm ngay, đúng thứ tự "
    "được cung cấp, không bỏ bước nào.\n"
    "Chỉ được trả lời dựa trên các đoạn tài liệu được cung cấp. "
    "Không suy diễn, không thêm thông tin ngoài tài liệu.\n"
    "Không giới hạn số câu: nói đủ các bước còn hơn nói ngắn. "
    "Không bịa giá, không hứa thời gian, không thay kỹ thuật viên kết luận.\n"
    "Tuyệt đối không trả về KHONG_DU_THONG_TIN khi đã có phần phải nói ngay."
)
"""Separate from _ANSWER_SYSTEM because of one line in that one.

"tối đa bốn câu" is right for a maintenance question and wrong for a gas
leak, where the instruction runs to four steps and the fourth is the one about
not touching a light switch. A cap on length is a cap on how much of the
warning survives.
"""


_GENERAL_SYSTEM = (
    "Bạn là kỹ thuật viên sửa chữa thiết bị gia dụng của FixHome, đang nhắn tin "
    "với khách hàng Việt Nam.\n"
    "Trả lời bằng kiến thức nghề của bạn: giải thích nguyên nhân, cách kiểm tra "
    "an toàn tại nhà, nên làm gì trước khi thợ tới. Viết tự nhiên và đủ ý như "
    "đang nói chuyện thật, không lặp lại câu hỏi của khách.\n"
    "\n"
    "TUYỆT ĐỐI KHÔNG nói ba thứ sau, vì chúng không thuộc về bạn:\n"
    "1. Bất kỳ con số tiền nào. Không giá, không khoảng giá, không 'khoảng vài "
    "trăm nghìn'. Khách hỏi tiền thì nói cần biết rõ thiết bị và hư hỏng mới "
    "báo được.\n"
    "2. Điều khoản bảo hành, chính sách hoàn tiền, cam kết thời gian của FixHome.\n"
    "3. Khẳng định chắc chắn thiết bị hỏng gì khi chưa nhìn thấy. Nói 'thường "
    "là', 'khả năng cao', và nói rõ thợ phải kiểm tra mới chắc.\n"
    "\n"
    "Nếu câu hỏi không liên quan tới thiết bị gia dụng, điện nước trong nhà hay "
    "dịch vụ sửa chữa, trả về đúng một từ: NGOAI_PHAM_VI"
)
"""For questions the tables do not cover.

Refusing everything ungrounded made the assistant useless outside its own
catalogue: someone asking why frost forms on an evaporator got the same canned
sentence as someone asking about the weather. General repair knowledge is not a
fact anybody owns, and the model has it.

What it must not produce is the part that *is* owned. A price, a warranty term,
or a flat "your compressor is dead" reaches the customer as a commitment the
business then has to honour, and those three come from the tables and the
technician, never from a model.
"""

_APOLOGY = re.compile(
    r"^\s*(dạ\s*)?(em\s+|mình\s+|chúng\s+tôi\s+)?(rất\s+)?xin\s+lỗi[^.!?\n]*[.!?\n]\s*",
    re.IGNORECASE,
)


_PRONOUN_FIXES = (
    # The assistant speaking of itself. "Tôi" is not wrong Vietnamese, it is
    # the wrong register: a repair company's assistant says "em".
    (r"\bTôi\b", "Em"),
    (r"\btôi\b", "em"),
    # The customer. "Bạn" reads flat and slightly cold; the trade says anh/chị,
    # which also avoids guessing anyone's gender.
    (r"\bBạn\b", "Anh/chị"),
    (r"\bbạn\b", "anh/chị"),
    # Talking about the customer in the third person, to the customer.
    (r"\bcủa khách\b", "của anh/chị"),
    (r"\bcho khách\b", "cho anh/chị"),
    (r"\bkhách nên\b", "anh/chị nên"),
)


_MISSPELLINGS = (
    # Observed on every television answer: "hòng dải đèn nền". "Hòng" is a
    # real word — it means hoping to, as in "hòng thoát" — and it is never the
    # word for broken. The knowledge base writes "hỏng" and the model drops
    # the hook off the o on its way out. Correcting it also corrects the rare
    # sentence where "hòng" was meant, and that sentence is about someone
    # hoping to get away with something — not a thing a repair assistant
    # discussing a television has any reason to write.
    (r"\bhòng\b", "hỏng"),
    (r"\bHòng\b", "Hỏng"),
)


def _fix_spelling(text: str) -> str:
    """Correct the few misspellings the model reliably produces.

    Deliberately a short list of observed ones rather than a spellchecker. A
    general corrector would rewrite the trade's own words — "tụ", "bạc đạn",
    "aptomat" — and every wrong correction reaches a customer as a sentence
    that reads as though nobody checked it.
    """
    for pattern, replacement in _MISSPELLINGS:
        text = re.sub(pattern, replacement, text)
    return text


def _fix_pronouns(text: str) -> str:
    """Put the answer back into the register the persona asks for.

    The instruction is in the prompt and the persona file now sits above it,
    and a 3B model still wrote "Tôi đã kiểm tra và xác nhận rằng thiết bị của
    khách", then "thiết bị của bạn" one turn later. Register is a rule, so it
    is enforced like one rather than requested.

    Only whole words, and only the pronouns. Rewriting more of a sentence than
    this is how a fluent answer turns into a mechanical one, which is the thing
    being fixed.
    """
    for pattern, replacement in _PRONOUN_FIXES:
        text = re.sub(pattern, replacement, text)
    return text


def _strip_apology(text: str) -> str:
    """Remove an apology the answer opens with.

    A customer reporting a broken appliance is not complaining about FixHome,
    so an apology puts the fault in the wrong place and makes the conclusion
    read as backing away from it. Instructing the model not to apologise made
    it worse: shown the prohibition, a 3B model opened with the prohibition.

    Only the opening, and only whole sentences of it. An apology in the middle
    of an answer is usually attached to something real — a delay, a limit — and
    cutting text out of the middle of a sentence is how a fluent answer becomes
    an incoherent one.
    """
    previous = None
    while previous != text:
        previous = text
        text = _APOLOGY.sub("", text, count=1)
    return text.strip()


def _narrate_system() -> str:
    """The instructions, with the written voice in front of them.

    The hand-written half says what the turn must contain; the persona file
    says how a person says it. Keeping the two apart means whoever edits the
    voice edits a Vietnamese document rather than a Python string.
    """
    return f"{voice_guidance()}\n\n{_NARRATE_SYSTEM}"


_OUT_OF_SCOPE = "NGOAI_PHAM_VI"

_NARRATE_SYSTEM = (
    "Bạn là nhân viên kỹ thuật FixHome đang nhắn tin với khách hàng Việt Nam.\n"
    "Bạn được cho sẵn KẾT QUẢ CHẨN ĐOÁN. Việc của bạn chỉ là diễn đạt lại cho "
    "tự nhiên và lịch sự, như người thật đang trả lời tin nhắn.\n"
    "\n"
    "Viết theo mạch: xác nhận đã đọc thông tin khách gửi, nói đã kiểm tra, nêu "
    "khả năng hư hỏng, nêu khoảng chi phí, dặn việc cần làm ngay, rồi chủ động "
    "mời khách đặt thợ với đúng tên dịch vụ được cho.\n"
    "\n"
    "Bắt buộc:\n"
    "- Chỉ dùng đúng những con số và tên hư hỏng được cho. Không thêm, không "
    "đổi, không làm tròn, không ước lượng thêm bất kỳ con số nào.\n"
    "- Xưng em, gọi khách là anh/chị.\n"
    "- Bốn tới sáu câu, liền mạch, không gạch đầu dòng.\n"
    "- Không hứa thời gian, không khẳng định chắc chắn, không nhắc tới bảo hành.\n"
    "- Vào thẳng kết quả, giọng bình thường và dứt khoát.\n"
    "- Câu cuối mời khách đặt dịch vụ, gọi đúng tên dịch vụ được cho.\n"
    "- Viết thành đoạn văn xuôi, không chép lại các nhãn ở phần dữ liệu."
)
"""Written as what to do, never as what not to.

A 3B model repeats what it is shown. Told "tuyệt đối không xin lỗi, khách báo
thiết bị hỏng chứ không phải khiếu nại FixHome", it opened its next answer
with "Xin lỗi, em hiểu nhầm rồi. Khách báo rằng thiết bị hỏng, nhưng không
phải khiếu nại FixHome." — the prohibition, the reasoning, and two apologies.
The advisory prompt had the same accident: given the blunt sentence as an
example of what to avoid, it produced that exact sentence.

What must not happen is enforced after the fact instead. See _strip_apology.
"""
"""Wording only. The facts are handed over and may not be touched.

The reply was assembled from a template and read like one: same shape, same
order, same stock phrases for every customer. The knowledge base still owns
every fault name and every figure — this turns them into a message somebody
would actually send, and the caller checks that no number appeared that was not
given.
"""

_PRICE_LIKE = re.compile(
    r"\d[\d.,]*\s*(?:đ\b|vnd|k\b|nghìn|nghin|triệu|trieu|tr\b)", re.IGNORECASE
)
"""A number with money beside it, whatever the instruction said.

Telling the model not to quote a price is not a guarantee that it will not, and
a figure a customer reads is a figure they will hold the business to. Cheaper to
drop the answer than to explain afterwards why the number was not real.
"""

_INSUFFICIENT = "KHONG_DU_THONG_TIN"

_DECLINES = (
    "khong du thong tin",
    "khong co du thong tin",
    "khong the tra loi",
    "khong tim thay thong tin",
)
"""Ways the model says it cannot answer, in the customer's alphabet.

The sentinel was compared verbatim, so the model writing it back as proper
Vietnamese — "Không đủ thông tin." — passed the check and reached a customer as
the whole answer, with citations underneath it. Two words of internal protocol,
punctuated and capitalised, presented as advice.
"""


def _declines(text: str) -> bool:
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    folded = folded.replace("đ", "d").replace("_", " ")
    return any(phrase in folded for phrase in _DECLINES)


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
        # The warning answers are longer by instruction and were timing out.
        # Derived rather than injected, so a deployment that tunes the ordinary
        # budget does not silently leave this one behind.
        self._safety_timeout = max(timeout_seconds * 3, 25.0)
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._max_tokens = max_tokens

    async def _chat(
        self, messages: List[Dict[str, Any]], timeout_seconds: Optional[float] = None
    ) -> Optional[str]:
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
            async with httpx.AsyncClient(
                timeout=timeout_seconds or self._timeout
            ) as client:
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

    async def assess_context(
        self,
        crop: Optional[ImagePayload],
        context,
        candidate_condition_codes: List[Tuple[str, str]],
    ) -> VlmVerdict:
        """Choose from the assembled context rather than a bare code list.

        The context carries the conversation, the questions already put, the
        price rows and the policy text. Handing over only the shortlist is what
        made the assistant read like a lookup: it was one.
        """
        if not context.candidates:
            return VlmVerdict()

        prompt = build_context_prompt(context)
        if candidate_condition_codes and crop is not None:
            prompt += "\n\nDẤU HIỆU NHÌN THẤY (chỉ chọn trong đây, viết thường):\n"
            prompt += "\n".join(
                f"  {code} — {name}" for code, name in candidate_condition_codes
            )

        content: List[Dict[str, Any]] = []
        if crop is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{crop.to_base64()}"},
                }
            )
        content.append({"type": "text", "text": prompt})

        raw = await self._chat(
            [
                {"role": "system", "content": _assess_system(crop is not None)},
                {"role": "user", "content": content},
            ]
        )
        if raw is None:
            return VlmVerdict()
        return _parse_verdict(
            raw,
            [c.fault.fault_code for c in context.candidates],
            [code for code, _ in candidate_condition_codes],
            has_image=crop is not None,
        )

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
                {"role": "system", "content": _assess_system(crop is not None)},
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

    async def narrate(self, facts_vi: str, allowed_numbers: List[str]) -> str:
        """Turn a finished diagnosis into a message a person would send.

        Returns an empty string if the model introduced a number nobody gave
        it, in which case the caller keeps its own wording. A warmer sentence is
        worth having; a warmer sentence with an invented price is not.
        """
        raw = await self._chat(
            [
                {"role": "system", "content": _narrate_system()},
                {"role": "user", "content": facts_vi},
            ]
        )
        if raw is None:
            return ""

        text = _fix_spelling(_fix_pronouns(_strip_apology(raw.strip())))
        if not text or _declines(text):
            return ""

        permitted = {n.replace(".", "").replace(",", "") for n in allowed_numbers}
        for found in re.findall(r"\d[\d.,]*", text):
            if found.replace(".", "").replace(",", "") not in permitted:
                logger.warning("qwen_narration_invented_a_number")
                return ""
        return text

    async def answer_generally(self, question: str, history_vi: str = "") -> str:
        """Answer from the model's own knowledge, inside the trade.

        Empty string when the question is not about home appliances or repair,
        or when the answer quoted money, so the caller refuses rather than
        improvises.
        """
        prompt = question
        if history_vi:
            prompt = f"Câu chuyện từ đầu:\n{history_vi}\n\nCâu hỏi hiện tại: {question}"

        raw = await self._chat(
            [
                {"role": "system", "content": _GENERAL_SYSTEM},
                {"role": "user", "content": prompt},
            ]
        )
        if raw is None:
            return ""

        answer = raw.strip()
        if _OUT_OF_SCOPE in answer.upper().replace(" ", "_"):
            return ""
        if _PRICE_LIKE.search(answer):
            logger.warning("qwen_general_answer_quoted_money")
            return ""
        return answer

    async def answer(
        self,
        question: str,
        passages_vi: List[str],
        safety_vi: Optional[str] = None,
    ) -> tuple[str, float]:
        if not (passages_vi or safety_vi):
            return "", 0.0

        numbered = "\n\n".join(
            f"[{i}] {p}" for i, p in enumerate(passages_vi, start=1)
        )
        # A pinned warning is not one of the reference documents. Handing it
        # over as "[1]" among the rest and asking for a short answer, a 3B
        # model turned four ordered gas-leak instructions into "Khó hiểu rõ
        # ràng." The diagnosis prompt has framed it as an order from the
        # beginning; this surface was given the passage and none of the framing.
        head = ""
        if safety_vi:
            head = (
                "PHẢI NÓI NGAY, TRƯỚC KHI TRẢ LỜI BẤT KỲ ĐIỀU GÌ KHÁC:\n"
                f"{safety_vi}\n\n"
                "Nhắc lại đầy đủ các việc trên cho khách, đúng thứ tự đó, bằng "
                "lời của bạn. Không rút gọn, không bỏ bước nào. Xong rồi mới "
                "trả lời phần còn lại của câu hỏi.\n\n"
            )
        prompt = (
            f"{head}"
            f"Tài liệu tham khảo:\n\n{numbered}\n\n"
            f"Câu hỏi của khách hàng: {question}\n\n"
            "Trả lời dựa trên tài liệu trên."
        )
        raw = await self._chat(
            [
                # The four-sentence cap is right for a maintenance question
                # and wrong for a burning smell: it is the instruction the
                # model obeys when it drops the third and fourth safety step.
                {
                    "role": "system",
                    "content": _SAFETY_ANSWER_SYSTEM if safety_vi else _ANSWER_SYSTEM,
                },
                {"role": "user", "content": prompt},
            ],
            # A warning answer is two or three times longer by instruction, so
            # it needs longer than a maintenance question. At the ordinary
            # budget it timed out and the customer was shown the
            # service-unavailable message instead of the warning.
            timeout_seconds=self._safety_timeout if safety_vi else None,
        )
        if raw is None:
            return "", 0.0

        text = raw.strip()
        if not text or _declines(text):
            return "", 0.0

        # The first retrieved passage is the best match, so a longer list means
        # weaker support for any single one; this is a coarse proxy until the
        # retriever reports a calibrated score.
        confidence = 0.8 if len(passages_vi) == 1 else 0.7
        return text, confidence


def build_context_prompt(ctx) -> str:
    """Render the assembled context as the user turn.

    Order matters. The device comes first because it constrains everything
    after it; the conversation next, because a fault named three messages ago
    is still the fault; the shortlist after that, so the model is choosing
    against what it has just read rather than against a list in isolation.

    Policy and price lines are included so the model can say what it is allowed
    to say about cost and maintenance without reaching for anything else. They
    are facts it may repeat, not facts it may extend.
    """
    lines: List[str] = []

    # Before the device, before the conversation, before everything. A model
    # with a small context window attends to what it sees first, and this is
    # the one part of the bundle where being read late is a real cost.
    safety = getattr(ctx, "safety", None) or []
    for pinned in safety:
        lines += [
            "PHẢI NÓI NGAY, TRƯỚC KHI HỎI HAY CHẨN ĐOÁN BẤT KỲ ĐIỀU GÌ:",
            pinned.chunk.as_passage_vi(),
            "",
        ]

    if ctx.device_name_vi:
        how = f" (nhận ra từ {ctx.device_source_vi})" if ctx.device_source_vi else ""
        lines.append(f"THIẾT BỊ: {ctx.device_name_vi} [{ctx.device_type}]{how}")
    else:
        lines.append("THIẾT BỊ: chưa xác định")

    if ctx.history and len(ctx.history) > 1:
        lines += ["", "CUỘC TRÒ CHUYỆN TỪ ĐẦU:"]
        lines += [f"  {line}" for line in ctx.history]
    else:
        lines += ["", f'KHÁCH MÔ TẢ: "{ctx.latest_message}"']

    if ctx.already_asked:
        lines += [
            "",
            "ĐÃ HỎI KHÁCH RỒI, đừng hỏi lại: " + "; ".join(ctx.already_asked[-4:]),
        ]

    lines += ["", "CÁC KHẢ NĂNG HƯ HỎNG (chỉ được chọn trong đây):"]
    for index, candidate in enumerate(ctx.candidates, start=1):
        fault = candidate.fault
        lines.append(f"{index}. {fault.fault_code} — {fault.name_vi}")
        lines.append(
            "   Khách thường tả là: " + ", ".join(fault.symptoms_vi[:6])
        )
        lines.append(f"   Mức khớp từ khoá: {candidate.score:.2f}")

    if ctx.price_rows:
        lines += ["", "GIÁ THAM KHẢO (chỉ dùng đúng những con số này):"]
        lines += [f"  {row.as_text_vi()}" for row in ctx.price_rows]

    if ctx.policies:
        lines += ["", "CHÍNH SÁCH LIÊN QUAN:"]
        lines += [f"  {p.policy.content_vi}" for p in ctx.policies]

    # Last, and deliberately so. These are the longest blocks in the bundle, and
    # putting them above the shortlist pushed the candidate faults into the
    # middle of a wall of prose. They are what the answer is built from, not
    # what it is chosen from.
    passages = getattr(ctx, "passages", None) or []
    if passages:
        lines += [
            "",
            "TÀI LIỆU NGHỀ (dựa vào đây để giải thích, không được thêm ngoài):",
        ]
        for hit in passages:
            lines += ["", hit.chunk.as_passage_vi()]

    business = getattr(ctx, "business", None) or []
    if business:
        lines += ["", "QUY ĐỊNH CỦA FIXHOME:"]
        for hit in business:
            lines += ["", hit.chunk.as_passage_vi()]

    return "\n".join(lines)


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

    # Rescue misplaced fault codes first. Clearing the condition field before
    # looking in it threw away real answers: asked about a water heater with no
    # image, the model returned {"fault_codes": [], "condition_codes":
    # ["WH_INSTANT_NO_HOT", ...]} — the right codes, in the wrong field — and
    # the customer got "Qwen không chọn được mã nào" and a dead end.
    misplaced_faults = [c for c in named_conditions if c in set(allowed_faults)]

    if not has_image:
        # Nothing was looked at, so nothing was seen. The model returned
        # ["crack", "scratch", "rust"] for a text-only call, which is not a
        # judgement call to weigh — it is a description of a photograph that
        # does not exist. Fault codes rescued above are unaffected: they are
        # not claims about an image.
        named_conditions = []

    # A code from our own vocabulary put in the wrong field is a slotting
    # mistake, not an invention, and dropping it throws away a correct answer.
    # Asked about a socket described as "cháy đen, có mùi khét" the model
    # returned {"fault_codes": ["burn_mark"], "condition_codes": []}: burn_mark
    # is a real visible-condition code, and discarding it left the most urgent
    # case in the catalogue with an empty diagnosis. Anything in neither list
    # is still refused.
    misplaced_conditions = [c for c in named_faults if c in allowed_condition_set]
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
