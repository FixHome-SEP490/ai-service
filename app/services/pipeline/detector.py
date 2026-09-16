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

import asyncio
from dataclasses import dataclass
from typing import List, Optional, Protocol

from app.services.pipeline.images import ImagePayload
from app.services.pipeline.knowledge_base import KnowledgeBase


class DetectorClassMismatch(RuntimeError):
    """The weights and the device catalog disagree about the class list."""


@dataclass(frozen=True)
class Detection:
    device_type: str
    confidence: float
    box_xywh: tuple[int, int, int, int]
    crop: ImagePayload
    """The cropped device region handed to the VLM stage."""


class Detector(Protocol):
    async def detect(self, image: ImagePayload) -> List[Detection]:
        """Return detections ordered by confidence, highest first."""
        ...


class StubDetector:
    """Deterministic stand-in used by tests and by local runs without weights."""

    def __init__(self, kb: KnowledgeBase, device_type: Optional[str] = None) -> None:
        self._kb = kb
        self._device_type = device_type or (kb.device_types[0] if kb.device_types else "")

    async def detect(self, image: ImagePayload) -> List[Detection]:
        if not self._device_type:
            return []
        box = (0, 0, image.width, image.height)
        return [
            Detection(
                device_type=self._device_type,
                confidence=0.91,
                box_xywh=box,
                crop=image.crop(box),
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
        self._names: dict[int, str] = {}

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from ultralytics import YOLO  # local import, optional dependency

            model = YOLO(self._weights_path)
            self._names = {int(i): str(n) for i, n in model.names.items()}

            # The weights carry their own class list, and it is the weights that
            # decide what index 7 means. If it has drifted from the catalog, the
            # detector would keep working and quietly name the wrong appliance —
            # a toilet reported as an oven, with full confidence.
            unknown = sorted(set(self._names.values()) - set(self._kb.device_types))
            if unknown:
                raise DetectorClassMismatch(
                    f"The weights at {self._weights_path} predict classes that are "
                    f"not in the device catalog: {', '.join(unknown)}"
                )
            self._model = model

    async def detect(self, image: ImagePayload) -> List[Detection]:
        self._ensure_loaded()

        # Ultralytics is synchronous and CPU/GPU bound. Off the event loop it
        # goes, or one inference blocks every other request on the worker.
        results = await asyncio.to_thread(
            self._model.predict,
            image.image,
            conf=self._min_confidence,
            verbose=False,
        )
        if not results:
            return []

        detections: List[Detection] = []
        for box in results[0].boxes:
            left, top, right, bottom = (int(v) for v in box.xyxy[0].tolist())

            # Clamp to the frame. A box may extend past the edge, and a negative
            # origin silently flips PIL's crop into taking the wrong region
            # rather than raising.
            left, top = max(0, left), max(0, top)
            right = min(image.width, right)
            bottom = min(image.height, bottom)
            if right <= left or bottom <= top:
                continue

            box_xywh = (left, top, right - left, bottom - top)
            detections.append(
                Detection(
                    device_type=self._names[int(box.cls[0])],
                    confidence=float(box.conf[0]),
                    box_xywh=box_xywh,
                    crop=image.crop(box_xywh),
                )
            )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections
