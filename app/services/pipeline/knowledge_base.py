# app/services/pipeline/knowledge_base.py
"""Loads the curated catalog, the fault knowledge base and the service mapping.

Every Vietnamese string and price the service returns comes from here, never
from model free text. Editing the JSON is how the team changes wording or
pricing; no retraining involved.

Ownership is split deliberately. Fault codes belong to this service and the team
authors them now. Service codes belong to Backend, so they live in
`service_mapping.json` and stay empty until that catalog is agreed; filling one
file is then the whole integration, with no change to the fault data or code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Fault:
    fault_code: str
    device_type: str
    name_vi: str
    symptoms_vi: List[str]
    price_min: int
    price_max: int
    urgency: str
    suggested_actions_vi: List[str]
    price_reviewed: bool = False
    """Whether a person has checked the range against current market rates.

    Estimated ranges are usable for an advisory figure but must not be presented
    as authoritative, and the team needs to see at a glance which entries are
    still guesses."""


@dataclass(frozen=True)
class ServiceRef:
    """A Backend service a fault maps to. Absent until Backend agrees a catalog."""

    service_code: str
    name_vi: str


@dataclass(frozen=True)
class Policy:
    doc_id: str
    title_vi: str
    content_vi: str


class KnowledgeBase:
    def __init__(self, catalog: dict, kb: dict, mapping: dict) -> None:
        self._device_names: Dict[str, str] = {
            d["device_type"]: d["name_vi"] for d in catalog["devices"]
        }
        self._service_groups: Dict[str, str] = {
            d["device_type"]: d["service_group"] for d in catalog["devices"]
        }
        self._condition_names: Dict[str, str] = {
            c["code"]: c["name_vi"] for c in catalog["visible_conditions"]
        }
        self._detector_classes: List[str] = [
            d["device_type"] for d in catalog["devices"] if d.get("detector_class")
        ]
        self._open_images_classes: Dict[str, Optional[str]] = {
            d["device_type"]: d.get("open_images_class") for d in catalog["devices"]
        }
        self._faults: List[Fault] = [Fault(**f) for f in kb["faults"]]
        self._policies: List[Policy] = [Policy(**p) for p in kb["policies"]]
        self._services: Dict[str, List[ServiceRef]] = {}
        for entry in mapping.get("mappings", []):
            self._services[entry["fault_code"]] = [
                ServiceRef(service_code=s["service_code"], name_vi=s["name_vi"])
                for s in entry.get("services", [])
            ]

    @property
    def device_types(self) -> List[str]:
        return list(self._device_names)

    @property
    def detector_classes(self) -> List[str]:
        """Device types YOLO is trained on. The rest are text-only diagnoses."""
        return list(self._detector_classes)

    def open_images_class(self, device_type: str) -> Optional[str]:
        """Source class in Open Images V7, or None when images must be collected."""
        return self._open_images_classes.get(device_type)

    @property
    def condition_codes(self) -> List[str]:
        return list(self._condition_names)

    @property
    def policies(self) -> List[Policy]:
        return list(self._policies)

    def device_name_vi(self, device_type: str) -> Optional[str]:
        return self._device_names.get(device_type)

    def service_group(self, device_type: str) -> Optional[str]:
        return self._service_groups.get(device_type)

    def condition_name_vi(self, code: str) -> Optional[str]:
        return self._condition_names.get(code)

    def faults_for_device(self, device_type: str) -> List[Fault]:
        return [f for f in self._faults if f.device_type == device_type]

    def fault(self, fault_code: str) -> Optional[Fault]:
        return next((f for f in self._faults if f.fault_code == fault_code), None)

    def services_for_fault(self, fault_code: str) -> List[ServiceRef]:
        """Empty while Backend has not supplied a catalog. Not an error."""
        return list(self._services.get(fault_code, []))

    def all_service_groups(self) -> List[str]:
        return sorted(set(self._service_groups.values()))


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    catalog = json.loads((DATA_DIR / "device_catalog.json").read_text(encoding="utf-8"))
    kb = json.loads((DATA_DIR / "fault_knowledge_base.json").read_text(encoding="utf-8"))
    mapping = json.loads((DATA_DIR / "service_mapping.json").read_text(encoding="utf-8"))
    return KnowledgeBase(catalog=catalog, kb=kb, mapping=mapping)
