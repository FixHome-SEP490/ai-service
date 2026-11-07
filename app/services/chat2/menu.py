"""What the chat model may choose from, for one appliance.

The model is never asked to recall a fault or a service. It is shown the
faults and the open services of the appliance in front of it, at most twelve
faults and four services, and picks codes from that list; the JSON schema it
decodes under enumerates exactly those codes, so an invented code cannot be
produced at all. Names, prices and safety steps shown to the customer are
looked up here afterwards, never taken from the model's text.

The services are Backend's open ones as last fetched (`catalog`), so a
service the admin opens, closes or reprices reaches the chat within minutes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.services.chat2 import catalog as live

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Faults whose first words to the customer must be a safety step.
URGENT = "HIGH"


@dataclass(frozen=True)
class FaultItem:
    code: str
    name_vi: str
    symptoms_vi: Tuple[str, ...]
    urgency: str
    actions_vi: Tuple[str, ...]
    service_code: Optional[str]


@dataclass(frozen=True)
class ServiceItem:
    code: str
    name_vi: str
    kind: str  # repair | clean | install
    price_min: Optional[int]
    price_max: Optional[int]


@dataclass(frozen=True)
class Question:
    text_vi: str
    if_yes: Tuple[str, ...]
    if_no: Tuple[str, ...]


@dataclass
class DeviceMenu:
    device_type: str
    name_vi: str
    faults: List[FaultItem] = field(default_factory=list)
    services: List[ServiceItem] = field(default_factory=list)
    questions: List[Question] = field(default_factory=list)

    def fault(self, code: Optional[str]) -> Optional[FaultItem]:
        return next((f for f in self.faults if f.code == code), None)

    def service(self, code: Optional[str]) -> Optional[ServiceItem]:
        return next((s for s in self.services if s.code == code), None)

    @property
    def repair_service(self) -> Optional[ServiceItem]:
        return next((s for s in self.services if s.kind == "repair"), None)


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


# Appliances Backend sells services for that the device catalogue does not
# list, so nothing could book them: the catalogue's KT-02 and KT-03 carry no
# device type at all. Named here, matched to their services by code.
EXTRA_DEVICES: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "range_hood": ("Máy hút mùi", ("KT-02", "KT-03")),
}


@lru_cache(maxsize=1)
def devices() -> Dict[str, str]:
    """device_type -> Vietnamese name: the detector's appliances, then the text-only ones."""
    names = {d["device_type"]: d["name_vi"] for d in _load("device_catalog.json")["devices"]}
    names.update({k: v[0] for k, v in EXTRA_DEVICES.items()})
    return names


@lru_cache(maxsize=1)
def not_aliases() -> Dict[str, Tuple[str, ...]]:
    """Names that hold an alias of the appliance yet are another thing: "máy sấy tóc" for the tumble dryer."""
    return {d["device_type"]: tuple(d.get("not_aliases_vi") or ()) for d in _load("device_catalog.json")["devices"]}


@lru_cache(maxsize=1)
def device_aliases() -> Dict[str, Tuple[str, ...]]:
    return {d["device_type"]: tuple(d.get("aliases_vi") or ()) for d in _load("device_catalog.json")["devices"]}


@lru_cache(maxsize=None)
def confusable(device_type: str) -> Tuple[str, ...]:
    """Appliances the detector mistakes this one for (device_catalog.json)."""
    for d in _load("device_catalog.json")["devices"]:
        if d["device_type"] == device_type:
            return tuple(d.get("confusable_with") or ())
    return ()


@lru_cache(maxsize=1)
def fault_cards() -> Dict[str, dict]:
    """fault_code -> short card (tools/build_fault_cards.py); empty when the file is absent."""
    path = DATA_DIR / "fault_cards.json"
    return json.loads(path.read_text(encoding="utf-8"))["cards"] if path.exists() else {}


def all_names() -> Dict[str, Tuple[str, ...]]:
    """Every name an appliance goes by: its own, then its aliases."""
    aliases = device_aliases()
    return {d: (name, *aliases.get(d, ())) for d, name in devices().items()}


# Menus of the catalogue they were built from; a new fetch builds new ones.
_MENUS: Tuple[object, Dict[str, Optional[DeviceMenu]]] = (None, {})


def menu_for(device_type: str) -> Optional[DeviceMenu]:
    global _MENUS
    catalog = live.current()
    if _MENUS[0] is not catalog:
        _MENUS = (catalog, {})
    menus = _MENUS[1]
    if device_type not in menus:
        menus[device_type] = _build(device_type, catalog)
    return menus[device_type]


@lru_cache(maxsize=1)
def _mappings() -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """fault_code -> its services in order of preference (service_mapping.json)."""
    return tuple(
        (row["fault_code"], tuple(s["service_code"] for s in row.get("services") or () if s.get("active")))
        for row in _load("service_mapping.json")["mappings"]
    )


@lru_cache(maxsize=1)
def _kb() -> dict:
    return _load("fault_knowledge_base.json")


def _build(device_type: str, catalog) -> Optional[DeviceMenu]:
    names = devices()
    if device_type not in names:
        return None
    services = [
        ServiceItem(
            code=s.code,
            name_vi=s.name_vi,
            kind=s.kind or live.kind_of(s.name_vi),
            price_min=s.base_price,
            price_max=s.price_max,
        )
        for s in live.services_for(device_type, catalog, all_names(), not_aliases(), EXTRA_DEVICES.get(device_type, ("", ()))[1])
    ]
    open_codes = {s.code for s in services}
    mapped: Dict[str, str] = {}
    for fault_code, codes in _mappings():
        for code in codes:
            if code in open_codes:
                mapped.setdefault(fault_code, code)
                break
    known = {code for _, codes in _mappings() for code in codes}
    added = [catalog.services[s.code] for s in services if s.code not in known]
    device_words = {w for n in all_names().get(device_type, ()) for w in live.fold(n).split()}
    kb = _kb()
    general = next((s.code for s in services if s.kind == "repair"), None)
    for f in kb["faults"]:
        # Only a fault that books the appliance's general repair is open to a
        # more specific one; a mapping to a specific service stands.
        if f["device_type"] != device_type or mapped.get(f["fault_code"], general) != general:
            continue
        # A repair the admin added since the mapping was written, for this fault.
        fit = next((s for s in added if live.fits_fault(s, f["name_vi"], device_words)), None)
        if fit is not None:
            mapped[f["fault_code"]] = fit.code
    faults = [
        FaultItem(
            code=f["fault_code"],
            name_vi=f["name_vi"],
            symptoms_vi=tuple(f.get("symptoms_vi") or ()),
            urgency=f.get("urgency") or "MEDIUM",
            actions_vi=tuple(f.get("suggested_actions_vi") or ()),
            service_code=mapped.get(f["fault_code"]),
        )
        for f in kb["faults"]
        if f["device_type"] == device_type
    ]
    questions = [
        Question(q["question_vi"], tuple(q.get("favours_if_yes") or ()), tuple(q.get("favours_if_no") or ()))
        for q in kb.get("discriminators") or []
        if q["device_type"] == device_type
    ]
    menu = DeviceMenu(device_type, names[device_type], faults, services, questions)
    repair = menu.repair_service
    if repair:
        menu.faults = [f if f.service_code else _with_service(f, repair.code) for f in menu.faults]
    return menu


def _with_service(fault: FaultItem, code: str) -> FaultItem:
    return FaultItem(fault.code, fault.name_vi, fault.symptoms_vi, fault.urgency, fault.actions_vi, code)


def price_text(service: ServiceItem) -> str:
    lo, hi = service.price_min, service.price_max
    if not lo:
        return ""
    if hi and hi != lo:
        return f"{lo:,}đ – {hi:,}đ".replace(",", ".")
    return f"{lo:,}đ".replace(",", ".")
