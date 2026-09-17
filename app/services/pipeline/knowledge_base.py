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

    needs_technician_review: bool = False
    """A technician has not yet read this entry.

    Separate from price_reviewed, which is only about the numbers. This flag
    covers the whole entry — the symptoms, what to do first, how urgent it is —
    and it is set on everything written without a tradesman in the room.
    Nothing in the service reads it; it is there so the backlog is a query
    rather than a spreadsheet somebody maintains by hand."""


@dataclass(frozen=True)
class ServiceRef:
    """A Backend service a fault maps to. Absent until Backend agrees a catalog."""

    service_code: str
    name_vi: str
    base_price: Optional[int] = None
    """What Backend charges for it. Quoting the fault's floor instead named a
    price from our own labour table that had nothing to do with the service the
    customer was about to book."""


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


@dataclass(frozen=True)
class PriceRow:
    """One line from the labour or parts table, as something retrieval can find.

    The two tables were built for computing a fault's range offline and were
    never visible to the chat surface, so "dây điện thay bên mình tính giá sao"
    came back as out of scope while the answer sat in a file the service had
    already loaded."""

    code: str
    name_vi: str
    kind: str
    """"labour" or "part"."""

    price_min: int
    price_max: int
    unit_vi: str
    device_types: List[str] = field(default_factory=list)

    def as_text_vi(self) -> str:
        if self.price_min == self.price_max:
            money = f"{self.price_min:,}đ".replace(",", ".")
        else:
            money = (
                f"{self.price_min:,}đ tới {self.price_max:,}đ".replace(",", ".")
            )
        what = "Tiền công" if self.kind == "labour" else "Giá linh kiện"
        return f"{what} — {self.name_vi}: {money} một {self.unit_vi.lower()}."


class KnowledgeBase:
    def __init__(
        self,
        catalog: dict,
        kb: dict,
        mapping: dict,
        labour: Optional[dict] = None,
        parts: Optional[dict] = None,
    ) -> None:
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
        self._prices: List[PriceRow] = []
        for row in (labour or {}).get("services", []):
            self._prices.append(
                PriceRow(
                    code=row["service_code"],
                    name_vi=row["name_vi"],
                    kind="labour",
                    price_min=row["price"],
                    price_max=row["price"],
                    unit_vi=row.get("unit_vi", "lần"),
                    device_types=[row["device_type"]] if row.get("device_type") else [],
                )
            )
        for row in (parts or {}).get("parts", []):
            self._prices.append(
                PriceRow(
                    code=row["code"],
                    name_vi=row["name_vi"],
                    kind="part",
                    price_min=row["price_min"],
                    price_max=row["price_max"],
                    unit_vi=row.get("unit_vi", "cái"),
                    device_types=row.get("device_types", []),
                )
            )

        self._services: Dict[str, List[ServiceRef]] = {}
        for entry in mapping.get("mappings", []):
            self._services[entry["fault_code"]] = [
                ServiceRef(
                    service_code=s["service_code"],
                    name_vi=s["name_vi"],
                    base_price=s.get("base_price"),
                )
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

    FALLBACK_SERVICE_CODE = "KIEM_TRA_CHAN_DOAN_THIET_BI"
    """What a customer books when the fault is not settled.

    The PO's rule: a fault with no service of its own falls to an on-site
    inspection. It is also the right offer while a question is still open —
    somebody comes and looks is literally what is being proposed."""

    def fallback_service(self) -> Optional[ServiceRef]:
        """The inspection service, as Backend spells it.

        Not the labour row of the same name. Backend's code is the one the
        mobile app can turn into a booking; ours prices it.
        """
        for refs in self._services.values():
            for ref in refs:
                if ref.service_code == self.FALLBACK_SERVICE_CODE:
                    return ref
        return None

    def services_for_fault(self, fault_code: str) -> List[ServiceRef]:
        """Empty while Backend has not supplied a catalog. Not an error."""
        return list(self._services.get(fault_code, []))

    def labour_row(self, code: Optional[str]) -> Optional[PriceRow]:
        """The labour service a fault maps to, by code."""
        if not code:
            return None
        return next(
            (r for r in self._prices if r.kind == "labour" and r.code == code), None
        )

    @property
    def price_rows(self) -> List[PriceRow]:
        """Every labour and part line, for answering a question about cost."""
        return list(self._prices)

    def all_service_groups(self) -> List[str]:
        return sorted(set(self._service_groups.values()))


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    catalog = json.loads((DATA_DIR / "device_catalog.json").read_text(encoding="utf-8"))
    kb = json.loads((DATA_DIR / "fault_knowledge_base.json").read_text(encoding="utf-8"))
    mapping = json.loads((DATA_DIR / "service_mapping.json").read_text(encoding="utf-8"))
    labour = json.loads((DATA_DIR / "labour_catalog.json").read_text(encoding="utf-8"))
    parts = json.loads((DATA_DIR / "parts_catalog.json").read_text(encoding="utf-8"))
    return KnowledgeBase(
        catalog=catalog, kb=kb, mapping=mapping, labour=labour, parts=parts
    )
