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


def test_a_platform_question_is_answered_from_the_knowledge_index(client_with):
    client, model = client_with(
        {"devices": [], "intent": "question"},
        {"passages": ["system:tong-quan-fixhome:2", "catalog:services"]},
        {"quote": "FixHome là nền tảng kết nối", "grounded": True, "reply": "Dạ FixHome là nền tảng kết nối anh/chị với thợ sửa đồ gia dụng tại nhà ạ."},
        {"supported": True},
        device=None,
    )
    d = client.post("/api/v1/chat/ask", json={"question": "fixhome là gì vậy em"}).json()
    assert d["status"] == "ok" and d["answerVi"].startswith("Dạ FixHome")
    assert [c["docId"] for c in d["citations"]] == ["system:tong-quan-fixhome:2", "catalog:services"]
    toc = model.calls[1]["messages"][0]["content"]
    assert "catalog:services" in toc and "device:air_conditioner" not in toc
    passages = model.calls[2]["messages"][0]["content"]
    assert "FixHome đang nhận các dịch vụ sau" in passages


def test_nothing_picked_says_so_instead_of_guessing(client_with):
    client, model = client_with({"devices": [], "intent": "question"}, {"passages": []}, device=None)
    d = client.post("/api/v1/chat/ask", json={"question": "fixhome có cho vay trả góp không"}).json()
    assert d["status"] == "no_grounding" and "chưa có thông tin" in d["answerVi"]
    assert len(model.calls) == 2


def test_a_follow_up_question_is_asked_about_the_fault_just_concluded(client_with):
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": [], "intent": "question"},
        {"passages": ["fault:AC_DRAIN_BLOCKED:0"]},
        {"quote": "thông ống trong một buổi", "grounded": True, "reply": "Dạ thông ống thoát nước thường làm xong trong một buổi ạ."},
        {"supported": True},
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "sửa có lâu không em", "sessionId": first["sessionId"]}).json()
    assert d["status"] == "ok" and d["messageVi"].startswith("Dạ thông ống")
    # The booking bar keeps the service already offered.
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["AC-02"]
    toc = model.calls[3]["messages"][0]["content"]
    assert "fault:AC_DRAIN_BLOCKED" in toc and "device:air_conditioner" in toc
    assert "nghẹt đường thoát nước" in model.calls[4]["messages"][0]["content"]


def test_asking_for_a_technician_after_a_conclusion_points_to_the_button(client_with):
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": [], "intent": "book"},
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "ok đặt thợ luôn em", "sessionId": first["sessionId"]}).json()
    assert "Đặt thợ ngay" in d["messageVi"] and "vệ sinh điều hòa" in d["messageVi"]
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["AC-02"]
    assert len(model.calls) == 3


@pytest.mark.parametrize("latest,intent", [("Vậy giờ em thấy sao?", "question"), ("Không.", "question"), ("đúng rồi", "greeting")])
def test_asking_for_the_verdict_again_restates_it(client_with, latest, intent):
    """Live 07/11: these went to the question tier, which answered with a price table."""
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": [], "intent": intent},
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": latest, "sessionId": first["sessionId"]}).json()
    assert d["messageVi"].startswith("Dạ theo những gì anh/chị kể, máy lạnh khả năng cao bị nghẹt")
    assert "Đặt thợ ngay" in d["messageVi"] and "000" not in d["messageVi"]
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["AC-02"]
    assert len(model.calls) == 3


def test_a_follow_up_with_something_specific_is_answered_as_a_question(client_with):
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": [], "intent": "question"},
        {"passages": ["fault:AC_DRAIN_BLOCKED:0"]},
        {"quote": "không phải do gas", "grounded": True, "reply": "Dạ chảy nước thường không phải do thiếu gas ạ."},
        {"supported": True},
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "vậy có phải hết gas không em", "sessionId": first["sessionId"]}).json()
    assert d["messageVi"].startswith("Dạ chảy nước thường không phải")
    assert len(model.calls) == 6


def test_an_answer_its_quote_does_not_support_says_only_what_is_known(client_with):
    """07/11: "có thợ nữ không" came back "Có, ..." from a sentence about choosing technicians."""
    client, model = client_with(
        {"devices": [], "intent": "question"},
        {"passages": ["system:cau-hoi-thuong-gap:0"]},
        {"quote": "Khách xem được danh sách thợ phù hợp rồi chọn những thợ mình ưu tiên.", "grounded": True,
         "reply": "Có, anh/chị chọn được thợ nữ trong danh sách. Em chưa có thông tin cụ thể về thợ nữ ạ."},
        {"supported": False},
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "có thợ nữ không em"}).json()
    assert d["messageVi"] == "Em chưa có thông tin cụ thể về thợ nữ ạ."
    # The reply is checked against the passages shown, not against the quote alone.
    verify = model.calls[3]["messages"]
    assert "chọn được thợ nữ" in verify[1]["content"] and "Đoạn tài liệu" in verify[0]["content"]


def test_an_unsupported_answer_with_no_admission_says_there_is_no_information(client_with):
    client, _ = client_with(
        {"devices": [], "intent": "question"},
        {"passages": ["system:cau-hoi-thuong-gap:0"]},
        {"quote": "", "grounded": False, "reply": "Thợ sẽ mang đầy đủ đồ nghề và linh kiện cần thiết."},
        {"supported": False},
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "thợ có mang đồ nghề không"}).json()
    assert d["messageVi"] == "Dạ câu này em chưa có thông tin chính xác ạ."


@pytest.mark.parametrize("latest", ["sửa có lâu không em", "thế bảo hành bao lâu", "cái đó có nguy hiểm không em"])
def test_a_question_about_the_fault_is_not_mistaken_for_asking_the_verdict(latest):
    from app.services.chat2.brain import asks_for_the_verdict
    from app.services.chat2.menu import menu_for

    assert not asks_for_the_verdict(latest, menu_for("air_conditioner"))


def test_a_new_symptom_after_a_conclusion_is_diagnosed_again(client_with):
    client, model = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": [], "own_problem": True, "intent": "repair"},
        _turn(need="chảy nước, kêu to", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ vẫn khả năng nghẹt ống thoát nước ạ."),
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "à mà nó còn kêu to nữa", "sessionId": first["sessionId"]}).json()
    assert d["messageVi"].startswith("Dạ vẫn khả năng") and len(model.calls) == 4


def test_a_short_reply_before_any_conclusion_goes_back_to_the_diagnosis(client_with):
    client, model = client_with(
        {"devices": ["washing_machine"], "intent": "repair"},
        _turn(need_kind=UNCLEAR, decision="ask", service_code="WM-01", reply="Dạ máy có vào nước không ạ?", options=["Có", "Không"]),
        {"devices": [], "intent": "repair"},
        _turn(need="không vào nước", fault_code="WM_NO_WATER_INLET", service_code="WM-01", reply="Dạ khả năng máy không cấp nước ạ."),
        device="washing_machine",
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy giặt bị sao á"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "Không", "sessionId": first["sessionId"]}).json()
    assert d["status"] == "ok" and d["suspectedFaults"][0]["faultCode"] == "WM_NO_WATER_INLET"


def test_an_appliance_question_on_ask_goes_through_the_diagnosis(client_with):
    client, _ = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
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


def test_a_bare_no_to_the_assistants_own_question_goes_back_to_the_diagnosis(client_with):
    client, model = client_with(
        {"devices": ["refrigerator"], "intent": "repair"},
        _turn(need_kind=UNCLEAR, decision="ask", service_code="FR-01", reply="Dạ tủ lạnh có hiện tượng gì ạ?", options=["Không lạnh", "Ồn"]),
        {"devices": [], "intent": "question"},
        _turn(need_kind=UNCLEAR, decision="ask", service_code="FR-01", reply="Dạ ngăn đá có còn đông đá không ạ?", options=["Có", "Không"]),
        device="refrigerator",
    )
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "tủ lạnh hư rồi em ơi"}).json()
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "Không", "sessionId": first["sessionId"]}).json()
    assert d["status"] == "needs_clarification" and len(model.calls) == 4


def test_an_appliance_outside_the_catalogue_is_declined_by_name(client_with):
    """07/11: "nồi cơm điện nấu cơm bị sống" was asked which appliance it meant."""
    client, model = client_with(
        {"devices": [], "own_problem": True, "intent": "repair", "other_appliance": "nồi cơm điện"},
        device=None,
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "nồi cơm điện nấu cơm bị sống"}).json()
    assert d["messageVi"].startswith("Dạ hiện FixHome chưa nhận nồi cơm điện")
    assert len(model.calls) == 1


def test_a_catalogue_alias_inside_an_unlisted_name_does_not_count(client_with):
    """07/11: "máy sấy tóc" held the tumble dryer's alias "máy sấy" and was booked as one."""
    client, model = client_with(
        {"devices": [], "own_problem": True, "intent": "repair", "other_appliance": "máy sấy tóc"},
        device=None,
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "máy sấy tóc bị cháy"}).json()
    assert d["messageVi"].startswith("Dạ hiện FixHome chưa nhận máy sấy tóc")
    assert len(model.calls) == 1


@pytest.mark.parametrize("status,said,note", [
    ("COMPLETED", 'Em thấy ngày 03/10/2026 thợ FixHome đã sửa "Sửa điều hòa"', 'Khách từng sửa "Sửa điều hòa" ngày 03/10/2026'),
    ("SCHEDULED", 'Em thấy anh/chị đang có lịch "Sửa điều hòa" ngày 03/10/2026', 'Khách đang có lịch "Sửa điều hòa" ngày 03/10/2026'),
])
def test_an_earlier_booking_of_the_appliance_is_told_by_its_status_once(client_with, status, said, note):
    """BUG 53 (PO 01/11): a job not yet done was told back as if it had been."""
    client, _ = client_with(
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
        {"devices": ["air_conditioner"], "intent": "repair"},
        _turn(need="chảy nước nhiều", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ khả năng nghẹt ống thoát nước ạ."),
    )
    jobs = [{"serviceVi": "Sửa điều hòa", "deviceVi": "Máy lạnh", "date": "2026-10-03", "status": status}]
    first = client.post("/api/v1/diagnosis/analyze", json={"description": "máy lạnh chảy nước", "pastJobs": jobs}).json()
    assert said in first["messageVi"]
    assert any(note in n for n in first["notesVi"])
    again = client.post("/api/v1/diagnosis/analyze", json={"description": "chảy nhiều lắm", "sessionId": first["sessionId"],
                                                            "pastJobs": jobs}).json()
    assert "Em thấy" not in again["messageVi"]


def test_no_reminder_of_an_earlier_booking_beside_a_safety_step(client_with):
    client, _ = client_with(
        {"devices": ["power_outlet"], "intent": "repair"},
        _turn(need="ổ cắm có tia lửa", fault_code="OUTLET_SHORT_CIRCUIT", service_code="EL-01", reply="Dạ ổ cắm bị chập ạ."),
        device="power_outlet",
    )
    jobs = [{"serviceVi": "Sửa ổ cắm", "deviceVi": "Ổ cắm điện", "date": "2026-10-03", "status": "COMPLETED"}]
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "ổ cắm có tia lửa", "pastJobs": jobs}).json()
    assert d["messageVi"].startswith("Trước tiên") and "Em thấy" not in d["messageVi"]


def test_an_unlisted_phrase_holding_an_appliance_the_router_chose_is_still_that_appliance(client_with):
    """07/11: "lap khoa van tay" came back with other_appliance "lap khoa van tay" and was declined."""
    client, model = client_with(
        {"devices": ["smart_lock"], "own_problem": False, "intent": "service", "other_appliance": "lap khoa van tay"},
        _turn(need="lắp khóa vân tay", need_kind="xin_viec", service_code="LK-03", reply="Dạ anh/chị bấm Đặt thợ để lắp khoá nhé."),
        device=None,
    )
    d = client.post("/api/v1/diagnosis/analyze", json={"description": "lap khoa van tay"}).json()
    assert "chưa nhận" not in d["messageVi"]
    assert [s["serviceCode"] for s in d["recommendedServices"]] == ["LK-03"]
