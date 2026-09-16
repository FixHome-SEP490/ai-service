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
from dataclasses import dataclass, field
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

    requires_assessment: bool = False
    """The tables cannot put a ceiling on this one.

    Either the cost is genuinely open-ended — a cracked TV panel, a holed water
    heater — or no labour row covers the work and no part stands in for it, so
    the only figure available is the inspection fee. Showing that as a confident
    number would read as the price of the repair. `price_max` is 0 here, and the
    customer is told a technician has to look."""

    labour_code: Optional[str] = None
    part_codes: List[str] = field(default_factory=list)
    """What the range was computed from, so a quote can be traced back."""

    price_note_vi: Optional[str] = None


@dataclass(frozen=True)
class ServiceRef:
    """A Backend service a fault maps to. Absent until Backend agrees a catalog."""

    service_code: str
    name_vi: str


@dataclass(frozen=True)
class Discriminator:
    """A question whose answer removes candidates.

    Written by hand because the most useful ones ask about something no symptom
    mentions: whether the unit was cleaned recently, whether the breaker trips,
    whether other lights in the house do the same. Those separate faults that
    share every listed symptom.
    """

    device_type: str
    question_vi: str
    favours_if_yes: List[str]
    favours_if_no: List[str]


@dataclass(frozen=True)
class ConfusionQuestion:
    """One question that separates two devices a photograph cannot.

    It asks about something the customer can see — a turntable, where the fan is
    mounted — rather than which category the appliance belongs to. Someone who
    could tell a microwave from an oven would not have needed the photograph
    diagnosed in the first place, so asking them to choose the label hands the
    hard part back to the person who came for help.
    """

    devices: List[str]
    question_vi: str
    if_yes: str
    if_no: str
    yes_words_vi: List[str] = field(default_factory=list)
    no_words_vi: List[str] = field(default_factory=list)


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
        self._aliases: Dict[str, List[str]] = {
            d["device_type"]: d.get("aliases_vi", []) for d in catalog["devices"]
        }
        self._confusable: Dict[str, List[str]] = {
            d["device_type"]: d.get("confusable_with", []) for d in catalog["devices"]
        }
        self._confusion: List[ConfusionQuestion] = [
            ConfusionQuestion(**q) for q in catalog.get("confusion_questions", [])
        ]
        self.version: str = str(kb.get("version", "unknown"))
        """Which edition of the fault table produced an answer.

        Every Vietnamese sentence and every price a customer sees comes from
        this file, so a complaint about wording or a quote is a complaint about
        one version of it. Wording changes without the code changing at all."""

        self._faults: List[Fault] = [Fault(**f) for f in kb["faults"]]
        self._policies: List[Policy] = [Policy(**p) for p in kb["policies"]]
        self._discriminators: List[Discriminator] = [
            Discriminator(**d) for d in kb.get("discriminators", [])
        ]
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

    def aliases_vi(self, device_type: str) -> List[str]:
        """What customers call this device, so a description can be believed."""
        return self._aliases.get(device_type, [])

    def confusion_question(self, device_type: str) -> Optional[ConfusionQuestion]:
        """The question that separates this device from the one it is confused with."""
        return next(
            (q for q in self._confusion if device_type in q.devices), None
        )

    def confusable_with(self, device_type: str) -> List[str]:
        """Classes a person looking at a photograph would also struggle with."""
        return self._confusable.get(device_type, [])

    def device_name_vi(self, device_type: str) -> Optional[str]:
        return self._device_names.get(device_type)

    def service_group(self, device_type: str) -> Optional[str]:
        return self._service_groups.get(device_type)

    def condition_name_vi(self, code: str) -> Optional[str]:
        return self._condition_names.get(code)

    def discriminators_for_device(self, device_type: Optional[str]) -> List[Discriminator]:
        """Questions for one device, or every question when none is known."""
        if device_type is None:
            return list(self._discriminators)
        return [d for d in self._discriminators if d.device_type == device_type]

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
