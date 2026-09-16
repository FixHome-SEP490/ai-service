"""A one-to-one conversation with the FixHome assistant.

Not the test console. This is the thing a customer would use: one thread, one
message box, a photo attached only when there is one to attach. Everything the
assistant knows it learned in this thread — which appliance, what has already
been said, what has already been asked.

The distinction matters because the failures that annoy people are conversation
failures, and a form cannot show them. Being asked "nước có nóng nhưng lâu hơn
trước phải không?" right after writing "máy nước nóng không nóng" only looks
wrong when the two sit one above the other.

Routing is by whether there is a photograph and what the sentence is doing. A
question about cost or policy goes to the advisory surface, which answers from
the price tables and the policy text and refuses anything it cannot ground.
Anything else is a symptom, and goes to diagnosis.

    python -m uvicorn app.main:app --port 8000
    python tools/chat_app.py          # http://127.0.0.1:7870
"""

from __future__ import annotations

import io
import os
import re
import unicodedata
from typing import Any, Optional

import gradio as gr
import httpx
from PIL import Image

SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 120.0

_URGENCY_VI = {
    "LOW": "Không gấp",
    "MEDIUM": "Nên xử lý sớm",
    "HIGH": "Cần xử lý ngay",
}

_ASK_WORDS = (
    "gia", "tien", "bao nhieu", "chi phi", "bao lau", "bao hanh", "chinh sach",
    "co the", "the nao", "lam sao", "quy dinh", "huy", "doi lich", "thanh toan",
)
"""Openings that mean the customer is asking rather than describing.

A question about cost or policy sent to diagnosis comes back as three questions
about symptoms, which is the wrong surface answering the wrong question."""


def _fold(text: str) -> str:
    stripped = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in stripped if unicodedata.category(c) != "Mn").replace("đ", "d")


def _is_a_question(text: str) -> bool:
    folded = _fold(text)
    if "?" in text and not re.search(r"\b(hong|hu|khong|bi|keu|ro|chay)\b", folded):
        return True
    return any(word in folded for word in _ASK_WORDS)


def _as_jpeg(path: str) -> bytes:
    with Image.open(path) as image:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()


def _money(value: Optional[int]) -> str:
    return f"{value:,}đ".replace(",", ".") if value is not None else ""


def _reply_to_diagnosis(result: dict[str, Any]) -> str:
    if "code" in result:
        return (
            "Hiện em chưa kiểm tra được, anh/chị chọn dịch vụ thủ công giúp em nhé. "
            f"(`{result['code']}`)"
        )

    device = result.get("device")
    opening = ""
    if device:
        opening = f"Em xem thì đây là **{device['nameVi']}**. "

    if result.get("status") == "needs_clarification":
        questions = (result.get("clarification") or {}).get("questionsVi", [])
        asked = "\n".join(f"- {q}" for q in questions)
        return f"{opening}Em hỏi thêm cho chắc ạ:\n\n{asked}"

    faults = result.get("suspectedFaults") or []
    lines = [opening + "Nhiều khả năng là:"]
    lines += [f"- **{f['nameVi']}**" for f in faults]

    price = result.get("priceEstimate") or {}
    if price.get("max") is None and price.get("min"):
        lines.append(
            f"\nChi phí dự kiến từ {_money(price['min'])}, phần còn lại kỹ thuật viên "
            "phải xem tận nơi mới tính được ạ."
        )
    elif price.get("max") == price.get("min"):
        lines.append(f"\nChi phí dự kiến {_money(price.get('min'))}.")
    elif price.get("min") is not None:
        lines.append(
            f"\nChi phí dự kiến khoảng {_money(price['min'])} tới {_money(price['max'])}."
        )

    actions = result.get("suggestedActionsVi") or []
    if actions:
        lines.append("\nAnh/chị làm giúp em mấy việc này trước ạ:")
        lines += [f"- {a}" for a in actions]

    urgency = _URGENCY_VI.get(result.get("urgency", "LOW"))
    if result.get("urgency") in ("MEDIUM", "HIGH"):
        lines.append(f"\n**{urgency}.**")

    lines.append(f"\n_{result.get('disclaimerVi', '')}_")
    return "\n".join(lines)


def _reply_to_question(result: dict[str, Any]) -> str:
    answer = result.get("answerVi") or ""
    if result.get("status") != "ok":
        return answer
    citations = result.get("citations") or []
    if citations:
        sources = ", ".join(c["titleVi"] for c in citations[:3])
        return f"{answer}\n\n_Theo: {sources}_"
    return answer


def respond(message: dict[str, Any], history: list, session_id: str):
    text = (message.get("text") or "").strip()
    files = message.get("files") or []
    if not text and not files:
        return history, session_id, None

    shown = text or "(gửi ảnh)"
    history = history + [{"role": "user", "content": shown}]

    try:
        if files:
            data = {"description": text or "Anh/chị xem giúp em thiết bị này bị gì ạ"}
            if session_id:
                data["sessionId"] = session_id
            uploads = [("files", ("photo.jpg", _as_jpeg(files[0]), "image/jpeg"))]
            result = httpx.post(
                f"{SERVICE_URL}/api/v1/diagnosis/analyze-upload",
                data=data,
                files=uploads,
                timeout=REQUEST_TIMEOUT,
            ).json()
            reply = _reply_to_diagnosis(result)
        elif _is_a_question(text):
            body = {"question": text}
            if session_id:
                body["sessionId"] = session_id
            result = httpx.post(
                f"{SERVICE_URL}/api/v1/chat/ask", json=body, timeout=REQUEST_TIMEOUT
            ).json()
            reply = _reply_to_question(result)
        else:
            data = {"description": text}
            if session_id:
                data["sessionId"] = session_id
            result = httpx.post(
                f"{SERVICE_URL}/api/v1/diagnosis/analyze-upload",
                data=data,
                timeout=REQUEST_TIMEOUT,
            ).json()
            reply = _reply_to_diagnosis(result)
    except httpx.HTTPError as exc:
        reply = f"Em chưa kết nối được tới máy chủ ạ.\n\n`{exc}`"
        result = {}

    history = history + [{"role": "assistant", "content": reply}]
    return history, result.get("sessionId") or session_id, None


def reset():
    """A new thread, and a new session with it.

    Keeping the old session id would carry the previous appliance and the
    previous answers into a conversation that looks empty, which is worse than
    forgetting.
    """
    return [], "", None


def build_app() -> gr.Blocks:
    with gr.Blocks(title="FixHome — Trợ lý sửa chữa", fill_height=True) as app:
        gr.Markdown(
            "## Trợ lý FixHome\n"
            "Anh/chị mô tả thiết bị đang gặp vấn đề, gửi kèm ảnh nếu có. "
            "Hỏi về giá hoặc chính sách cũng được ạ."
        )
        session = gr.State("")

        chat = gr.Chatbot(
            type="messages",
            height=520,
            show_label=False,
            avatar_images=(None, None),
            value=[
                {
                    "role": "assistant",
                    "content": (
                        "Dạ em chào anh/chị. Thiết bị nhà mình đang gặp vấn đề gì ạ? "
                        "Anh/chị tả giúp em hiện tượng, có ảnh thì gửi kèm luôn ạ."
                    ),
                }
            ],
        )
        box = gr.MultimodalTextbox(
            show_label=False,
            placeholder="Nhập tin nhắn, kèm ảnh nếu có...",
            file_types=["image"],
            file_count="single",
        )
        with gr.Row():
            clear = gr.Button("Bắt đầu lại", scale=1)
            session_box = gr.Textbox(
                label="Session", interactive=False, scale=3, container=False
            )

        box.submit(
            respond, inputs=[box, chat, session], outputs=[chat, session, box]
        ).then(lambda s: s, inputs=session, outputs=session_box)
        clear.click(reset, outputs=[chat, session, box])

    return app


if __name__ == "__main__":
    build_app().launch(server_name="127.0.0.1", server_port=7870)
