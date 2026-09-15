# app/services/pipeline/detector.py
"""Device detector stage.

YOLOv8n locates the appliance in the photo and classifies it into the closed
catalog, then hands the crop downstream. Two reasons this stage exists instead
of asking the VLM directly: a small detector trained on the team's own photos
identifies Vietnamese household appliances more reliably than a general 3B
model, and the crop lets the VLM spend its attention on the device rather than
the room around it.

The real implementation loads Ultralytics weights. `StubDetector` keeps CI free
of model downloads and GPU requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from app.services.pipeline.knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class Detection:
    device_type: str
    confidence: float
    box_xywh: tuple[int, int, int, int]
    crop_ref: str
    """Opaque handle to the cropped region passed to the VLM stage."""


class Detector(Protocol):
    async def detect(self, image_ref: str) -> List[Detection]:
        """Return detections ordered by confidence, highest first."""
        ...


class StubDetector:
    """Deterministic stand-in used by tests and by local runs without weights."""

    def __init__(self, kb: KnowledgeBase, device_type: Optional[str] = None) -> None:
        self._kb = kb
        self._device_type = device_type or (kb.device_types[0] if kb.device_types else "")

    async def detect(self, image_ref: str) -> List[Detection]:
        if not self._device_type:
            return []
        return [
            Detection(
                device_type=self._device_type,
                confidence=0.91,
                box_xywh=(0, 0, 640, 640),
                crop_ref=image_ref,
            )
        ]


class YoloDetector:
    """Ultralytics YOLOv8n wrapper.

    Deliberately not imported at module scope: the service must start and the
    test suite must run on machines with no torch and no weights.
    """

    def __init__(self, weights_path: str, kb: KnowledgeBase, min_confidence: float) -> None:
        self._weights_path = weights_path
        self._kb = kb
        self._min_confidence = min_confidence
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from ultralytics import YOLO  # local import, optional dependency

            self._model = YOLO(self._weights_path)

    async def detect(self, image_ref: str) -> List[Detection]:
        raise NotImplementedError(
            "YoloDetector requires trained weights; see docs/AI-TECHNICAL-GUIDE.md"
        )
