"""Chat brain v2 against a fake model server: the rules code keeps around the model's choice."""

import json

import httpx
import pytest

from app.services.chat2.brain import (
    DAMAGE,
    MAX_QUESTIONS,
    REQUEST,
    SYMPTOM,
    UNCLEAR,
    ChatBrain,
    Turn,
    _parse,
    _turn_schema,
    code_reading,
    questions_asked,
)
from app.services.chat2.menu import devices, menu_for


def _server(replies):
    """A fake OpenAI-compatible endpoint answering each call with the next reply."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        content = replies[len(calls) - 1]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]})

    return httpx.MockTransport(handler), calls


def _route(*names, intent="repair"):
    return {"devices": list(names), "intent": intent}


def _turn(**kw):
    base = {
        "need": "", "need_kind": SYMPTOM, "fault_code": "NONE", "decision": "conclude",
        "service_code": "AC-01", "reply": "", "options": [], "confidence": 0.8,
    }
    return {**base, **kw}


async def _run(replies, history, device="air_conditioner"):
    transport, calls = _server(replies)
    async with httpx.AsyncClient(transport=transport) as client:
        verdict = await ChatBrain("http://fake/v1", "m").turn(client, history, device)
    return verdict, calls


def test_schema_enumerates_only_the_appliances_own_codes():
    menu = menu_for("air_conditioner")
    schema = _turn_schema(menu)
    faults = schema["properties"]["fault_code"]["enum"]
    assert set(faults) == {f.code for f in menu.faults} | {"NONE"}
    assert "FRIDGE_COMPRESSOR" not in faults
    assert set(schema["properties"]["service_code"]["enum"]) == {"AC-01", "AC-02", "AC-03", "AC-04"}
    assert schema["required"][:2] == ["need", "need_kind"]


def test_json_cut_before_its_closing_brace_is_read():
    assert _parse('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}
    assert _parse('{\n  "a": 1,\n  "b": "x"\n') == {"a": 1, "b": "x"}
    # Cut between a key and its value: the fields that arrived are kept.
    assert _parse('{\n  "quote": "Gò Vấp", \n  "reply": "Dạ có ạ.",\n  "grounded": ') == {"quote": "Gò Vấp", "reply": "Dạ có ạ."}


def test_every_appliance_has_a_menu_and_every_fault_a_service():
    for device in devices():
        menu = menu_for(device)
        assert menu.faults or device == "range_hood", device
        if menu.repair_service:
            assert all(f.service_code for f in menu.faults), device


def test_range_hood_services_are_reachable():
    assert {s.code for s in menu_for("range_hood").services} == {"KT-02", "KT-03"}


@pytest.mark.asyncio
async def test_conclusion_carries_price_from_catalogue_not_model():
    v, calls = await _run(
        [_route("air_conditioner"),
         _turn(need="mùi hôi, bẩn", fault_code="AC_DIRTY_FILTER", service_code="AC-02", reply="Dạ máy lạnh bẩn dàn lạnh nên có mùi hôi ạ.")],
        [Turn("user", "máy lạnh có mùi hôi, nhìn rất bẩn")],
    )
    assert v.decision == "conclude" and v.fault_code == "AC_DIRTY_FILTER" and v.service_code == "AC-02"
    assert "Vệ sinh điều hòa" in v.booking_vi and "199.000đ" in v.booking_vi
    assert "199.000" not in v.reply_vi
    assert calls[1]["structured_outputs"]["json"]["required"][0] == "need"
    assert calls[1]["stop"] == ["\n\n\n"]
    assert calls[1]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_a_described_symptom_concludes_even_when_the_model_wanted_to_ask():
    v, _ = await _run(
        [_route("air_conditioner"),
         _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", decision="ask", reply="Dạ nước chảy ở đâu ạ?")],
        [Turn("user", "máy lạnh chảy nước")],
    )
    assert v.decision == "conclude" and v.fault_code == "AC_DRAIN_BLOCKED"
    assert "?" not in v.reply_vi
    assert "nghẹt đường thoát nước ngưng" in v.reply_vi


@pytest.mark.asyncio
async def test_nothing_described_asks_one_question_with_options():
    v, _ = await _run(
        [_route("air_conditioner"),
         _turn(need_kind=UNCLEAR, decision="ask", reply="Dạ cục nóng ngoài trời có chạy không ạ", options=["Có chạy", "Không chạy", "Chưa rõ"])],
        [Turn("user", "máy lạnh bị hư")],
    )
    assert v.decision == "ask" and v.reply_vi.endswith("?") and v.question_vi == v.reply_vi
    assert v.options_vi == ["Có chạy", "Không chạy", "Chưa rõ"]


@pytest.mark.asyncio
async def test_a_need_that_says_nothing_specific_gets_a_question():
    v, _ = await _run(
        [_route("air_conditioner"),
         _turn(need="máy lạnh có vấn đề", fault_code="AC_PCB_FAULT", reply="Dạ cục nóng có chạy không ạ?", options=["Có", "Không"])],
        [Turn("user", "máy lạnh nhà em có vấn đề, xem giúp")],
    )
    assert v.decision == "ask" and v.options_vi == ["Có", "Không"]


def test_describes_nothing_keeps_real_symptoms():
    from app.services.chat2.brain import describes_nothing

    menu = menu_for("air_conditioner")
    assert describes_nothing("máy lạnh bị hư rồi", menu)
    assert describes_nothing("điều hòa có vấn đề", menu)
    assert not describes_nothing("chảy nước", menu)
    assert not describes_nothing("máy lạnh không mát", menu)
    fridge = menu_for("refrigerator")
    assert not describes_nothing("ngăn mát không lạnh, ngăn đá vẫn lạnh", fridge)
    assert describes_nothing("tủ lạnh có vấn đề", fridge)
    assert not describes_nothing("khóa vân tay không nhận vân", menu_for("smart_lock"))


@pytest.mark.asyncio
async def test_question_limit_forces_a_conclusion():
    history = [
        Turn("user", "máy lạnh bị sao á"),
        Turn("assistant", "Dạ cục nóng ngoài trời có chạy không ạ?"),
        Turn("user", "không rõ"),
        Turn("assistant", "Dạ máy có được vệ sinh gần đây không ạ?"),
        Turn("user", "chưa rõ"),
    ]
    assert questions_asked(history) == MAX_QUESTIONS
    v, _ = await _run([_route("air_conditioner"), _turn(need_kind=UNCLEAR, decision="ask", reply="Dạ quạt có thổi gió không ạ?")], history)
    assert v.decision == "conclude" and v.service_code == "AC-01"
    assert "tận nơi" in v.reply_vi


@pytest.mark.asyncio
async def test_damage_books_the_repair_service_whatever_the_model_picked():
    v, _ = await _run(
        [_route("air_conditioner"),
         _turn(need="rơi khỏi tường", need_kind=DAMAGE, service_code="AC-04", reply="Dạ em đặt tháo máy cho anh/chị.")],
        [Turn("user", "cục lạnh bung khỏi tường rớt xuống sàn")],
    )
    assert v.decision == "conclude" and v.fault_code is None and v.service_code == "AC-01"


@pytest.mark.asyncio
async def test_a_request_books_the_service_asked_for():
    v, _ = await _run(
        [_route("air_conditioner", intent="service"),
         _turn(need="tháo máy chuyển nhà", need_kind=REQUEST, service_code="AC-04", decision="ask", reply="Dạ máy treo tường hay âm trần ạ?")],
        [Turn("user", "tháo máy lạnh chuyển nhà")],
    )
    assert v.decision == "conclude" and v.service_code == "AC-04"


@pytest.mark.asyncio
async def test_a_repair_fault_overrides_a_mismatched_service():
    v, _ = await _run(
        [_route("air_conditioner"), _turn(need="không mát", fault_code="AC_LOW_REFRIGERANT", service_code="AC-03")],
        [Turn("user", "máy lạnh không mát")],
    )
    assert v.service_code == "AC-01"


@pytest.mark.asyncio
async def test_urgent_fault_starts_with_the_safety_step():
    v, _ = await _run(
        [_route("air_conditioner"), _turn(need="mùi khét", fault_code="AC_SMELL_BURNT", reply="Dạ máy lạnh có dấu hiệu chập điện ạ.")],
        [Turn("user", "máy lạnh có mùi khét")],
    )
    assert v.reply_vi.startswith("Trước tiên anh/chị")


@pytest.mark.asyncio
async def test_the_words_win_over_the_photograph():
    v, calls = await _run(
        [_route("oven"), _turn(need="không nóng", fault_code="OVEN_HEATING_ELEMENT", service_code="KT-08")],
        [Turn("user", "lò nướng bật đèn sáng mà không nóng")],
        device="microwave_oven",
    )
    assert v.device_type == "oven" and v.service_code == "KT-08"
    assert "OVEN_HEATING_ELEMENT" in json.dumps(calls[1]["structured_outputs"]["json"])


@pytest.mark.asyncio
async def test_a_guessed_appliance_does_not_outvote_the_photograph():
    v, _ = await _run(
        [_route("power_outlet"), _turn(need="tụ yếu", fault_code="AC_CAPACITOR")],
        [Turn("user", "đo cái tụ dầu chỉ còn 15 micro")],
        device="air_conditioner",
    )
    assert v.device_type == "air_conditioner" and v.fault_code == "AC_CAPACITOR"


@pytest.mark.asyncio
async def test_with_a_photograph_the_router_cannot_decline():
    v, calls = await _run(
        [_route(intent="offtopic"), _turn(need="cả dãy trọ cúp điện khi bật", fault_code="AC_PCB_FAULT")],
        [Turn("user", "hôm qua vừa bật lên là cả dãy phòng trọ cúp điện")],
    )
    assert v.decision == "conclude" and v.device_type == "air_conditioner" and len(calls) == 2


def test_the_more_specific_name_wins_and_time_questions_are_not_bookings():
    from app.services.chat2.brain import WHEN_WORDS, describes_nothing, mentions, named_in

    assert named_in("cái quạt trần rớt xuống giường") == ["ceiling_fan"]
    assert named_in("máy giặt không vắt, tiện vệ sinh luôn máy lạnh") == ["washing_machine", "air_conditioner"]
    assert mentions("đặt rồi bao lâu thợ tới", WHEN_WORDS)
    assert describes_nothing("máy này mấy hôm nay hơi lạ", menu_for("air_conditioner"))


def test_names_appliance_reads_names_and_aliases_without_accents():
    from app.services.chat2.brain import names_appliance

    assert names_appliance("lo nuong nha em khong nong", "oven")
    assert names_appliance("cái điều hoà kêu to", "air_conditioner")
    assert not names_appliance("đo cái tụ dầu chỉ còn 15 micro", "power_outlet")
    assert not names_appliance("rung y như cái máy giặt vắt lệch đồ", "washing_machine")
    assert not names_appliance("nóng như cái lò nướng bánh mì", "oven")


@pytest.mark.asyncio
async def test_a_named_appliance_that_is_no_look_alike_is_added_not_swapped():
    v, _ = await _run(
        [_route("air_conditioner", "washing_machine"),
         _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED"),
         _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01")],
        [Turn("user", "máy lạnh chảy nước, máy giặt cũng không vắt")],
    )
    assert v.device_type == "air_conditioner" and [o.device_type for o in v.others] == ["washing_machine"]


@pytest.mark.asyncio
async def test_the_newest_message_can_change_the_subject():
    transport, calls = _server([
        _route("air_conditioner", "refrigerator"),
        _turn(need="tủ lạnh kêu to", fault_code="FRIDGE_NOISY", service_code="FR-01"),
    ])
    history = [
        Turn("user", "máy lạnh chảy nước"),
        Turn("assistant", "Dạ khả năng nghẹt ống thoát nước ạ."),
        Turn("user", "à mà cái tủ lạnh nhà em đêm nào cũng kêu to"),
    ]
    async with httpx.AsyncClient(transport=transport) as client:
        v = await ChatBrain("http://fake/v1", "m").turn(client, history, None, current="air_conditioner")
    assert v.device_type == "refrigerator" and v.others == []
    assert "chỉ xét tủ lạnh" in calls[1]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_a_reply_naming_nothing_stays_on_the_appliance():
    transport, _ = _server([_route(), _turn(need="chảy nước", fault_code="AC_DRAIN_BLOCKED", service_code="AC-02")])
    history = [Turn("user", "máy lạnh bị sao á"), Turn("assistant", "Dạ máy đang bị gì ạ?"), Turn("user", "chảy nước")]
    async with httpx.AsyncClient(transport=transport) as client:
        v = await ChatBrain("http://fake/v1", "m").turn(client, history, None, current="air_conditioner")
    assert v.device_type == "air_conditioner"


@pytest.mark.asyncio
async def test_two_appliances_are_each_concluded():
    v, calls = await _run(
        [_route("washing_machine", "air_conditioner"),
         _turn(need="không vắt", fault_code="WM_NO_SPIN", service_code="WM-01"),
         _turn(need="vệ sinh", need_kind=REQUEST, service_code="AC-02")],
        [Turn("user", "máy giặt không vắt, tiện vệ sinh luôn máy lạnh")],
        device=None,
    )
    assert v.device_type == "washing_machine" and v.service_code == "WM-01"
    assert [(o.device_type, o.service_code) for o in v.others] == [("air_conditioner", "AC-02")]
    assert "chỉ xét" in calls[1]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_offtopic_is_declined_without_a_diagnosis():
    v, calls = await _run([_route(intent="offtopic")], [Turn("user", "laptop vô nước")], device=None)
    assert v.decision == "not_repair" and len(calls) == 1


def test_a_reported_error_code_is_read_from_the_brands_table():
    context, sentence = code_reading([Turn("user", "máy giặt Samsung báo lỗi 4C")], "washing_machine")
    assert context and "4C" in context
    assert sentence and "Samsung" in sentence
    context, sentence = code_reading([Turn("user", "máy giặt báo lỗi 4C")], "washing_machine")
    assert context and "chưa rõ hãng" in context and sentence is None
    assert code_reading([Turn("user", "máy giặt không vắt")], "washing_machine") == (None, None)


def test_fault_cards_are_rebuilt_from_the_documents():
    """A document edited without rerunning tools/build_fault_cards.py would leave the model reading the old card."""
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("build_fault_cards", root / "tools" / "build_fault_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = json.dumps(module.build(), ensure_ascii=False, indent=1) + "\n"
    assert (root / "app" / "data" / "fault_cards.json").read_text(encoding="utf-8") == built, (
        "fault_cards.json is stale: run python tools/build_fault_cards.py"
    )


def test_knowledge_index_is_rebuilt_from_the_documents():
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("build_knowledge_index", root / "tools" / "build_knowledge_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = json.dumps(module.build(), ensure_ascii=False, indent=1) + "\n"
    assert (root / "app" / "data" / "knowledge_index.json").read_text(encoding="utf-8") == built, (
        "knowledge_index.json is stale: run python tools/build_knowledge_index.py"
    )


def test_every_platform_question_has_somewhere_to_be_answered_from():
    from app.services.chat2.answer import candidates

    platform = {p.section_vi for p in candidates(None, None)}
    for needed in ("Khách hỏi FixHome là gì, FixHome làm gì", "Em là ai trong cuộc trò chuyện này",
                   "Hai cách thanh toán", "Hai thành phố, hai mươi chín quận", "FixHome đang nhận những dịch vụ gì",
                   "Thợ của FixHome có được kiểm tra không"):
        assert needed in platform, needed
    assert not [p for p in candidates("air_conditioner", None) if "ảnh" in p.section_vi.lower() and "đọc" in p.section_vi.lower()]


def test_a_quoted_answer_never_says_there_is_no_information():
    from app.services.chat2.answer import _tidy

    quote = "Thành phố Hồ Chí Minh có mười bảy: Quận 1, Gò Vấp, Bình Thạnh."
    assert _tidy("Em chưa có thông tin cụ thể về thợ tại Gò Vấp.", False, True, quote).startswith("Dạ, Thành phố Hồ Chí Minh")
    assert _tidy("Chào anh/chị, em có nhận đơn tại Gò Vấp. Em chưa có thông tin chi tiết hơn.", False, True, quote) == "Em có nhận đơn tại Gò Vấp."
    assert _tidy("Em chưa có thông tin đó.", False, False, "") == "Em chưa có thông tin đó."
    assert _tidy("Anh/chị hãy bấm 'Đặt thợ' để hệ thống gợi ý dịch vụ.", False, True, "Hà Nội có Long Biên.").startswith("Dạ, Hà Nội")


@pytest.mark.asyncio
async def test_the_models_unclear_stands_for_a_vague_message_even_when_words_are_unusual():
    # 06/11: overruling the model on words alone turned 86% of vague messages into guesses.
    v, _ = await _run(
        [_route("air_conditioner"),
         _turn(need="dùng thấy không được ổn như trước", need_kind=UNCLEAR, decision="ask", reply="Dạ máy đang bị sao ạ?")],
        [Turn("user", "dùng thấy không được ổn như trước")],
    )
    assert v.decision == "ask"


@pytest.mark.asyncio
async def test_unclear_with_a_named_fault_and_a_specific_message_concludes():
    v, _ = await _run(
        [_route("refrigerator"),
         _turn(need="ngăn mát không lạnh, ngăn đá vẫn lạnh", need_kind=UNCLEAR, fault_code="FRIDGE_FAN_FAULT",
               service_code="FR-01", decision="ask", reply="Ngăn đá có đóng tuyết không ạ?")],
        [Turn("user", "tủ lạnh ngăn mát không lạnh mà ngăn đá vẫn lạnh")],
        device="refrigerator",
    )
    assert v.decision == "conclude" and v.fault_code == "FRIDGE_FAN_FAULT"
