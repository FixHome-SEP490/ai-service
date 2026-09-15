"""Gradio demo for the diagnosis pipeline.

Upload a photo, type a Vietnamese description, see the detection drawn on the
image next to the diagnosis. Two uses: checking training progress by eye during
development, and demonstrating the system without asking anyone to read JSON.

It talks to the running service over HTTP rather than importing the pipeline, so
what you see here is exactly what Backend will receive, and it works just as
well against a deployed instance.

    python -m uvicorn app.main:app --port 8000
    python tools/demo_app.py

Set AI_SERVICE_URL to point at a remote deployment.
"""

from __future__ import annotations

import io
import os
from typing import Any, Optional

import gradio as gr
import httpx
from PIL import Image, ImageDraw

SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 30.0

_URGENCY_COLOR = {"LOW": "#2e7d32", "MEDIUM": "#ef6c00", "HIGH": "#c62828"}


def _post_upload(image: Optional[Image.Image], description: str) -> dict[str, Any]:
    files = []
    if image is not None:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=90)
        files.append(("files", ("upload.jpg", buffer.getvalue(), "image/jpeg")))

    response = httpx.post(
        f"{SERVICE_URL}/api/v1/diagnosis/analyze-upload",
        data={"description": description},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    return response.json()


def _draw_detection(image: Optional[Image.Image], result: dict[str, Any]) -> Optional[Image.Image]:
    """Draw the detector box so the device it locked onto is visible at a glance."""
    device = result.get("device")
    if image is None or not device or not device.get("boundingBox"):
        return image

    canvas = image.convert("RGB").copy()
    box = device["boundingBox"]
    # The service downscales on intake, so box coordinates are in the scaled
    # frame; rescale them back onto the image the user actually uploaded.
    scale = max(canvas.width, canvas.height) / 1024 if max(canvas.width, canvas.height) > 1024 else 1
    x, y = box["x"] * scale, box["y"] * scale
    w, h = box["width"] * scale, box["height"] * scale

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x, y, x + w, y + h], outline="#00c853", width=max(3, canvas.width // 250))
    label = f"{device['nameVi']} {device['confidence']:.0%}"
    draw.rectangle([x, max(0, y - 28), x + 9 * len(label), y], fill="#00c853")
    draw.text((x + 4, max(2, y - 24)), label, fill="black")
    return canvas


def _render(result: dict[str, Any]) -> str:
    if "code" in result:
        return f"### Lỗi `{result['code']}`\n\n{result.get('message', '')}"

    if result.get("status") == "needs_clarification":
        clar = result.get("clarification") or {}
        questions = "\n".join(f"- {q}" for q in clar.get("questionsVi", []))
        groups = ", ".join(clar.get("serviceGroupCodes", []))
        return (
            "### Cần làm rõ thêm\n\n"
            f"Độ tin cậy {result.get('confidence', 0):.0%}, chưa đủ để kết luận.\n\n"
            f"{questions}\n\nNhóm dịch vụ để chọn thủ công: {groups}"
        )

    lines: list[str] = []
    device = result.get("device")
    if device:
        lines.append(f"### {device['nameVi']} — {device['confidence']:.0%}")
    else:
        lines.append("### Không có ảnh, chẩn đoán theo mô tả")

    conditions = result.get("visibleConditions") or []
    if conditions:
        lines.append("\n**Dấu hiệu nhìn thấy trên ảnh**")
        lines += [f"- {c['nameVi']} ({c['confidence']:.0%})" for c in conditions]

    faults = result.get("suspectedFaults") or []
    if faults:
        lines.append("\n**Nghi ngờ hư hỏng**")
        lines += [f"- {f['nameVi']} ({f['confidence']:.0%}) — từ {f['source']}" for f in faults]

    services = result.get("recommendedServices") or []
    if services:
        lines.append("\n**Dịch vụ gợi ý**")
        lines += [f"- `{s['serviceCode']}` {s['nameVi']}" for s in services]
    else:
        lines.append("\n_Chưa có bảng dịch vụ của Backend nên phần gợi ý dịch vụ để trống._")

    actions = result.get("suggestedActionsVi") or []
    if actions:
        lines.append("\n**Nên làm ngay**")
        lines += [f"- {a}" for a in actions]

    price = result.get("priceEstimate")
    if price:
        # No ceiling means the tables cannot price the job, not that it is free.
        if price.get("max") is None:
            lines.append(
                f"\n**Giá tham khảo** từ {price['min']:,} {price['currency']}, "
                "phần còn lại cần kỹ thuật viên khảo sát tại chỗ"
            )
        elif price["max"] == price["min"]:
            lines.append(f"\n**Giá tham khảo** {price['min']:,} {price['currency']}")
        else:
            lines.append(
                f"\n**Giá tham khảo** {price['min']:,} – {price['max']:,} {price['currency']}"
            )

    urgency = result.get("urgency", "LOW")
    color = _URGENCY_COLOR.get(urgency, "#555")
    lines.append(f"\n**Mức khẩn cấp** <span style='color:{color}'>{urgency}</span>")
    lines.append(f"\n**Độ tin cậy chung** {result.get('confidence', 0):.0%}")
    lines.append(f"\n---\n_{result.get('disclaimerVi', '')}_")
    return "\n".join(lines)


def diagnose(image: Optional[Image.Image], description: str):
    if not description or not description.strip():
        return image, "Nhập mô tả sự cố trước đã.", {}
    try:
        result = _post_upload(image, description.strip())
    except httpx.HTTPError as exc:
        return image, f"Không gọi được service tại {SERVICE_URL}\n\n`{exc}`", {}
    return _draw_detection(image, result), _render(result), result


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
    with gr.Blocks(title="FixHome AI — Demo") as demo:
        gr.Markdown(
            "# FixHome AI Service\n"
            f"Đang gọi `{SERVICE_URL}`. "
            "Chẩn đoán dùng ảnh để nhận thiết bị và mô tả để suy ra hư hỏng."
        )

        with gr.Tab("Chẩn đoán"):
            with gr.Row():
                with gr.Column():
                    image_in = gr.Image(type="pil", label="Ảnh thiết bị")
                    description_in = gr.Textbox(
                        label="Mô tả sự cố",
                        placeholder="Máy lạnh mới vệ sinh tháng trước mà vẫn không mát",
                        lines=3,
                    )
                    run = gr.Button("Chẩn đoán", variant="primary")
                with gr.Column():
                    image_out = gr.Image(label="Vùng thiết bị phát hiện được")
                    result_md = gr.Markdown()
            raw_json = gr.JSON(label="Response thô (đúng cái Backend nhận được)")
            run.click(
                diagnose,
                inputs=[image_in, description_in],
                outputs=[image_out, result_md, raw_json],
            )

        with gr.Tab("Hỏi đáp"):
            question_in = gr.Textbox(
                label="Câu hỏi",
                placeholder="Bao lâu nên vệ sinh máy lạnh một lần?",
                lines=2,
            )
            ask_btn = gr.Button("Hỏi", variant="primary")
            answer_md = gr.Markdown()
            answer_json = gr.JSON(label="Response thô")
            ask_btn.click(ask, inputs=question_in, outputs=[answer_md, answer_json])

    return demo


if __name__ == "__main__":
    build_demo().launch(server_name="127.0.0.1", server_port=7860)
