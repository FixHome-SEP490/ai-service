"""What to get ready before the technician comes, fitted to the appliance (PO 26/10/2026)."""

import asyncio

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import visit_prep
from app.services.pipeline.knowledge_base import get_knowledge_base
from tests.test_several_appliances import _photo, _pipeline

KB = get_knowledge_base()

WATER = {"washing_machine", "dishwasher", "water_heater", "water_purifier", "faucet", "sink", "toilet", "water_pipe"}
WATER_WORDS = ("van nước", "van cấp nước", "van chặn", "van tổng", "khoá nước")


def test_every_appliance_has_its_own_steps():
    data = visit_prep._data()
    assert set(data["devices"]) == set(KB.device_types)
    for device, steps in data["devices"].items():
        assert 3 <= len(steps) <= 6, device


def test_no_appliance_is_told_what_belongs_to_another():
    for device in KB.device_types:
        text = " ".join(visit_prep.steps_for(device)).lower()
        if device not in WATER:
            # "Sửa bếp gas mà lại kêu khoá ống nước" is what the PO ruled out.
            assert not any(w in text for w in WATER_WORDS), device
        if device != "gas_stove":
            assert "gas" not in text, device


def test_the_question_is_recognised_and_nothing_else():
    for asked in (
        "trước khi thợ tới em cần làm gì",
        "em cần chuẩn bị gì không",
        "thợ tới thì nhà mình cần làm gì",
        "truoc khi tho den can luu y gi",
        "có cần dọn dẹp gì không em",
    ):
        assert visit_prep.asks_how_to_prepare(asked), asked
    for other in (
        "trước khi thợ tới có dùng tạm được không",
        "máy lạnh không mát",
        "sửa hết bao nhiêu tiền",
        "thợ tới lúc mấy giờ",
    ):
        assert not visit_prep.asks_how_to_prepare(other), other


def test_a_named_appliance_gets_its_own_steps():
    reply = asyncio.run(_pipeline().answer(ChatRequest(question="sửa bếp gas thì trước khi thợ tới em cần chuẩn bị gì")))
    assert "bếp gas" in reply.answer_vi and "van bình gas" in reply.answer_vi
    assert not any(w in reply.answer_vi for w in WATER_WORDS)


def test_every_appliance_of_the_visit_gets_its_paragraph_and_the_booking_bar_stays():
    pipeline = _pipeline()
    first = asyncio.run(
        pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
        )
    )
    reply = asyncio.run(pipeline.diagnose(DiagnosisRequest(description="trước khi thợ tới em cần làm gì", session_id=first.session_id)))
    assert "Với máy lạnh:\n•" in reply.message_vi and "Với máy giặt:\n•" in reply.message_vi
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "washing_machine"]
    assert [s.service_code[:2] for s in reply.recommended_services] == ["AC", "WM"]


def test_with_no_appliance_known_the_general_steps_and_a_question():
    reply = asyncio.run(_pipeline().answer(ChatRequest(question="trước khi thợ tới em cần làm gì")))
    assert "thiết bị nào đang hỏng" in reply.answer_vi
    assert "thợ sẽ gọi trước khi sang" in reply.answer_vi
