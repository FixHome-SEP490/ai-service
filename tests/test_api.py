"""Endpoint tests.

These pin the wire contract Backend and the chatbot depend on: camelCase keys,
both image entry points reaching the same pipeline, and failures that still say
fallback is allowed.
"""

import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _jpeg(width: int = 800, height: int = 600) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 80, 120)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_analyze_accepts_data_uri_and_answers_in_camel_case():
    payload = {
        "requestId": "req_test_1",
        "description": "Máy lạnh không mát dù mới vệ sinh tháng trước",
        "images": ["data:image/jpeg;base64," + base64.b64encode(_jpeg()).decode()],
    }
    response = client.post("/api/v1/diagnosis/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["requestId"] == "req_test_1"
    assert "suspectedFaults" in body
    assert "disclaimerVi" in body
    assert body["device"]["boundingBox"]["width"] > 0


def test_multipart_upload_reaches_the_same_pipeline():
    # The stub detector reports the first catalog device, so the description
    # has to match that device for retrieval to find any candidate fault.
    response = client.post(
        "/api/v1/diagnosis/analyze-upload",
        data={"description": "Máy lạnh chạy lâu mới mát, hơi ra yếu"},
        files={"files": ("photo.jpg", _jpeg(), "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["device"] is not None
    assert body["disclaimerVi"]


def test_multipart_without_any_file_still_diagnoses_from_text():
    response = client.post(
        "/api/v1/diagnosis/analyze-upload",
        data={"description": "Ổ cắm có mùi cháy khét và nóng bất thường"},
    )

    assert response.status_code == 200
    assert response.json()["device"] is None


def test_oversized_image_is_refused_with_a_stable_code(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "IMAGE_MAX_BYTES", 500)
    response = client.post(
        "/api/v1/diagnosis/analyze",
        json={
            "description": "Máy giặt không vắt",
            "images": [base64.b64encode(_jpeg()).decode()],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_IMAGE"
    assert body["fallbackAllowed"] is True


def test_errors_never_leak_internal_detail():
    """Public failures carry a safe message, never exception text or paths."""
    response = client.post(
        "/api/v1/diagnosis/analyze",
        json={"description": "abc", "images": ["bm90IGFuIGltYWdl"]},
    )

    assert response.status_code == 422
    serialized = response.text.lower()
    for leak in ("traceback", "unidentifiedimage", "site-packages", ".py", "errno"):
        assert leak not in serialized


def test_unknown_request_field_is_rejected():
    response = client.post(
        "/api/v1/diagnosis/analyze",
        json={"description": "Tủ lạnh không lạnh", "bogusField": True},
    )
    assert response.status_code == 422


def test_chat_endpoint_returns_citations():
    response = client.post(
        "/api/v1/chat/ask",
        json={"question": "Bao lâu nên vệ sinh máy lạnh một lần?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["citations"]
    assert body["citations"][0]["docId"]
