"""The detector stage, without torch or weights.

The real model is replaced by an object with the shape Ultralytics returns, so
the box arithmetic, the ordering and the class-name mapping are all exercised on
a machine that has neither a GPU nor a download.
"""

from types import SimpleNamespace

import pytest
from PIL import Image

from app.services.pipeline.detector import (
    DetectorClassMismatch,
    YoloDetector,
)
from app.services.pipeline.images import ImagePayload
from app.services.pipeline.knowledge_base import get_knowledge_base


def _payload(width: int = 800, height: int = 600) -> ImagePayload:
    return ImagePayload(
        image=Image.new("RGB", (width, height), (180, 180, 180)),
        mime_type="image/jpeg",
        width=width,
        height=height,
    )


class _Box:
    def __init__(self, xyxy, cls, conf):
        self.xyxy = [SimpleNamespace(tolist=lambda v=xyxy: list(v))]
        self.cls = [cls]
        self.conf = [conf]


def _detector(names, boxes) -> YoloDetector:
    detector = YoloDetector(weights_path="unused.pt", kb=get_knowledge_base(), min_confidence=0.25)
    detector._names = names
    detector._model = SimpleNamespace(
        predict=lambda *a, **k: [SimpleNamespace(boxes=boxes)]
    )
    return detector


@pytest.mark.asyncio
async def test_detections_come_back_highest_confidence_first():
    detector = _detector(
        {0: "air_conditioner", 1: "television"},
        [_Box((10, 10, 110, 110), 0, 0.42), _Box((20, 20, 220, 220), 1, 0.91)],
    )
    found = await detector.detect(_payload())
    assert [d.device_type for d in found] == ["television", "air_conditioner"]
    assert found[0].box_xywh == (20, 20, 200, 200)


@pytest.mark.asyncio
async def test_a_box_running_off_the_frame_is_clamped():
    """A negative origin makes PIL crop a different region instead of raising.

    Left alone, the crop handed to the VLM would be of somewhere else in the
    photograph, and nothing downstream could tell.
    """
    detector = _detector({0: "television"}, [_Box((-30, -10, 900, 700), 0, 0.8)])
    found = await detector.detect(_payload(800, 600))
    assert found[0].box_xywh == (0, 0, 800, 600)
    assert found[0].crop.width == 800
    assert found[0].crop.height == 600


@pytest.mark.asyncio
async def test_a_degenerate_box_is_dropped_rather_than_cropped():
    detector = _detector({0: "television"}, [_Box((900, 700, 950, 780), 0, 0.8)])
    assert await detector.detect(_payload(800, 600)) == []


def test_weights_naming_a_class_outside_the_catalog_are_refused(monkeypatch):
    """Index 7 means whatever the weights say it means.

    If the two lists drift apart the detector keeps working and names the wrong
    appliance with full confidence, which no caller can detect.
    """
    import app.services.pipeline.detector as module

    fake = SimpleNamespace(names={0: "air_conditioner", 1: "spaceship"})
    monkeypatch.setitem(
        __import__("sys").modules,
        "ultralytics",
        SimpleNamespace(YOLO=lambda path: fake),
    )
    detector = module.YoloDetector(
        weights_path="stale.pt", kb=get_knowledge_base(), min_confidence=0.25
    )
    with pytest.raises(DetectorClassMismatch, match="spaceship"):
        detector._ensure_loaded()


@pytest.mark.parametrize(
    "given",
    ["http://host:8000", "http://host:8000/", "http://host:8000/v1", "http://host:8000/v1/"],
)
def test_the_vlm_address_is_accepted_with_or_without_the_v1_suffix(given):
    """vLLM prints its address as .../v1, so that is what gets pasted.

    Appending another produced /v1/v1/chat/completions and a 404, and the
    pipeline reports a failed call as low confidence, so a wrong address looked
    like an inconclusive photograph rather than a misconfiguration.
    """
    from app.services.pipeline.qwen_client import QwenClient

    client = QwenClient(base_url=given, model_name="m", timeout_seconds=1.0)
    assert client._url == "http://host:8000/v1/chat/completions"


def test_a_code_in_the_wrong_field_is_moved_rather_than_discarded():
    """burn_mark is a real condition code the model put under fault_codes.

    Dropping it left a socket described as "cháy đen, có mùi khét" with an
    empty diagnosis: the most urgent case in the catalogue, silently lost. A
    code from our own vocabulary in the wrong slot is a mistake about where to
    put it, not an invention.
    """
    from app.services.pipeline.qwen_client import _parse_verdict

    verdict = _parse_verdict(
        '{"fault_codes": ["burn_mark", "OUTLET_SHORT_CIRCUIT"],'
        ' "condition_codes": [], "confidence": 0.7}',
        allowed_faults=["OUTLET_SHORT_CIRCUIT", "OUTLET_OVERLOAD"],
        allowed_conditions=["burn_mark", "crack"],
    )
    assert verdict.fault_codes == ["OUTLET_SHORT_CIRCUIT"]
    assert verdict.condition_codes == ["burn_mark"]


def test_an_invented_code_is_still_refused():
    from app.services.pipeline.qwen_client import _parse_verdict

    verdict = _parse_verdict(
        '{"fault_codes": ["OUTLET_ON_FIRE"], "condition_codes": ["smells_bad"],'
        ' "confidence": 0.9}',
        allowed_faults=["OUTLET_SHORT_CIRCUIT"],
        allowed_conditions=["burn_mark"],
    )
    assert verdict.fault_codes == []
    assert verdict.condition_codes == []
    assert verdict.confidence == 0.0


def test_nothing_was_seen_when_nothing_was_sent():
    """A text-only call came back describing cracks and scratches.

    There was no photograph. The model was told "thiết bị đã được nhận diện từ
    ảnh" on a call carrying no image, and obliged. Whatever it claims to have
    seen, a turn with no image saw nothing.
    """
    from app.services.pipeline.qwen_client import _parse_verdict

    verdict = _parse_verdict(
        '{"fault_codes": ["OVEN_THERMOSTAT"], "condition_codes": ["crack", "rust"],'
        ' "confidence": 0.8}',
        allowed_faults=["OVEN_THERMOSTAT"],
        allowed_conditions=["crack", "rust"],
        has_image=False,
    )
    assert verdict.fault_codes == ["OVEN_THERMOSTAT"]
    assert verdict.condition_codes == []
