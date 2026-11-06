"""Chat2Provider behind the real endpoints, against a fake model server."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_provider import get_ai_provider
from app.services.chat2.brain import REQUEST, SYMPTOM, UNCLEAR
from app.services.chat2.provider import STATE_VERSION, Chat2Provider
from app.services.pipeline.detector import StubDetector
from app.services.pipeline.knowledge_base import get_knowledge_base

# 1x1 PNG
PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class FakeModel:
    """Answers the router and the diagnosis from scripted replies, records every call."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append(body)
        reply = self.replies.pop(0)
        text = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def _turn(**kw):
    base = {"need": "", "need_kind": SYMPTOM, "fault_code": "NONE", "decision": "conclude",
            "service_code": "AC-01", "reply": "", "options": [], "confidence": 0.8}
    return {**base, **kw}


@pytest.fixture(autouse=True)
def model_server(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VLM_BASE_URL", "http://model.test")


@pytest.fixture
def client_with():
    def make(*replies, device="air_conditioner"):
        model = FakeModel(*replies)
        provider = Chat2Provider(
            detector=StubDetector(get_knowledge_base(), device_type=device),
            transport=httpx.MockTransport(model),
        )
        app.dependency_overrides[get_ai_provider] = lambda: provider
        return TestClient(app), model

    yield make
    app.dependency_overrides.clear()


def test_photo_and_short_symptom_conclude_with_the_bookable_service(client_with):
    client, model = client_with(
        {"devices": [], "intent": "repair"},
        _turn(need="mùi hôi, bẩn", fault_code="AC_DIRTY_FILTER", service_code="AC-02",
              reply="Dạ máy lạnh bẩn dàn lạnh nên có mùi hôi ạ. Anh/chị bấm Đặt thợ nhé."),
    )
    r = client.post("/api/v1/diagnosis/analyze", json={"description": "có mùi hôi như thối, rất bẩn", "images": [PNG]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "ok" and d["device"]["deviceType"] == "air_conditioner"
    assert d["device"]["source"] == "image"
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["AC-02"]
    assert d["suspectedFaults"][0]["faultCode"] == "AC_DIRTY_FILTER"
    assert d["priceEstimate"]["min"] > 0
    assert "199.000" not in d["messageVi"] and d["messageVi"].startswith("Dạ máy lạnh bẩn")
    assert d["diagnosticState"]["engine"] == STATE_VERSION
    assert d["photos"][0]["deviceType"] == "air_conditioner"
    # The model never receives the photograph.
    assert "image" not in json.dumps(model.calls)


def test_a_question_carries_quick_reply_options_and_no_service(client_with):
    client, _ = client_with(
        {"devices": ["washing_machine"], "intent": "repair"},
        _turn(need="", need_kind=UNCLEAR, decision="ask", service_code="WM-01",
              reply="Dạ máy giặt đang bị sao ạ", options=["Không vắt", "Không xả", "Kêu to"]),
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "máy giặt bị sao á"}).json()
    assert d["status"] == "needs_clarification"
    assert d["clarification"]["questionsVi"] == ["Dạ máy giặt đang bị sao ạ?"]
    assert d["clarification"]["answerOptionsVi"] == ["Không vắt", "Không xả", "Kêu to"]
    assert d["recommendedServices"] == []
    assert d["messageVi"] is None


def test_the_session_carries_the_conversation_to_the_next_turn(client_with):
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need_kind=UNCLEAR, decision="ask", reply="Dạ máy lạnh đang bị sao ạ?", options=["Không mát", "Chảy nước"]),
        {"devices": [], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh có vấn đề"}).json()
    second = client.post(
        "/api/v1/diagnosis/analyze", json={"description": "Chảy nước", "sessionId": first["sessionId"]}
    ).json()
    assert second["sessionId"] == first["sessionId"] and second["status"] == "ok"
    sent = [m["content"] for m in model.calls[3]["messages"][1:]]
    assert sent == ["máy lạnh có vấn đề", "Dạ máy lạnh đang bị sao ạ?", "Chảy nước"]
    assert (first["stateVersion"], second["stateVersion"]) == (1, 2)


def test_a_restarted_service_resumes_from_the_state_backend_kept(client_with):
    client, model = client_with(
        {"devices": [], "intent": "repair"},
        _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01", reply="Dạ khả năng máy không vắt được do lỗi vắt ạ."),
        device=None,
    )
    state = {"engine": STATE_VERSION, "photo_device": "washing_machine", "photo_confidence": 0.9, "version": 7,
             "turns": [{"role": "user", "text": "máy giặt"}, {"role": "assistant", "text": "Dạ máy đang bị sao ạ?"}]}
    d = client.post(
        "/api/v1/diagnosis/analyze",
        json={"description": "không vắt", "sessionId": "abc", "diagnosticState": state},
    ).json()
    assert d["device"]["deviceType"] == "washing_machine" and d["recommendedServices"][0]["serviceCode"] == "WM-01"
    assert len(model.calls[1]["messages"]) == 4
    assert d["stateVersion"] == 8 and d["diagnosticState"]["version"] == 8


def test_two_appliances_come_back_as_devices(client_with):
    client, _ = client_with(
        {"devices": ["washing_machine", "air_conditioner"], "intent": "repair"},
        _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01", reply="Dạ máy giặt khả năng lỗi vắt ạ."),
        _turn(need="vệ sinh", need_kind=REQUEST, service_code="AC-02", reply="Dạ anh/chị bấm Đặt thợ để vệ sinh máy lạnh nhé."),
        device=None,
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "máy giặt không vắt, tiện vệ sinh máy lạnh"}).json()
    assert [x["deviceType"] for x in d["devices"]] == ["washing_machine", "air_conditioner"]
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["WM-01", "AC-02"]
    assert d["devices"][0]["isPrimary"] is True


def test_a_policy_question_is_answered_from_policy_passages(client_with):
    client, model = client_with(
        {"devices": [], "intent": "question"},
        "Dạ FixHome bảo hành theo từng dịch vụ, thợ sẽ ghi rõ khi hoàn tất ạ.",
        device=None,
    )
    d = client.post("/api/v1/chat/ask", json={"question": "bảo hành bao lâu vậy em"}).json()
    assert d["status"] in ("ok", "no_grounding")
    if d["status"] == "ok":
        assert d["citations"] and "bảo hành" in model.calls[1]["messages"][0]["content"].lower()


def test_an_appliance_question_on_ask_goes_through_the_diagnosis(client_with):
    client, _ = client_with(
        {"devices": ["air_conditioner"], "intent": "question"},
        {"devices": ["air_conditioner"], "intent": "question"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        device=None,
    )
    d = client.post("/api/v1/chat/ask", json={"question": "máy lạnh chảy nước là sao vậy em?"}).json()
    assert d["status"] == "ok" and d["recommendedServices"][0]["serviceCode"] == "AC-02"


def test_model_down_is_a_503_backend_turns_into_the_manual_path(client_with):
    def down(request):
        raise httpx.ConnectError("refused")

    provider = Chat2Provider(detector=StubDetector(get_knowledge_base()), transport=httpx.MockTransport(down))
    app.dependency_overrides[get_ai_provider] = lambda: provider
    r = TestClient(app).post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh không mát"})
    assert r.status_code == 503
    assert "refused" not in r.text
