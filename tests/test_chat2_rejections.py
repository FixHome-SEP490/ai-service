"""The customer turning the conclusion down, and the follow-ups mistaken for it (fixhome.sbs, 12/11).

BUG 20: after "máy giặt không vắt được", "không phải bệnh đó, máy kêu lúc cấp
nước" came back as the same belt verdict and a second "sai rồi" repeated the
first answer. BUG 23: the booking description kept the "sai rồi". BUG 19:
"chưa dùng lần nào" dropped the fault for an installation price. A chewed cord
typed without accents was concluded on the compressor, and "vẫn mát" typed
without accents was written back as "không mát".
"""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_provider import get_ai_provider
from app.services.chat2 import answer as answer_tier
from app.services.chat2.brain import (
    DAMAGE,
    REQUEST,
    SYMPTOM,
    UNCLEAR,
    WIRE_STEP,
    adds_to_account,
    contradicts,
    is_question,
    mentions_bare_wire,
    tidy_reply,
)
from app.services.chat2.provider import Chat2Provider, Session
from app.services.chat2.pushback import account, denial
from app.services.pipeline.detector import StubDetector
from app.services.pipeline.knowledge_base import get_knowledge_base


class FakeModel:
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


def _route(device, intent="repair", own=True):
    return {"devices": [device], "own_problem": own, "intent": intent, "other_appliance": ""}


@pytest.fixture(autouse=True)
def model_server(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VLM_BASE_URL", "http://model.test")


@pytest.fixture
def client_with():
    def make(*replies):
        model = FakeModel(*replies)
        provider = Chat2Provider(detector=StubDetector(get_knowledge_base(), device_type=None),
                                 transport=httpx.MockTransport(model))
        app.dependency_overrides[get_ai_provider] = lambda: provider
        return TestClient(app), model

    yield make
    app.dependency_overrides.clear()


def _send(client, text, first=None):
    body = {"description": text}
    if first:
        body["sessionId"] = first["sessionId"]
    return client.post("/api/v1/diagnosis/analyze", json=body).json()


def _enum(call):
    return call["structured_outputs"]["json"]["properties"]["fault_code"]["enum"]


# ----------------------------------------------------------------- the words


@pytest.mark.parametrize("text,rest", [
    ("sai rồi", ""),
    ("sai roi", ""),
    ("nói sai rồi em ơi", ""),
    ("không đúng", ""),
    ("khong dung", ""),
    ("khong dung roi em", ""),
    ("chưa đúng lắm", ""),
    ("hông phải", ""),
    ("không phải bệnh đó, máy kêu lúc cấp nước", "máy kêu lúc cấp nước"),
    ("khong phai benh do, may keu luc cap nuoc", "may keu luc cap nuoc"),
    ("sai rồi, máy chỉ kêu to lúc cấp nước thôi", "máy chỉ kêu to lúc cấp nước thôi"),
    ("ko phai, may keu re re luc lay nuoc vao", "may keu re re luc lay nuoc vao"),
    ("khong dung, may van mat ma chay nuoc tong tong", "may van mat ma chay nuoc tong tong"),
    ("sai rồi, máy vẫn mát nhưng chảy nước", "máy vẫn mát nhưng chảy nước"),
    ("à không phải đâu em, nó kêu to lắm", "nó kêu to lắm"),
    ("em đoán sai rồi, nó chảy nước", "nó chảy nước"),
    ("máy kêu lúc cấp nước chứ không phải bệnh đó", "máy kêu lúc cấp nước"),
    ("kp, tủ vẫn lạnh mà kêu to", "tủ vẫn lạnh mà kêu to"),
    ("không phải vậy đâu, bình vẫn nóng nhưng rò nước", "bình vẫn nóng nhưng rò nước"),
])
def test_a_denial_is_read_with_or_without_accents(text, rest):
    assert denial(text) == rest


@pytest.mark.parametrize("text", [
    # dùng / đúng: the verb, not a denial (BUG 19)
    "không dùng được nữa", "khong dung duoc nua roi em", "chưa dùng lần nào", "chua dung lan nao",
    "không dùng nữa", "khong dung nua",
    # the customer taking back their own words, a plain answer, an appointment
    "à nhầm, máy chưa vệ sinh", "Không", "không, nó chảy nước", "đúng rồi", "sai giờ rồi",
    "mua về cất kho giờ mới lấy ra", "máy giặt không vắt được",
])
def test_words_that_turn_nothing_down(text):
    assert denial(text) is None


def test_the_account_drops_a_bare_denial_at_either_end():
    assert account("máy kêu lúc cấp nước, không phải bệnh đó") == "máy kêu lúc cấp nước"
    assert account("sai rồi") == ""


@pytest.mark.parametrize("text,asks", [
    ("chưa dùng lần nào", False), ("chua dung lan nao", False), ("không dùng được nữa rồi em", False),
    ("mua về cất kho giờ mới lấy ra", False), ("máy mới lắp hôm qua", False),
    ("sửa có lâu không", True), ("tự làm được không em", True), ("có nguy hiểm không", True),
    ("bảo hành bao lâu", True), ("đã dùng lần nào chưa", True), ("vậy là bệnh gì", True), ("thật à", True),
    ("máy lạnh chảy nước là sao vậy?", True),
])
def test_a_question_is_told_from_a_statement_by_its_form(text, asks):
    assert is_question(text) is asks


@pytest.mark.parametrize("text,adds", [
    ("chưa dùng lần nào", True), ("chua dung lan nao", True), ("mua về cất kho giờ mới lấy ra", True),
    ("không dùng được nữa", True), ("sửa có lâu không", False), ("cảm ơn em", False), ("ok", False),
    ("thanh toán tiền mặt được", False), ("bên mình có thợ nữ", False), ("bao nhiêu tiền", False),
])
def test_what_adds_to_the_account_after_a_conclusion(text, adds):
    assert adds_to_account(text) is adds


@pytest.mark.parametrize("reply,customer,wrong", [
    ("Máy không mát và chảy nước thường do nghẹt đường thoát nước.", "khong dung, may van mat ma chay nuoc tong tong", True),
    ("Máy không mát và chảy nước.", "sai rồi, máy vẫn mát nhưng chảy nước", True),
    ("Tủ không lạnh và kêu to.", "tu van lanh ma keu to", True),
    ("Bình không nóng nữa.", "binh van nong nhung ro nuoc", True),
    ("Máy chảy nước thường do nghẹt đường thoát nước.", "may van mat ma chay nuoc", False),
    ("Máy không mát thường do thiếu gas.", "máy lạnh không mát", False),
    # "vẫn không mát" is still not cooling
    ("Máy không mát thường do thiếu gas.", "máy vẫn không mát", False),
])
def test_a_sentence_contradicting_the_customer_is_caught(reply, customer, wrong):
    assert contradicts(reply, customer) is wrong


def test_a_leak_is_written_chay_with_its_accent():
    assert tidy_reply("Máy chạy nước thường do nghẹt ống.") == "Máy chảy nước thường do nghẹt ống."
    assert tidy_reply("Máy chạy nước nóng yếu.") == "Máy chạy nước nóng yếu."


@pytest.mark.parametrize("text,bare", [
    ("day dien tu lanh bi chuot can lo loi dong", True), ("dây điện tủ lạnh bị chuột cắn, thấy cả lõi đồng", True),
    ("dây nguồn quạt bị hở dây", True), ("may giat dut day curoa", False), ("máy giặt đứt dây curoa", False),
])
def test_a_bared_cord_is_told_from_a_broken_belt(text, bare):
    assert mentions_bare_wire(text) is bare


def test_the_answer_tier_admits_not_knowing_once():
    reply = "Em chưa có thông tin về việc nên mua máy hãng nào. Em chưa có thông tin đó."
    assert answer_tier.unsupported(reply) == "Em chưa có thông tin về việc nên mua máy hãng nào."
    assert answer_tier._tidy(reply, about_appliance=False).count("chưa có thông tin") == 1


# ------------------------------------------------------------ the conversation


WASHER = _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01",
               reply="Máy không vắt thường do lệch tải hoặc hỏng dây curoa.")


@pytest.mark.parametrize("said,rest", [
    ("không phải bệnh đó, máy kêu lúc cấp nước", "máy kêu lúc cấp nước"),
    ("sai rồi, máy chỉ kêu to lúc cấp nước thôi", "máy chỉ kêu to lúc cấp nước thôi"),
    ("ko phai, may keu re re luc lay nuoc vao", "may keu re re luc lay nuoc vao"),
])
def test_a_turned_down_fault_is_never_chosen_again_and_the_new_account_counts(client_with, said, rest):
    client, model = client_with(
        _route("washing_machine"), WASHER,
        # The model repeats itself in words; code writes the sentence.
        _turn(need="kêu lúc cấp nước", fault_code="WM_NO_WATER_INLET", service_code="WM-01",
              reply="Máy không vắt có thể do dây curoa hoặc lệch tải."),
    )
    first = _send(client, "máy giặt không vắt được")
    assert first["suspectedFaults"][0]["faultCode"] == "WM_NO_SPIN"
    second = _send(client, said, first)
    # No router call: the turn is a diagnosis of the same washing machine.
    assert len(model.calls) == 3
    assert "WM_NO_SPIN" not in _enum(model.calls[2])
    assert "Khách vừa nói em đoán sai" in model.calls[2]["messages"][0]["content"]
    assert second["suspectedFaults"][0]["faultCode"] == "WM_NO_WATER_INLET"
    assert second["messageVi"].startswith("Dạ vậy máy giặt") and "curoa" not in second["messageVi"]
    disagreed = second["customerDisagreed"]
    assert disagreed["kind"] == "fault" and disagreed["rejected"] == ["WM_NO_SPIN"]
    assert disagreed["restVi"] == rest and disagreed["correctionVi"] == said
    assert disagreed["saidVi"] == "máy giặt không vắt được"
    assert second["diagnosticState"]["rejected"] == ["WM_NO_SPIN"]


def test_sai_roi_twice_gives_a_third_fault_not_the_first_again(client_with):
    client, model = client_with(
        _route("washing_machine"), WASHER,
        # A bare "sai rồi": the model asks instead; code concludes on the next fault.
        _turn(need="", need_kind=UNCLEAR, decision="ask", reply="Dạ máy đang bị sao ạ?"),
        {"fault_code": "WM_DRAIN_PUMP"},
        _turn(need="không vắt", fault_code="WM_MOTOR_FAULT", service_code="WM-01", reply="Dạ lệch tải ạ."),
    )
    first = _send(client, "máy giặt không vắt được")
    second = _send(client, "sai rồi", first)
    assert second["status"] == "ok" and second["suspectedFaults"][0]["faultCode"] == "WM_DRAIN_PUMP"
    assert second["customerDisagreed"]["restVi"] == ""
    third = _send(client, "sai rồi", second)
    enum = _enum(model.calls[-1])
    assert "WM_NO_SPIN" not in enum and "WM_DRAIN_PUMP" not in enum
    assert third["suspectedFaults"][0]["faultCode"] == "WM_MOTOR_FAULT"
    assert third["messageVi"] != second["messageVi"] and "lệch tải" not in third["messageVi"]
    assert third["customerDisagreed"]["rejected"] == ["WM_DRAIN_PUMP"]


@pytest.mark.parametrize("device,first_said,first_turn,said,new_turn,not_said", [
    ("air_conditioner", "may lanh khong mat",
     _turn(need="không mát", fault_code="AC_LOW_REFRIGERANT", service_code="AC-01", reply="Máy không mát thường do thiếu gas."),
     "khong dung, may van mat ma chay nuoc tong tong",
     _turn(need="vẫn mát, chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02",
           reply="Máy không mát và chảy nước thường do nghẹt đường thoát nước."), "không mát"),
    ("air_conditioner", "máy lạnh chạy mà không mát",
     _turn(need="không mát", fault_code="AC_LOW_REFRIGERANT", service_code="AC-01", reply="Máy có thể thiếu gas."),
     "sai rồi, máy vẫn mát nhưng chảy nước",
     _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Máy chạy nước do nghẹt ống."), "thiếu gas"),
    ("refrigerator", "tu lanh khong lanh",
     _turn(need="không lạnh", fault_code="FRIDGE_LOW_GAS", service_code="FR-01", reply="Tủ không lạnh thường do thiếu gas."),
     "sai roi, tu van lanh ma keu to",
     _turn(need="kêu to", fault_code="FRIDGE_NOISY", service_code="FR-01", reply="Tủ không lạnh và kêu to."), "không lạnh"),
    ("water_heater", "bình nóng lạnh không nóng",
     _turn(need="không nóng", fault_code="WH_HEATING_ELEMENT", service_code="WH-02", reply="Bình không nóng do hỏng thanh đốt."),
     "không phải vậy đâu, bình vẫn nóng nhưng rò nước",
     _turn(need="rò nước", fault_code="WH_TANK_LEAK", service_code="WH-03", reply="Bình không nóng và rò nước."), "không nóng"),
])
def test_a_correction_on_every_appliance_is_answered_in_code_words(client_with, device, first_said, first_turn, said,
                                                                    new_turn, not_said):
    client, model = client_with(_route(device), first_turn, new_turn)
    first = _send(client, first_said)
    second = _send(client, said, first)
    rejected = first["suspectedFaults"][0]["faultCode"]
    assert rejected not in _enum(model.calls[2])
    assert second["suspectedFaults"][0]["faultCode"] == new_turn["fault_code"]
    assert not_said not in second["messageVi"].lower() and "chạy nước" not in second["messageVi"]
    assert second["customerDisagreed"]["rejected"] == [rejected]


@pytest.mark.parametrize("said", ["không dùng được nữa", "khong dung duoc nua roi em"])
def test_cannot_use_it_any_more_is_not_a_denial(client_with, said):
    client, model = client_with(
        {"devices": ["refrigerator"], "own_problem": True, "intent": "repair", "other_appliance": ""},
        _turn(need="không lạnh", fault_code="FRIDGE_LOW_GAS", service_code="FR-01", reply="Tủ không lạnh thường do thiếu gas."),
        _route("refrigerator"),
        _turn(need="không lạnh, không dùng được", fault_code="FRIDGE_LOW_GAS", service_code="FR-01", reply="Dạ tủ thiếu gas ạ."),
    )
    first = _send(client, "tu lanh khong lanh")
    second = _send(client, said, first)
    assert len(model.calls) == 4  # routed as usual
    assert second["customerDisagreed"] is None
    assert "FRIDGE_LOW_GAS" in _enum(model.calls[3])
    assert second["suspectedFaults"][0]["faultCode"] == "FRIDGE_LOW_GAS"


def test_no_to_the_assistants_own_question_is_an_answer_not_a_denial(client_with):
    client, model = client_with(
        _route("air_conditioner"),
        _turn(need="", need_kind=UNCLEAR, decision="ask", reply="Dạ máy lạnh đang bị sao ạ?"),
        _route("air_conditioner"),
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ nghẹt ống thoát nước ạ."),
    )
    first = _send(client, "máy lạnh có vấn đề")
    second = _send(client, "không phải, nó chảy nước", first)
    assert second["customerDisagreed"] is None and len(model.calls) == 4


@pytest.mark.parametrize("device,first_said,first_turn,said,model_turn,kept", [
    ("air_conditioner", "máy lạnh mới lắp mà không mát",
     _turn(need="mới lắp không mát", fault_code="AC_LOW_REFRIGERANT", service_code="AC-01", reply="Máy có thể thiếu gas."),
     "chưa dùng lần nào",
     _turn(need="lắp máy", need_kind=REQUEST, fault_code="NONE", service_code="AC-03", reply="Giá lắp đặt điều hòa là 449.000đ."),
     "AC_LOW_REFRIGERANT"),
    ("washing_machine", "máy giặt không vắt",
     _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01", reply="Máy không vắt thường do lệch tải."),
     "chua dung lan nao",
     _turn(need="", need_kind=UNCLEAR, decision="ask", fault_code="NONE", service_code="WM-01",
           reply="Máy giặt chưa dùng lần nào thì chưa có thông tin lỗi cụ thể."), "WM_NO_SPIN"),
    ("refrigerator", "tủ lạnh mới mua về không lạnh",
     _turn(need="không lạnh", fault_code="FRIDGE_LOW_GAS", service_code="FR-01", reply="Tủ có thể thiếu gas."),
     "mua về cất kho giờ mới lấy ra",
     _turn(need="", need_kind=UNCLEAR, decision="ask", fault_code="NONE", service_code="FR-01", reply="Dạ tủ bị sao ạ?"),
     "FRIDGE_LOW_GAS"),
])
def test_a_follow_up_statement_keeps_the_fault(client_with, device, first_said, first_turn, said, model_turn, kept):
    """BUG 19: routed as a question, "chưa dùng lần nào" went to the documents and came back with a price."""
    client, model = client_with(
        _route(device), first_turn,
        {"devices": [device], "own_problem": False, "intent": "question", "other_appliance": ""},
        model_turn,
    )
    first = _send(client, first_said)
    second = _send(client, said, first)
    assert len(model.calls) == 4  # router, diagnosis; never the answer tier
    assert second["status"] == "ok" and second["suspectedFaults"][0]["faultCode"] == kept
    assert "449.000" not in second["messageVi"] and "chưa có thông tin" not in second["messageVi"]
    assert second["customerDisagreed"] is None


def test_a_real_question_after_a_conclusion_still_goes_to_the_documents(client_with):
    client, model = client_with(
        _route("air_conditioner"),
        _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02", reply="Dạ nghẹt ống thoát nước ạ."),
        {"devices": ["air_conditioner"], "own_problem": True, "intent": "question", "other_appliance": ""},
        {"passages": []},
    )
    first = _send(client, "máy lạnh chảy nước")
    second = _send(client, "sửa có lâu không", first)
    assert len(model.calls) == 4 and "chưa có thông tin" in second["messageVi"]


@pytest.mark.parametrize("device,said,model_turn", [
    ("refrigerator", "day dien tu lanh bi chuot can lo loi dong",
     _turn(need="chuột cắn dây", fault_code="FRIDGE_COMPRESSOR", service_code="FR-01",
           reply="Chuột cắn có thể gây hư hại dây điện hoặc các bộ phận khác.")),
    ("air_conditioner", "dây điện máy lạnh bị chuột gặm hở lõi",
     _turn(need="dây bị chuột gặm", fault_code="AC_SMELL_BURNT", service_code="AC-01", reply="Máy bị chập điện.")),
    ("washing_machine", "day nguon may giat bi chuot can ho loi",
     _turn(need="dây nguồn hở", need_kind=DAMAGE, fault_code="WM_PCB_FAULT", service_code="WM-01", reply="Lỗi bo mạch.")),
])
def test_a_chewed_cord_is_damage_with_the_unplug_step_not_a_fault(client_with, device, said, model_turn):
    client, _ = client_with(_route(device), model_turn)
    d = _send(client, said)
    assert d["messageVi"].startswith(WIRE_STEP)
    assert d["suspectedFaults"] == []
    assert "cần thợ tới kiểm tra hư hại" in d["messageVi"]
    assert d["recommendedServices"]


def test_a_cord_fault_stays_the_fault():
    from app.services.chat2.brain import _decide
    from app.services.chat2.menu import menu_for

    menu = menu_for("electric_fan")
    raw = _turn(need="dây nguồn hở", fault_code="FAN_CORD_DAMAGE", service_code=menu.services[0].code)
    _, fault, _ = _decide(menu, raw, 0, latest="day nguon quat bi chuot can ho loi")
    assert fault is not None and fault.code == "FAN_CORD_DAMAGE"


def test_a_broken_belt_gets_no_cord_step(client_with):
    client, _ = client_with(
        _route("washing_machine"),
        _turn(need="đứt dây curoa", fault_code="WM_NO_SPIN", service_code="WM-01", reply="Dạ máy hỏng dây curoa ạ."),
    )
    d = _send(client, "máy giặt đứt dây curoa")
    assert WIRE_STEP not in d["messageVi"] and d["suspectedFaults"][0]["faultCode"] == "WM_NO_SPIN"


def test_a_cleaning_request_gets_no_old_fault_reminder(client_with):
    client, _ = client_with(
        _route("refrigerator"),
        _turn(need="vệ sinh tủ, mùi hôi", need_kind=REQUEST, fault_code="FRIDGE_DIRTY_ODOR", service_code="FR-02",
              reply="Dạ tủ lạnh bẩn có mùi hôi ạ."),
    )
    jobs = [{"serviceVi": "Sửa tủ lạnh", "deviceVi": "Tủ lạnh", "date": "2026-11-02", "status": "COMPLETED"}]
    d = client.post("/api/v1/diagnosis/analyze", json={
        "description": "tôi còn 1 tủ lạnh xuất hiện mùi hôi khó chịu cần thêm dịch vụ vệ sinh tủ lạnh", "pastJobs": jobs}).json()
    assert "lỗi cũ quay lại" not in d["messageVi"] and "Em thấy" not in d["messageVi"]


def test_rejected_faults_survive_a_restart():
    from app.services.chat2.provider import Sessions

    s = Session("x", rejected=["WM_NO_SPIN"])
    state = s.export()
    restored = Sessions().get(None, state, [])
    assert restored.rejected == ["WM_NO_SPIN"]
