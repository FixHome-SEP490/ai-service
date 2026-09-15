"""Roboflow Universe datasets surveyed for this project.

Recorded here rather than in a document so the download script and the report
cite the same numbers. Image counts are as published on Universe at the time of
survey and are approximate; `fetch_roboflow.py list` prints what the API
actually reports today.

Every entry is CC BY 4.0, which means the report must credit the source. The
`class_map` translates each dataset's own class names into this project's
`device_type` values; a name absent from the map is dropped on import, which is
how the unrelated classes in the larger sets are filtered out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RoboflowSource:
    workspace: str
    project: str
    version: int
    images: int
    """As published on Universe when surveyed; approximate."""
    class_map: Dict[str, str]
    note: str = ""
    covers: List[str] = field(default_factory=list)

    total_classes: int = 1
    """Classes the dataset declares, including ones this project ignores."""

    @property
    def slug(self) -> str:
        return f"{self.workspace}/{self.project}:{self.version}"

    @property
    def images_per_class(self) -> int:
        """Rough per-class share of a multi-class dataset.

        A 3695-image set covering sixteen classes does not give this project
        3695 water heaters. Dividing is crude, since real datasets are never
        balanced, but it is far closer than quoting the dataset total and it
        keeps an inflated number out of the report.
        """
        if not self.images or self.total_classes <= 0:
            return 0
        return self.images // self.total_classes


SOURCES: List[RoboflowSource] = [
    RoboflowSource(
        workspace="hcmus-38m1y",
        project="air-conditioner-dr0fw",
        version=1,
        images=2314,
        class_map={"conditioner": "air_conditioner"},
        covers=["air_conditioner"],
        total_classes=1,
        note="Vietnamese team; likely the closest to local hardware",
    ),
    RoboflowSource(
        workspace="leeji9689-gmail-com",
        project="ac-08nlv",
        version=1,
        images=888,
        # The export declares a single unnamed class "0"; the dataset is
        # entirely air conditioners, so class 0 is unambiguous.
        class_map={"0": "air_conditioner"},
        covers=["air_conditioner"],
        total_classes=1,
    ),
    RoboflowSource(
        workspace="yolo-uv06o",
        project="air-conditioning-dataset",
        version=1,
        images=164,
        class_map={"air_conditioning": "air_conditioner"},
        covers=["air_conditioner"],
        total_classes=1,
    ),
    RoboflowSource(
        workspace="bassam-xhjea",
        project="air-conditioner",
        version=1,
        images=86,
        class_map={"air conditioner": "air_conditioner"},
        covers=["air_conditioner"],
        total_classes=1,
    ),
    RoboflowSource(
        workspace="house-hold-electronics",
        project="household-electronics-alry3",
        version=1,
        images=0,
        class_map={
            "ac": "air_conditioner",
            "fan": "electric_fan",
            # "fn" is a duplicate of "fan" left in by the author; dropping it
            # would discard usable boxes for no reason.
            "fn": "electric_fan",
            "light": "light_bulb",
        },
        covers=["air_conditioner", "electric_fan", "light_bulb"],
        total_classes=5,
        note="count not published; 'objects' class is dropped as meaningless here",
    ),
    RoboflowSource(
        workspace="evesyalari",
        project="household-appliances-3zh8e-e9y5g",
        version=1,
        images=3695,
        class_map={
            "hot water shower machine": "water_heater",
            "microwave oven": "microwave_oven",
            "super kettle": "kettle",
            "electric cooker": "oven",
            "electriccooker": "oven",
        },
        covers=["water_heater", "microwave_oven", "kettle", "oven"],
        total_classes=16,
        note=(
            "16 classes; the only public source for water heater. The 12 unused "
            "classes (blender, iron, vacuum, hair dryer, shaver, juicer, air "
            "purifier, water purifier, electric toothbrush, wifi router) are "
            "worth revisiting when the catalog grows past 15"
        ),
    ),
    RoboflowSource(
        workspace="yolov5-dtypd",
        project="plug-socket-detect",
        version=1,
        images=318,
        class_map={
            "socket": "power_outlet",
            # plug_2pin is the flat two-pin plug used across Vietnam, so this
            # set is less foreign than its origin suggested.
            "plug_2pin": "power_outlet",
            "plug_3pin": "power_outlet",
            "plug_rectangle": "power_outlet",
        },
        covers=["power_outlet"],
        total_classes=4,
        note="mixed hardware; plug_2pin matches the local standard",
    ),
]


def sources_for(device_type: str) -> List[RoboflowSource]:
    return [s for s in SOURCES if device_type in s.covers]


def coverage() -> Dict[str, dict]:
    """Per device type: how many datasets cover it, and a conservative estimate.

    The estimate is a lower bound to plan against, not a measurement. The exact
    figure only appears after `fetch_roboflow.py download` counts the labels it
    actually imported.
    """
    totals: Dict[str, dict] = {}
    for source in SOURCES:
        for device_type in source.covers:
            entry = totals.setdefault(device_type, {"datasets": 0, "estimate": 0})
            entry["datasets"] += 1
            entry["estimate"] += source.images_per_class
    return totals
