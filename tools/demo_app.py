"""Test and monitoring console for the AI service.

Three things an operator needs and a JSON response does not give.

**Chẩn đoán** is the customer's view: a photo, a description, and what comes
back. It keeps the session id between turns, so the assistant can ask which
appliance it is and actually receive the answer — the behaviour that separates a
conversation from a form, and the one a single-shot form can never show.

**Đường đi gói tin** is the operator's view. The pipeline is four stages and a
failure in any of them looks identical from outside: the assistant asks a
question. Without this, "it asked again" could be the detector finding nothing,
retrieval returning an empty shortlist, the model naming codes outside it, or
the model server being unreachable — four problems, four different fixes, one
symptom. The trace names which stage, how long it took, and what it produced.

**Hỏi đáp** is the policy surface, which never recommends a service.

It talks to the service over HTTP rather than importing the pipeline, so what is
shown here is exactly what Backend receives.

    python -m uvicorn app.main:app --port 8000
    python tools/demo_app.py

Set AI_SERVICE_URL to point at a deployment.
"""

from __future__ import annotations

import io
import os
import time
from typing import Any, Optional

import gradio as gr
import httpx
from PIL import Image, ImageDraw

SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 120.0

_URGENCY_COLOR = {"LOW": "#2e7d32", "MEDIUM": "#ef6c00", "HIGH": "#c62828"}

_STAGE_ROLE_VI = {
    "session": "Trí nhớ hội thoại — ghép lời khách qua nhiều lượt, nhớ thiết bị đã biết",
    "detector": "YOLO11s — nhận loại thiết bị từ ảnh và cắt vùng thiết bị",
    "retrieval": "RAG — tra bảng bệnh, rút danh sách ngắn để Qwen chọn",
    "vlm": "Qwen2.5-VL — đọc ảnh cắt và lời khách, chọn mã trong danh sách",
    "knowledge_base": "Bảng bệnh — dịch mã sang tiếng Việt, ghép giá, việc nên làm",
}


def _post(
    image: Optional[Image.Image],
    description: str,
    session_id: str,
    trace: bool,
) -> tuple[dict[str, Any], float]:
    files = []
    if image is not None:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=90)
        files.append(("files", ("upload.jpg", buffer.getvalue(), "image/jpeg")))

    data = {"description": description, "includeTrace": "true" if trace else "false"}
    if session_id:
        data["sessionId"] = session_id

    started = time.perf_counter()
    response = httpx.post(
        f"{SERVICE_URL}/api/v1/diagnosis/analyze-upload",
        data=data,
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    return response.json(), (time.perf_counter() - started) * 1000


def _draw_detection(image: Optional[Image.Image], result: dict[str, Any]):
    device = result.get("device")
    if image is None or not device or not device.get("boundingBox"):
        return image

    canvas = image.convert("RGB").copy()
    box = device["boundingBox"]
    # The service downscales on intake, so the box is in the scaled frame.
    longest = max(canvas.width, canvas.height)
    scale = longest / 1024 if longest > 1024 else 1
    x, y = box["x"] * scale, box["y"] * scale
    w, h = box["width"] * scale, box["height"] * scale

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x, y, x + w, y + h], outline="#00c853", width=max(3, canvas.width // 250))
    label = f"{device['nameVi']} {device['confidence']:.0%}"
    draw.rectangle([x, max(0, y - 28), x + 9 * len(label), y], fill="#00c853")
    draw.text((x + 4, max(2, y - 24)), label, fill="black")
    return canvas


def _price_line(price: Optional[dict[str, Any]]) -> str:
    if not price:
        return ""
    currency = price.get("currency", "VND")
    if price.get("max") is None:
        return (
            f"\n**Giá tham khảo** từ {price['min']:,} {currency}, "
            "phần còn lại cần kỹ thuật viên khảo sát tại chỗ"
        )
    if price["max"] == price["min"]:
        return f"\n**Giá tham khảo** {price['min']:,} {currency}"
    return f"\n**Giá tham khảo** {price['min']:,} – {price['max']:,} {currency}"


def _render(result: dict[str, Any]) -> str:
    if "code" in result:
        return f"### Lỗi `{result['code']}`\n\n{result.get('message', '')}"

    lines: list[str] = []
    device = result.get("device")
    if device:
        seen = "ảnh" if device.get("source") == "image" else "mô tả"
        lines.append(f"### {device['nameVi']} — {device['confidence']:.0%} (từ {seen})")
    else:
        lines.append("### Chưa xác định thiết bị")

    if result.get("status") == "needs_clarification":
        clar = result.get("clarification") or {}
        questions = "\n".join(f"- {q}" for q in clar.get("questionsVi", []))
        lines.append(
            f"\n**Chưa đủ chắc ({result.get('confidence', 0):.0%}), hỏi lại khách:**\n\n{questions}"
        )
        lines.append("\n_Trả lời vào ô mô tả rồi bấm Gửi — phiên được giữ nguyên._")
        return "\n".join(lines)

    for title, key, fmt in [
        ("Dấu hiệu nhìn thấy", "visibleConditions", lambda c: f"- {c['nameVi']} ({c['confidence']:.0%})"),
        ("Nghi ngờ hư hỏng", "suspectedFaults", lambda f: f"- {f['nameVi']} ({f['confidence']:.0%})"),
        ("Dịch vụ gợi ý", "recommendedServices", lambda s: f"- `{s['serviceCode']}` {s['nameVi']}"),
    ]:
        items = result.get(key) or []
        if items:
            lines.append(f"\n**{title}**")
            lines += [fmt(i) for i in items]

    if not (result.get("recommendedServices") or []):
        lines.append("\n_Backend chưa chốt bảng dịch vụ nên phần gợi ý để trống._")

    actions = result.get("suggestedActionsVi") or []
    if actions:
        lines.append("\n**Nên làm ngay**")
        lines += [f"- {a}" for a in actions]

    lines.append(_price_line(result.get("priceEstimate")))

    urgency = result.get("urgency", "LOW")
    color = _URGENCY_COLOR.get(urgency, "#555")
    lines.append(f"\n**Mức khẩn cấp** <span style='color:{color}'>{urgency}</span>")
    lines.append(f"\n**Độ tin cậy chung** {result.get('confidence', 0):.0%}")
    lines.append(f"\n---\n_{result.get('disclaimerVi', '')}_")
    return "\n".join(lines)


def _render_trace(result: dict[str, Any], round_trip_ms: float) -> str:
    stages = result.get("trace") or []
    if not stages:
        return "_Chưa có gói tin nào. Gửi một yêu cầu ở tab Chẩn đoán._"

    info = result.get("modelInfo") or {}
    lines = [
        f"### Gói tin đi qua {len(stages)} chặng, tổng {round_trip_ms:.0f}ms",
        "",
        f"Phiên `{result.get('sessionId', '-')}` · kết quả **{result.get('status')}**",
        "",
        "| Chặng | Thời gian | Kết quả | Vai trò |",
        "|---|---|---|---|",
    ]
    for stage in stages:
        mark = "✅" if stage["ok"] else "⛔"
        role = _STAGE_ROLE_VI.get(stage["name"], "")
        lines.append(f"| `{stage['name']}` | {stage['ms']}ms | {mark} {stage['summaryVi']} | {role} |")

    served = sum(s["ms"] for s in stages)
    lines += [
        "",
        f"Trong service {served}ms, còn lại {max(0, round_trip_ms - served):.0f}ms là "
        "mạng, giải mã ảnh và dựng phản hồi.",
        "",
        "### Chi tiết từng chặng",
    ]
    for stage in stages:
        lines.append(f"\n**`{stage['name']}`** — {stage['summaryVi']}")
        for key, value in (stage.get("detail") or {}).items():
            if value in (None, [], {}, ""):
                continue
            lines.append(f"- {key}: `{value}`")

    lines += [
        "",
        "### Phiên bản đang chạy",
        f"- Detector: `{info.get('detector') or 'chưa nạp weights, đang dùng stub'}`",
        f"- Qwen: `{info.get('vlm') or 'chưa cấu hình VLM_BASE_URL'}`",
        f"- Bảng bệnh: `{info.get('knowledgeBaseVersion') or '-'}`",
    ]
    return "\n".join(lines)


def diagnose(image, description, session_id, keep_session):
    if not description or not description.strip():
        return image, "Nhập mô tả sự cố trước đã.", "", session_id, {}
    try:
        result, ms = _post(
            image, description.strip(), session_id if keep_session else "", trace=True
        )
    except httpx.HTTPError as exc:
        return image, f"Không gọi được service tại {SERVICE_URL}\n\n`{exc}`", "", session_id, {}

    return (
        _draw_detection(image, result),
        _render(result),
        _render_trace(result, ms),
        result.get("sessionId") or "",
        result,
    )


def ask(question: str):
    if not question or not question.strip():
        return "Nhập câu hỏi trước đã.", {}
    try:
        response = httpx.post(
            f"{SERVICE_URL}/api/v1/chat/ask",
            json={"question": question.strip()},
            timeout=REQUEST_TIMEOUT,
        )
        result = response.json()
    except httpx.HTTPError as exc:
        return f"Không gọi được service tại {SERVICE_URL}\n\n`{exc}`", {}

    if result.get("status") != "ok":
        return f"**Không trả lời được**\n\n{result.get('answerVi', '')}", result

    citations = "\n".join(
        f"- `{c['docId']}` {c['titleVi']} ({c['score']:.2f})"
        for c in result.get("citations", [])
    )
    return f"{result['answerVi']}\n\n**Nguồn trích dẫn**\n{citations}", result


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="FixHome AI — Test & Monitor") as demo:
        gr.Markdown(
            "# FixHome AI Service\n"
            f"Đang gọi `{SERVICE_URL}`. YOLO nhận **vật**, Qwen suy ra **bệnh**, "
            "RAG cấp **lời**. Mọi câu tiếng Việt đều lấy từ bảng bệnh, không phải "
            "model tự viết."
        )
        session_state = gr.State("")

        with gr.Tab("Chẩn đoán"):
            with gr.Row():
                with gr.Column():
                    image_in = gr.Image(type="pil", label="Ảnh thiết bị")
                    description_in = gr.Textbox(
                        label="Mô tả sự cố, hoặc câu trả lời cho câu hỏi của AI",
                        placeholder="Máy lạnh chạy cả ngày mà không mát",
                        lines=3,
                    )
                    keep = gr.Checkbox(
                        value=True,
                        label="Giữ phiên hội thoại (bỏ tick để bắt đầu lại từ đầu)",
                    )
                    run = gr.Button("Gửi", variant="primary")
                    session_box = gr.Textbox(label="Session", interactive=False)
                with gr.Column():
                    image_out = gr.Image(label="Vùng thiết bị phát hiện được")
                    result_md = gr.Markdown()
            raw_json = gr.JSON(label="Response thô — đúng cái Backend nhận được")

        with gr.Tab("Đường đi gói tin"):
            gr.Markdown(
                "Mỗi yêu cầu ở tab Chẩn đoán được ghi lại ở đây: qua chặng nào, "
                "mất bao lâu, chặng đó làm ra cái gì. Một chặng hỏng thì nhìn từ "
                "ngoài đều giống nhau — AI hỏi lại khách — nên bảng này là chỗ "
                "duy nhất phân biệt được bốn nguyên nhân khác nhau."
            )
            trace_md = gr.Markdown("_Chưa có gói tin nào._")

        with gr.Tab("Hỏi đáp chính sách"):
            gr.Markdown(
                "Mặt riêng, chỉ trả lời từ tài liệu đã truy xuất. Không gợi ý "
                "dịch vụ, không tạo ý định đặt lịch. Không có căn cứ thì từ chối "
                "chứ không bịa."
            )
            question_in = gr.Textbox(
                label="Câu hỏi",
                placeholder="Bao lâu nên vệ sinh máy lạnh một lần?",
                lines=2,
            )
            ask_btn = gr.Button("Hỏi", variant="primary")
            answer_md = gr.Markdown()
            answer_json = gr.JSON(label="Response thô")

        run.click(
            diagnose,
            inputs=[image_in, description_in, session_state, keep],
            outputs=[image_out, result_md, trace_md, session_state, raw_json],
        ).then(lambda s: s, inputs=session_state, outputs=session_box)

        ask_btn.click(ask, inputs=question_in, outputs=[answer_md, answer_json])

    return demo


if __name__ == "__main__":
    build_demo().launch(server_name="127.0.0.1", server_port=7860)
