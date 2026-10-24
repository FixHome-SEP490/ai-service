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
    assert "xem tiếp" in reply.message_vi


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


def test_moving_on_keeps_the_first_appliance_on_the_visit():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát, máy giặt thì không vắt được")
    after = _run(pipeline, description="xem tiếp", session_id=first.session_id)
    assert [d.device_type for d in after.devices] == ["washing_machine", "air_conditioner"]
    assert after.devices[0].is_primary
    assert after.devices[1].service is not None


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
    after = _run(pipeline, description="xem tiếp", session_id=first.session_id)
    assert after.status.value == "needs_clarification"
    assert after.suspected_faults == []
    assert [s.service_code for s in after.recommended_services][:1] == ["FR-01"]


def test_what_was_said_about_one_appliance_is_not_searched_for_another():
    pipeline = _pipeline()
    first = _run(pipeline, description="máy lạnh không mát, tủ lạnh thì kêu to")
    after = _run(pipeline, description="xem tiếp", session_id=first.session_id)
    chat = pipeline._conversations.get_or_create(after.session_id)
    assert "không mát" not in chat.device_text()
    assert "kêu to" in chat.device_text()
    assert all(f.fault_code.startswith("FRIDGE") for f in after.suspected_faults)
