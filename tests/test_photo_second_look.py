"""A photograph the detector is unsure of: a second look, a guess said aloud, a correction in a word.

The served detector, 25/10/2026, read washing machines as a sink or a smart
lock and water heaters as a fridge, and the reply followed the photograph.
"""

import asyncio

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.detector import Detection
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm
from tests.test_several_appliances import COLOURS, _photo

KB = get_knowledge_base()


class _Detector:
    """Reads the colour, at the confidence the test asks for."""

    def __init__(self, confidence=0.9, reads_as=None):
        self.confidence = confidence
        self.reads_as = reads_as or {}

    async def detect(self, image):
        device = COLOURS.get(tuple(image.image.convert("RGB").getpixel((1, 1))))
        if device is None:
            return []
        device = self.reads_as.get(device, device)
        return [Detection(device_type=device, confidence=self.confidence, box_xywh=(0, 0, 64, 48), crop=image)]


class _Looks(StubVlm):
    """A vision-language model that sees the photograph's true colour."""

    def __init__(self, sees=True):
        self.sees = sees
        self.asked = 0

    async def identify(self, image, choices):
        self.asked += 1
        if not self.sees:
            return None
        return COLOURS.get(tuple(image.image.convert("RGB").getpixel((1, 1))))


def _pipeline(detector, vlm):
    sc.install(sc.LiveCatalog())
    return LocalPipeline(detector=detector, vlm=vlm, retriever=Retriever(KB), kb=KB)


def _run(pipeline, **kwargs):
    return asyncio.run(pipeline.diagnose(DiagnosisRequest(**kwargs)))


def test_a_confident_detection_is_not_asked_about():
    vlm = _Looks()
    reply = _run(_pipeline(_Detector(0.92), vlm), description="xem giúp em", images=[_photo("washing_machine")])
    assert vlm.asked == 0
    assert reply.device and not reply.device.uncertain


def test_an_unsure_detection_the_model_confirms_is_no_guess():
    vlm = _Looks()
    reply = _run(_pipeline(_Detector(0.55), vlm), description="xem giúp em", images=[_photo("washing_machine")])
    assert vlm.asked == 1
    assert reply.device.device_type == "washing_machine" and not reply.device.uncertain
    assert "Em đoán" not in (reply.message_vi or "")


def test_the_model_replaces_a_misread_and_the_reply_says_it_guessed():
    detector = _Detector(0.55, reads_as={"washing_machine": "refrigerator"})
    reply = _run(_pipeline(detector, _Looks()), description="xem giúp em", images=[_photo("washing_machine")])
    assert reply.device.device_type == "washing_machine"
    assert reply.device.uncertain
    assert "Em đoán ảnh là máy giặt" in reply.message_vi


def test_with_no_model_a_weak_detection_is_said_as_a_guess():
    reply = _run(
        _pipeline(_Detector(0.5), _Looks(sees=False)),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("washing_machine")],
    )
    guessed = [d.device_type for d in reply.devices if d.uncertain]
    assert guessed == ["air_conditioner", "washing_machine"]
    assert "Em đoán ảnh 1 là" in reply.message_vi and "ảnh 2 là máy giặt" in reply.message_vi


def test_a_photograph_corrected_in_a_word_changes_the_visit():
    detector = _Detector(0.55, reads_as={"refrigerator": "washing_machine"})
    pipeline = _pipeline(detector, _Looks(sees=False))
    first = _run(
        pipeline, description="máy lạnh nhà em không mát", images=[_photo("air_conditioner"), _photo("refrigerator")]
    )
    assert [d.device_type for d in first.devices] == ["air_conditioner", "washing_machine"]
    fixed = _run(pipeline, description="ảnh 2 là tủ lạnh", session_id=first.session_id)
    assert [d.device_type for d in fixed.devices] == ["refrigerator", "air_conditioner"]
    assert fixed.devices[0].is_primary and not fixed.devices[0].uncertain


def test_the_conversation_own_appliance_corrected_by_its_photograph():
    detector = _Detector(0.55, reads_as={"air_conditioner": "washing_machine"})
    pipeline = _pipeline(detector, _Looks(sees=False))
    first = _run(pipeline, description="xem giúp em", images=[_photo("air_conditioner")])
    assert first.device.device_type == "washing_machine" and first.device.uncertain
    fixed = _run(pipeline, description="ảnh này là máy lạnh", session_id=first.session_id)
    chat = pipeline._conversations.get_or_create(first.session_id)
    assert chat.device_type == "air_conditioner"
    assert all(f.fault_code.startswith("AC_") for f in fixed.suspected_faults)


def test_each_photograph_of_the_request_is_reported_in_order():
    detector = _Detector(0.55, reads_as={"refrigerator": "washing_machine"})
    reply = _run(
        _pipeline(detector, _Looks(sees=False)),
        description="máy lạnh nhà em không mát",
        images=[_photo("air_conditioner"), _photo("refrigerator")],
    )
    assert [(p.index, p.device_type, p.uncertain) for p in reply.photos] == [
        (0, "air_conditioner", True),
        (1, "washing_machine", True),
    ]
    wire = reply.model_dump(by_alias=True)
    assert wire["photos"][1] == {"index": 1, "deviceType": "washing_machine", "nameVi": "Máy giặt", "uncertain": True}


def test_no_photograph_no_readings():
    reply = _run(_pipeline(_Detector(), _Looks()), description="máy lạnh không mát")
    assert reply.photos == []
