"""Up to three appliances in one conversation, booked as one visit.

The customer photographs the air conditioner, the washing machine and the
fridge, or names them in one message. Only the first photograph used to be
looked at, and the reply offered one service. Backend books a visit of up to
three devices, so the reply now carries one entry and one service per
appliance, the one being talked through first.
"""

import asyncio
import base64
import io
import re

from PIL import Image

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.detector import Detection
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()

# One colour per appliance, so the fake detector can tell the photographs apart.
COLOURS = {
    (200, 0, 0): "air_conditioner",
    (0, 200, 0): "washing_machine",
    (0, 0, 200): "refrigerator",
    (200, 200, 0): "microwave_oven",
}


def _photo(device: str) -> str:
    colour = next(c for c, d in COLOURS.items() if d == device)
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _blank() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), (90, 90, 90)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class _ColourDetector:
    async def detect(self, image):
        pixel = image.image.convert("RGB").getpixel((1, 1))
        device = COLOURS.get(tuple(pixel))
        if device is None:
            return []
        return [Detection(device_type=device, confidence=0.9, box_xywh=(0, 0, 64, 48), crop=image)]


def _pipeline() -> LocalPipeline:
    sc.install(sc.LiveCatalog())
    return LocalPipeline(detector=_ColourDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)


def _run(pipeline, **kwargs):
    return asyncio.run(pipeline.diagnose(DiagnosisRequest(**kwargs)))


def test_three_photographs_give_three_appliances_and_three_services():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("washing_machine"), _photo("refrigerator")],
    )
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "washing_machine", "refrigerator"]
    assert [d.image_index for d in reply.devices] == [0, 1, 2]
    assert reply.devices[0].is_primary and not any(d.is_primary for d in reply.devices[1:])
    codes = [s.service_code for s in reply.recommended_services]
    assert codes[1:] == ["WM-01", "FR-01"]
    assert codes[0].startswith("AC-")
    assert [s.device_type for s in reply.recommended_services] == [
        "air_conditioner", "washing_machine", "refrigerator"
    ]
    assert "đặt chung" in reply.message_vi
    # Every appliance is answered in this reply (PO 25/10/2026): the two only
    # photographed are asked what is wrong with them, nobody waits for "xem tiếp".
    assert "xem tiếp" not in reply.message_vi
    assert "Về máy giặt" in reply.message_vi and "Về tủ lạnh" in reply.message_vi
    assert all(d.message_vi for d in reply.devices[1:])


def test_the_appliance_the_message_is_about_leads_whatever_the_photo_order():
    reply = _run(
        _pipeline(),
        description="máy giặt không vắt được",
        images=[_photo("air_conditioner"), _photo("washing_machine")],
    )
    assert reply.devices[0].device_type == "washing_machine"
    assert reply.devices[0].image_index == 1
    assert reply.devices[1].device_type == "air_conditioner"


def test_the_same_appliance_photographed_twice_is_one_appliance():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("air_conditioner")],
    )
    assert reply.devices == []
    assert len({s.service_code for s in reply.recommended_services}) <= 3


def test_a_photograph_of_nothing_known_is_skipped():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _blank(), _photo("refrigerator")],
    )
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "refrigerator"]
    assert reply.devices[1].image_index == 2


def test_an_unreadable_extra_photograph_does_not_cost_the_answer():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), "không phải ảnh"],
    )
    assert reply.device is not None and reply.device.device_type == "air_conditioner"


def test_appliances_named_in_one_message_each_get_a_service():
    reply = _run(_pipeline(), description="máy lạnh không mát, máy giặt thì không vắt được")
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "washing_machine"]
    washer = reply.devices[1]
    assert washer.service is not None and washer.service.service_code == "WM-01"
    assert washer.description_vi and "vắt" in washer.description_vi
    assert washer.suspected_faults, "what was said about it points at a fault"


def test_xem_tiep_brings_up_the_next_appliance_and_keeps_the_visit():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát, máy giặt thì không vắt được")
    after = _run(pipeline, description="xem tiếp", session_id=first.session_id)
    assert after.session_id == first.session_id
    assert [d.device_type for d in after.devices] == ["washing_machine", "air_conditioner"]
    assert after.devices[0].is_primary
    assert after.devices[1].service is not None
    # Shown again, not diagnosed from the words "xem tiếp".
    assert after.suspected_faults == first.devices[1].suspected_faults


def test_every_appliance_of_one_message_is_diagnosed_at_once():
    reply = _run(_pipeline(), description="máy lạnh chảy nước, máy giặt không vắt được, tủ lạnh không đông đá")
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "washing_machine", "refrigerator"]
    for entry in reply.devices:
        assert entry.suspected_faults, entry.device_type
        assert entry.service is not None and entry.message_vi
    assert reply.message_vi.count("Về ") == 2


def test_a_follow_up_naming_another_appliance_is_answered_in_its_own_conversation():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh nhà em không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    washer = _run(pipeline, description="còn máy giặt thì vắt kêu to lắm", session_id=first.session_id)
    assert washer.session_id == first.session_id
    assert washer.devices[0].device_type == "washing_machine" and washer.devices[0].is_primary
    assert [f.fault_code for f in washer.suspected_faults][:1] == ["WM_BEARING_NOISE"]
    chat = pipeline._conversations.get_or_create(first.session_id)
    assert chat.device_type == "air_conditioner"
    # The air conditioner's own thread goes on where it was.
    again = _run(pipeline, description="máy lạnh có chảy nước nữa", session_id=first.session_id)
    assert again.devices[0].device_type == "air_conditioner"


def test_a_dangerous_appliance_raises_the_whole_reply():
    reply = _run(_pipeline(), description="máy lạnh không mát, bếp gas nhà em có mùi gas nồng lắm")
    assert reply.urgency.value == "HIGH"


def test_a_correction_drops_the_appliance_it_replaces():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh nhà em không mát")
    after = _run(pipeline, description="không phải máy lạnh, là tủ lạnh", session_id=first.session_id)
    assert after.devices == []
    assert [s.service_code for s in after.recommended_services][:1] == ["FR-01"]


def test_an_appliance_whose_repair_is_not_open_is_listed_without_a_service():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("microwave_oven")],
    )
    microwave = reply.devices[1]
    assert microwave.service is None
    assert "chưa mở dịch vụ" in microwave.note_vi
    assert all(s.device_type != "microwave_oven" for s in reply.recommended_services)


def test_never_more_than_three():
    reply = _run(
        _pipeline(),
        description="máy lạnh không mát, máy giặt không vắt, tủ lạnh không lạnh, bếp từ không nóng",
    )
    assert len(reply.devices) == 3
    assert len(reply.recommended_services) <= 3
    assert "tối đa 3 thiết bị" in reply.message_vi


def test_a_cleaning_service_says_what_settles_its_price():
    reply = _run(
        _pipeline(),
        description="máy giặt không vắt được",
        images=[_photo("washing_machine"), _photo("air_conditioner")],
    )
    ac = reply.devices[1]
    assert ac.service is not None and ac.service.service_code == "AC-01"
    assert ac.price_estimate is not None and ac.price_estimate.requires_assessment


def test_the_wire_names_are_camel_case():
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("washing_machine")],
    )
    payload = reply.model_dump(by_alias=True)
    entry = payload["devices"][1]
    assert {"deviceType", "nameVi", "imageIndex", "isPrimary", "service", "priceEstimate"} <= set(entry)
    assert payload["recommendedServices"][1]["deviceType"] == "washing_machine"


def test_moving_to_a_photographed_appliance_asks_what_is_wrong_with_it():
    """Nothing was said about the fridge; it was only in the second photograph.

    The air conditioner's "không mát" used to be read as the fridge's symptom,
    and the answer it had already been given made the fridge skip its
    questions: "xem tiếp" came back as a fridge short of gas.
    """
    pipeline = _pipeline()
    first = _run(
        pipeline,
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("refrigerator")],
    )
    fridge = first.devices[1]
    assert fridge.device_type == "refrigerator" and fridge.status.value == "needs_clarification"
    assert "đang bị sao" in fridge.message_vi and fridge.suspected_faults == []
    assert fridge.service is not None and fridge.service.service_code == "FR-01"
    after = _run(pipeline, description="tủ lạnh thì không đông đá", session_id=first.session_id)
    assert after.devices[0].device_type == "refrigerator"
    assert after.suspected_faults and all(f.fault_code.startswith("FRIDGE") for f in after.suspected_faults)


def test_what_was_said_about_one_appliance_is_not_searched_for_another():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát, tủ lạnh thì kêu to")
    chat = pipeline._conversations.get_or_create(first.session_id)
    fridge = pipeline._conversations.get_or_create(chat.others["refrigerator"])
    assert "kêu to" not in chat.device_text()
    assert "không mát" not in fridge.device_text() and "kêu to" in fridge.device_text()
    entry = next(d for d in first.devices if d.device_type == "refrigerator")
    assert all(f.fault_code.startswith("FRIDGE") for f in entry.suspected_faults)


def test_the_appliance_named_leads_even_when_no_photograph_shows_it():
    """"Máy lạnh không mát" with a photograph the detector cannot read and one
    of the washing machine used to be answered about the washing machine alone;
    the air conditioner the customer was talking about vanished."""
    reply = _run(
        _pipeline(),
        description="máy lạnh nhà em không mát",
        images=[_blank(), _photo("washing_machine")],
    )
    assert [d.device_type for d in reply.devices] == ["air_conditioner", "washing_machine"]
    assert reply.devices[0].is_primary and reply.devices[0].image_index is None
    assert reply.devices[1].image_index == 1
    assert [s.service_code for s in reply.recommended_services][1:] == ["WM-01"]


def test_one_photograph_still_decides_with_the_words_as_before():
    reply = _run(_pipeline(), description="máy lạnh nhà em không mát", images=[_photo("washing_machine")])
    assert reply.devices == [] or reply.devices[0].is_primary


def test_a_plain_photograph_does_not_put_the_model_ahead_of_retrieval():
    """With a photograph and no damage seen in it, retrieval's leader leads.

    fixhome.sbs 25/10/2026: a photo of an air conditioner and "chạy cả ngày mà
    phòng vẫn nóng" came back as a failed compressor, the model's pick, ahead
    of retrieval's low refrigerant; nothing in the photo was about a compressor."""
    from app.services.pipeline.local_pipeline import _ranked_by_retrieval
    from types import SimpleNamespace as F

    shortlist = [F(fault_code="AC_LOW_REFRIGERANT"), F(fault_code="AC_COMPRESSOR_FAULT")]
    assert _ranked_by_retrieval(["AC_COMPRESSOR_FAULT"], shortlist, saw_a_photograph=False)[0] == "AC_LOW_REFRIGERANT"
    reply = _run(_pipeline(), description="máy lạnh chạy cả ngày mà phòng vẫn nóng", images=[_photo("air_conditioner")])
    assert [f.fault_code for f in reply.suspected_faults][:1] == ["AC_LOW_REFRIGERANT"]


# PO 25/10/2026: the reply must be about the appliance the customer is talking
# about, through the whole conversation, and an appliance photographed later
# joins the visit instead of replacing the one already talked through.

def _lead(reply):
    return next((d.device_type for d in reply.devices if d.is_primary), None)


def test_it_stays_on_the_appliance_just_talked_about():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    _run(pipeline, description="máy giặt thì không vắt", session_id=first.session_id)
    for said in ("nó kêu to nữa em", "vậy sửa hết bao nhiêu", "mà nó không lấy nước vào"):
        assert _lead(_run(pipeline, description=said, session_id=first.session_id)) == "washing_machine", said
    assert _lead(_run(pipeline, description="quay lại máy lạnh, nó chảy nước", session_id=first.session_id)) == "air_conditioner"


def test_the_photographs_are_pointed_at_by_their_place():
    pipeline = _pipeline()
    first = _run(
        pipeline,
        description="xem giúp em mấy cái này",
        images=[_photo("air_conditioner"), _photo("washing_machine"), _photo("refrigerator")],
    )
    assert _lead(_run(pipeline, description="cái thứ hai bị kêu to khi vắt", session_id=first.session_id)) == "washing_machine"
    assert _lead(_run(pipeline, description="anh 3 thi khong lanh", session_id=first.session_id)) == "refrigerator"
    assert _lead(_run(pipeline, description="hình số 1 chớp đèn không chạy", session_id=first.session_id)) == "air_conditioner"


def test_an_appliance_photographed_later_joins_the_visit():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner")])
    added = _run(pipeline, description="còn cái này nữa, không chạy", images=[_photo("microwave_oven")], session_id=first.session_id)
    assert added.session_id == first.session_id
    assert [d.device_type for d in added.devices] == ["microwave_oven", "air_conditioner"]
    chat = pipeline._conversations.get_or_create(first.session_id)
    assert chat.device_type == "air_conditioner"
    back = _run(pipeline, description="máy lạnh thì sao em", session_id=first.session_id)
    assert _lead(back) == "air_conditioner"
    assert all(f.fault_code.startswith("AC_") for f in back.suspected_faults)


def test_a_photograph_of_an_appliance_already_in_the_visit_goes_to_it():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    again = _run(pipeline, description="đây nè em, nó rung lắc mạnh", images=[_photo("washing_machine")], session_id=first.session_id)
    assert _lead(again) == "washing_machine"
    assert len(again.devices) == 2


def test_an_appliance_added_in_words_joins_the_visit():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát")
    added = _run(pipeline, description="à tủ lạnh thì ngăn đá không đông", session_id=first.session_id)
    assert [d.device_type for d in added.devices] == ["refrigerator", "air_conditioner"]


def test_a_child_is_not_an_appliance_added():
    pipeline = _pipeline()
    chat = pipeline._conversations.get_or_create(None)
    first = _run(pipeline, description="chuyện là tv nhà tui remote không ăn, con nhỏ nó cứ hỏi hoài đó", session_id=chat.session_id)
    assert not first.devices
    assert pipeline._conversations.get_or_create(first.session_id).device_type == "television"


def test_a_short_name_is_read_against_the_visit():
    pipeline = _pipeline()
    first = _run(
        pipeline,
        description="xem giúp em mấy cái này",
        images=[_photo("air_conditioner"), _photo("washing_machine")],
    )
    assert _lead(_run(pipeline, description="cục lạnh thì chảy nước", session_id=first.session_id)) == "air_conditioner"
    # "Từ hôm qua" is not "tủ".
    assert _lead(_run(pipeline, description="máy giặt nó kêu từ hôm qua", session_id=first.session_id)) == "washing_machine"


# Messages about several appliances, cut where each one starts. Each case is a
# shape eval_multi_message.py found on its dev half, 25/10/2026.

def _devices(text):
    return [d.device_type for d in _run(_pipeline(), description=text).devices]


def test_a_part_or_a_setting_is_not_a_correction():
    # "bộ chỉnh" folds to "bỏ", "chuyển sang gió mạnh" to a change of appliance.
    assert _devices(
        "tủ lạnh thấy cái dàn lưới phía sau rung rinh kêu rè rè suốt và quạt trần hổng biết hư quạt hay hỏng bộ chỉnh"
    ) == ["refrigerator", "ceiling_fan"]
    assert _devices(
        "máy giặt nước tràn qua miệng ống lênh láng, điều hòa mỗi lần chuyển sang gió mạnh là rung bần bật"
    ) == ["washing_machine", "air_conditioner"]
    assert _devices(
        "máy sấy bảng điều khiển không có điện, chắc hư bo rồi ống nước trong tường bắn ra như vòi cứu hỏa"
    ) == ["clothes_dryer", "water_pipe"]


def test_a_real_correction_is_still_one_appliance():
    reply = _run(_pipeline(), description="không phải máy lạnh mà là tủ lạnh không đông đá")
    assert reply.devices == [] or [d.device_type for d in reply.devices] == ["refrigerator"]


def test_a_connector_opens_the_next_appliance():
    assert _devices("tivi mất tiếng ngoài ra tủ lạnh ron cửa bị chai") == ["television", "refrigerator"]
    assert _devices("cho hoi chut, may say khong nong va bep gas cai num xoay cung ngac") == ["clothes_dryer", "gas_stove"]
    assert _devices("tivi thấy người cử động bên trong, lò nướng set 160 độ mà lên tận 230") == ["television", "oven"]


def test_spoken_fillers_do_not_hide_a_name():
    assert _devices("quạt à trần đo cái tụ thấy tụt một nửa với lại bếp kiểu là từ màn hình chớp chớp") == [
        "ceiling_fan", "induction_hob"
    ]


def test_teencode_names_are_found_with_the_others():
    assert _devices("máy giặt chạy xong nước vẫn ngập, ống nc nhà e tắm xong nước xuống phễu kêu òng ọc") == [
        "washing_machine", "water_pipe"
    ]


def test_bare_bet_and_den_opening_a_clause_are_the_toilet_and_the_light():
    # eval_multi_message.py dev half, 27/10/2026: the two appliances missed most.
    assert _devices(
        "bệt nhà mình ngồi xuống là tấm ngồi kêu cót két rồi lệch sang một bên, cả con Daikin cái điều khiển giờ như cục gạch"
    ) == ["toilet", "air_conditioner"]
    assert _devices(
        "máy giặt mở nắp ra là xộc lên mùi hôi như cống, còn đèn vừa bật lên thì chớp sáng chói một cái rồi tối hẳn"
    ) == ["washing_machine", "light_bulb"]
    # Not where it is the appliance's own light, or sitting on the floor.
    assert "light_bulb" not in _devices("lò vi sóng em đã thay cầu chì mà đèn không lên, máy giặt không vắt")
    assert "light_bulb" not in _devices("tủ lạnh không lạnh, đèn trong tủ vẫn sáng, máy giặt không vắt")
    assert "toilet" not in _devices("ngồi bệt xuống nhìn thì máy giặt rỉ nước dưới gầm, tủ lạnh không lạnh")


def test_a_connector_with_a_classifier_still_opens_the_next_appliance():
    # "Ngoài ra cái điều hòa" read as "ra cái điều hòa", an object, and was dropped.
    assert _devices(
        "chậu rửa bị gỉ ăn thủng, giọt nước nâu nhỏ xuống, còn lò nướng núm hẹn giờ bị lờn ngoài ra cái điều hòa mở 24 độ mà dàn trong kết đá"
    ) == ["sink", "oven", "air_conditioner"]
    assert _devices(
        "bồn rửa nước xoay vòng rồi đứng lại ngoài ra con Daikin bật lại được nửa ngày thì lớp trắng lại phủ kín"
    ) == ["sink", "air_conditioner"]


def test_what_is_meant_by_the_words_around_a_name():
    assert "light_bulb" not in _devices("bếp từ đèn chờ không sáng, máy giặt không vắt")
    assert _devices("cái quạt trên trần nhà quay uể oải, máy giặt không vắt") == ["ceiling_fan", "washing_machine"]
    assert _devices("bình đun nước tắm không nóng, tủ lạnh không lạnh") == ["water_heater", "refrigerator"]


# fixhome.sbs with the served model, 25/10/2026: three photographs, the third
# not recognised, then a fourth appliance named but its photograph held back
# by the web's three-photo limit.

def test_a_symptom_of_an_appliance_not_yet_in_the_visit_brings_it_in():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh nhà em không mát", images=[_photo("air_conditioner"), _photo("washing_machine"), _blank()])
    _run(pipeline, description="còn máy giặt thì vắt kêu rất to", session_id=first.session_id)
    fridge = _run(pipeline, description="cái thứ ba thì ngăn đá không đông", session_id=first.session_id)
    assert _lead(fridge) == "refrigerator"
    assert all(f.fault_code.startswith("FRIDGE_") for f in fridge.suspected_faults)


def test_a_fan_added_in_words_without_its_photograph():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    _run(pipeline, description="còn máy giặt thì vắt kêu rất to", session_id=first.session_id)
    fan = _run(pipeline, description="còn cái này nữa, quạt bật không quay", session_id=first.session_id)
    assert _lead(fan) == "electric_fan"


def test_one_more_symptom_is_not_one_more_appliance():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy giặt rung lắc mạnh", images=[_photo("washing_machine"), _photo("air_conditioner")])
    again = _run(pipeline, description="nó không cấp nước luôn em", session_id=first.session_id)
    assert _lead(again) == "washing_machine"
    assert "water_pipe" not in [d.device_type for d in again.devices]


def test_the_appliance_named_outright_beats_a_photograph_read_as_another():
    # The served detector, 25/10/2026: an air conditioner read as a fan, a
    # water heater as a smart lock, and the reply followed the photograph.
    reply = _run(_pipeline(), description="máy lạnh không mát", images=[_photo("washing_machine")])
    assert all(f.fault_code.startswith("AC_") for f in reply.suspected_faults)
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    fridge = _run(
        pipeline, description="đây là cái tủ lạnh, ngăn mát không lạnh", images=[_photo("microwave_oven")],
        session_id=first.session_id,
    )
    assert _lead(fridge) == "refrigerator"
    assert "microwave_oven" not in [d.device_type for d in fridge.devices]


def test_a_photograph_nobody_could_read_leaves_the_words_to_decide():
    # fixhome.sbs, 25/10/2026: a fridge the detector did not recognise, sent
    # with "ngăn mát không lạnh", was answered about the air conditioner.
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh nhà em không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    _run(pipeline, description="máy giặt thì không vắt được em", session_id=first.session_id)
    fridge = _run(pipeline, description="còn cái này nữa em, ngăn mát không lạnh", images=[_blank()], session_id=first.session_id)
    assert _lead(fridge) == "refrigerator"
    price = _run(pipeline, description="cái đó sửa hết bao nhiêu tiền", session_id=first.session_id)
    assert _lead(price) == "refrigerator"


def test_a_closing_sentence_is_said_once_for_the_whole_reply():
    from app.services.pipeline.local_pipeline import _said_once

    text = (
        "Về tivi: Hiện FixHome chưa mở dịch vụ sửa tivi. Anh/chị cần sửa thiết bị khác thì nhắn em nhé.\n\n"
        "Về lò vi sóng: Hiện FixHome chưa mở dịch vụ sửa lò vi sóng. Anh/chị cần sửa thiết bị khác thì nhắn em nhé.\n\n"
        "Chi phí tham khảo từ 199.000đ, thợ xem tận nơi."
    )
    once = _said_once(text)
    assert once.count("nhắn em nhé") == 1
    assert "Về lò vi sóng: Hiện FixHome chưa mở dịch vụ sửa lò vi sóng." in once


def test_a_question_goes_to_the_appliance_it_is_about():
    from app.schemas.chat import ChatRequest

    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh nhà em không mát", images=[_photo("air_conditioner"), _photo("washing_machine")])
    _run(pipeline, description="còn cái này nữa em, ngăn mát không lạnh", images=[_photo("refrigerator")], session_id=first.session_id)
    reply = asyncio.run(pipeline.answer(ChatRequest(question="cái đó sửa hết bao nhiêu tiền", sessionId=first.session_id)))
    assert reply.session_id == first.session_id
    # Asked for the price, it says the fridge's price, figures and all.
    assert "tủ lạnh" in reply.answer_vi and re.search(r"\d{3}\.000đ", reply.answer_vi), reply.answer_vi
    question = asyncio.run(pipeline.answer(ChatRequest(question="cái đó có nguy hiểm không em", sessionId=first.session_id)))
    fridge = pipeline._conversations.peek(pipeline._conversations.peek(first.session_id).others["refrigerator"])
    assert question.session_id == first.session_id
    assert any(t.text_vi == "cái đó có nguy hiểm không em" for t in fridge.turns)


def test_a_symptom_only_one_appliance_has_beats_a_misread_photograph():
    # The served detector read a fridge as a washing machine; the words said
    # "đá không đông".
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát", images=[_photo("air_conditioner")])
    again = _run(pipeline, description="em gửi thêm ảnh, cái này ngăn đá không đông", images=[_photo("washing_machine")], session_id=first.session_id)
    assert _lead(again) == "refrigerator"


def test_overlapping_names_are_read_the_same_way_every_time():
    from app.services.pipeline.local_pipeline import _named_spans_uncached

    # "vòi nước máy" holds "vòi nước" and "nước máy"; which won depended on the
    # order a set iterated in, so one message was cut differently per process.
    spans = _named_spans_uncached("máy lọc nước nhà em tắc lõi, vòi nước máy bên cạnh vẫn chảy", KB)
    assert [s[0] for s in spans] == ["water_purifier", "faucet"] or [s[0] for s in sorted(spans, key=lambda s: s[2])] == [
        "water_purifier", "faucet"
    ]
    # And a name never runs across punctuation: "đọng nước - máy lạnh".
    spans = _named_spans_uncached("đèn bên trong đọng nước - máy lạnh chạy có mùi khét", KB)
    assert "water_pipe" not in [s[0] for s in spans]
    assert "air_conditioner" in [s[0] for s in spans]
