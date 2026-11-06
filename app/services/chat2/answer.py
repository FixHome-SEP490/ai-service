"""Questions that are not a report of a broken appliance, answered from the knowledge index.

"FixHome là gì", "em là ai", "thanh toán thế nào", "có làm ở Thủ Đức không",
"bao lâu vệ sinh máy lạnh một lần", "tủ lạnh 10 năm có nên sửa không", and
after a diagnosis "sửa có lâu không", "tự làm được không".

Retrieval reads a table of contents instead of matching words. The model is
shown the titles of every passage the conversation may use (the platform's,
the appliance's being discussed, the concluded fault's; app/data/
knowledge_index.json, built by tools/build_knowledge_index.py) and picks up to
three, under a schema whose enum is those ids. A title says what a section is
about in words a customer's question shares meaning with but rarely spelling,
which is where word matching failed. The answer is then written from those
passages alone, two or three sentences, and they come back as citations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import httpx

from app.services.chat2.menu import DATA_DIR, devices

MAX_PICKED = 3
ANSWER_MAX = 420

PICK_SYSTEM = """Bạn chọn tài liệu để trả lời câu hỏi của khách hàng FixHome (dịch vụ sửa chữa, vệ sinh, lắp đặt đồ gia dụng tại nhà).
Đọc câu hỏi cuối của khách trong cuộc trò chuyện, rồi chọn tối đa 3 mục trong mục lục dưới đây chứa câu trả lời, mục sát nhất đứng trước.
Không mục nào trả lời được thì để danh sách rỗng.

Mục lục (mã | tài liệu › mục):
{toc}"""

ANSWER_SYSTEM = """Bạn là trợ lý của FixHome, nhắn tin riêng với khách. Xưng "em", gọi khách là "anh/chị".
Trả lời câu hỏi cuối của khách CHỈ bằng thông tin trong các đoạn tài liệu dưới đây.
- Trả lời thẳng vào điều khách hỏi ngay câu đầu, tối đa ba câu ngắn, không chào hỏi, không xin lỗi, không lan man.
- Số tiền, thời hạn, địa danh, điều khoản: chỉ nói khi có trong đoạn tài liệu, chép đúng.
- Đoạn tài liệu không có câu trả lời thì nói em chưa có thông tin đó, và nếu hợp thì gợi ý khách kể hiện tượng của máy để em xem giúp.
- Em không tự đặt lịch hay cử thợ được; muốn đặt thì khách bấm "Đặt thợ".
{context}
Đoạn tài liệu:
{passages}"""


@dataclass(frozen=True)
class Passage:
    id: str
    scope: str
    doc_vi: str
    section_vi: str
    text_vi: str


@dataclass
class Answer:
    reply_vi: str
    passages: List[Passage] = field(default_factory=list)
    grounded: bool = False
    latency_s: float = 0.0


@lru_cache(maxsize=1)
def index() -> Dict[str, Passage]:
    path = DATA_DIR / "knowledge_index.json"
    raw = json.loads(path.read_text(encoding="utf-8"))["passages"] if path.exists() else []
    return {p["id"]: Passage(**p) for p in raw}


def candidates(device_type: Optional[str], fault_code: Optional[str]) -> List[Passage]:
    """What a question in this conversation may draw on, platform first."""
    scopes = {"platform"}
    if device_type:
        scopes.add(f"device:{device_type}")
    if fault_code:
        scopes.add(f"fault:{fault_code}")
    return [p for p in index().values() if p.scope in scopes]


def _toc(items: Sequence[Passage]) -> str:
    return "\n".join(f"{p.id} | {p.doc_vi} › {p.section_vi}" for p in items)


def _pick_schema(items: Sequence[Passage]) -> dict:
    return {
        "type": "object",
        "properties": {
            "passages": {"type": "array", "items": {"type": "string", "enum": [p.id for p in items]}, "maxItems": MAX_PICKED},
        },
        "required": ["passages"],
        "additionalProperties": False,
    }


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "grounded": {"type": "boolean"},
        "reply": {"type": "string", "maxLength": ANSWER_MAX},
    },
    "required": ["grounded", "reply"],
    "additionalProperties": False,
}


async def answer(
    brain, client: httpx.AsyncClient, history, device_type: Optional[str], fault_code: Optional[str], fault_name: Optional[str] = None
) -> Answer:
    """`brain` is the ChatBrain whose server and call conventions are reused."""
    import time

    started = time.perf_counter()
    items = candidates(device_type, fault_code)
    transcript = [{"role": t.role, "content": t.text} for t in history]
    picked = await brain._call(
        client,
        [{"role": "system", "content": PICK_SYSTEM.format(toc=_toc(items))}, *transcript[-6:]],
        _pick_schema(items),
        120,
    )
    chosen = [index()[i] for i in dict.fromkeys(picked.get("passages") or []) if i in index()][:MAX_PICKED]
    if not chosen:
        return Answer(
            "Dạ câu này em chưa có thông tin chính xác ạ. Nếu máy nhà mình đang gặp vấn đề, anh/chị kể hiện tượng để em xem giúp nhé.",
            [], False, time.perf_counter() - started,
        )
    context = ""
    if device_type:
        context = f"Cuộc trò chuyện đang nói về {devices().get(device_type, device_type).lower()}"
        context += f", bệnh em đã chốt là {fault_name.lower()}." if fault_name else "."
    passages = "\n\n".join(f"[{p.doc_vi} › {p.section_vi}]\n{p.text_vi}" for p in chosen)
    raw = await brain._call(
        client,
        [{"role": "system", "content": ANSWER_SYSTEM.format(context=context, passages=passages)}, *transcript[-6:]],
        ANSWER_SCHEMA,
        260,
    )
    reply = " ".join((raw.get("reply") or "").split())[:ANSWER_MAX]
    return Answer(reply, chosen, bool(raw.get("grounded")), time.perf_counter() - started)
