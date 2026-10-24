# app/services/pipeline/service_catalog.py
"""The services Backend sells today, read from Backend while the service runs.

`service_mapping.json` was generated once from Backend's seed file. Every
service added in the admin screen since then was invisible here: never
offered, never priced, and a customer asking about an appliance only the new
service covers was told it is not something FixHome does.

Nothing here is trained. The catalogue is fetched from Backend's public
`GET /services` every few minutes and laid over the static mapping:

    names and prices    taken from Backend, so the figure on screen is the
                        one the booking will charge
    switched off        a service Backend no longer sells is not offered
    new, same kind      a new service that names the fault's appliance and is
                        the same kind of work (repair, cleaning) joins the
                        faults it fits; a fault that only had the on-site
                        inspection gets the specific service in front of it
    new appliance       a service for an appliance the knowledge base does not
                        know ("Sửa máy hút mùi") is offered when the customer
                        names that appliance, instead of a refusal

Installation services are never attached to a fault: a fault is something
broken, and "Lắp quạt treo tường" is not the repair for any of them.

With no URL configured, or before the first fetch succeeds, the snapshot in
`app/data/service_catalog.json` stands in for Backend: the same catalogue V2/V3
codes, names, labour prices and which services are open, written by
`tools/sync_catalog_v3.py` from Backend's own source. The two never disagree
about what a code is; the live one only knows sooner when the admin opens or
closes a service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)


_SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "service_catalog.json"
_QUESTIONS = Path(__file__).resolve().parents[2] / "data" / "service_questions.json"


@dataclass(frozen=True)
class LiveService:
    code: str
    name_vi: str
    description_vi: str = ""
    base_price: Optional[int] = None
    """Lowest labour price: the cheapest variant of a fixed-price service, or
    the reference price of one priced on inspection."""
    price_max: Optional[int] = None
    kind: str = ""
    device_types: tuple = ()
    """The appliances it is for, from the snapshot. Empty for an appliance the
    knowledge base does not know (range hoods)."""


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in lowered if unicodedata.category(c) != "Mn").replace("đ", "d")


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


_CLEANING = ("ve sinh", "bao duong", "bao tri", "nap gas")
_INSTALL = ("lap dat", "lap ")
_GENERIC = frozenset(
    "sua thay lap dat ve sinh bao duong tri tien cong co ban khong bi hong loi va hoac "
    "cho cua mot cai chiec may nha khan cap gia dinh".split()
)
_HEADS = re.compile(
    r"\b(may|binh|noi|bep|lo|quat|tu|den|khoa|voi|o|ong|bon|chau|cua|am|tivi|ti vi)\s+[a-z0-9]+(?:\s+[a-z0-9]+)?"
)


def kind_of(text: str) -> str:
    """What sort of work a service or a fault's service is: clean, install or repair."""
    folded = " " + " ".join(_words(text)) + " "
    if any(f" {w}" in folded for w in _CLEANING) and not folded.strip().startswith("sua"):
        return "clean"
    if folded.strip().startswith(("lap dat", "lap ")):
        return "install"
    return "repair"


class LiveCatalog:
    """A snapshot of Backend's active services, and the rules for using it."""

    def __init__(
        self, services: Iterable[LiveService] = (), loaded_at: float = 0.0, enrich: bool = True
    ) -> None:
        known = snapshot().services if enrich else {}
        self.services: Dict[str, LiveService] = {}
        for service in services:
            # Backend's list carries no appliance and no kind; the snapshot has
            # both for every code it knows.
            seen = known.get(service.code)
            if seen is not None:
                service = replace(
                    service,
                    kind=service.kind or seen.kind,
                    device_types=service.device_types or seen.device_types,
                    base_price=service.base_price if service.base_price is not None else seen.base_price,
                    price_max=service.price_max if service.price_max is not None else seen.price_max,
                )
            self.services[service.code] = service
        self.loaded_at = loaded_at

    @property
    def loaded(self) -> bool:
        return bool(self.services)

    def refreshed(self, ref):
        """The same reference with Backend's current name and price, or None if
        Backend does not sell it."""
        live = self.services.get(ref.service_code)
        if live is None:
            return None
        return replace(
            ref,
            name_vi=live.name_vi or ref.name_vi,
            base_price=live.base_price if live.base_price is not None else ref.base_price,
            price_max=live.price_max if live.price_max is not None else ref.price_max,
            kind=live.kind or ref.kind,
            active=True,
        )

    def ref_for(self, code: str, ref=None):
        """The bookable reference for a code, or None if Backend does not sell it."""
        from app.services.pipeline.knowledge_base import ServiceRef

        if ref is not None:
            return self.refreshed(ref)
        live = self.services.get(code)
        if live is None:
            return None
        return ServiceRef(
            service_code=live.code,
            name_vi=live.name_vi,
            base_price=live.base_price,
            price_max=live.price_max,
            kind=live.kind or kind_of(live.name_vi),
        )

    def devices_of(self, service: LiveService, kb) -> Set[str]:
        """The appliances a service is for: the snapshot's list, else the one
        appliance its name (then its description) names."""
        if service.device_types:
            return set(service.device_types)
        from app.services.pipeline import device_hint

        for text in (service.name_vi, service.description_vi):
            if not text:
                continue
            devices = {h.device_type for h in device_hint.devices_named_in(text, kb)}
            if len(devices) == 1:
                return devices
            if devices:
                return set()
        return set()

    def services_for(self, fault, static_refs: List, kb, known_codes: Iterable[str]) -> List:
        """What to offer for a fault: the mapped service kept current, plus
        services added in the admin screen since the snapshot that fit it.

        When the mapped service is not open (microwave repair before Backend
        turns it on), the appliance's own repair stands in if that is open, and
        nothing otherwise: a button that books a service Backend refuses is
        worse than saying it is not offered yet."""
        current = [r for r in (self.refreshed(ref) for ref in static_refs) if r]
        wanted_kind = (static_refs[0].kind if static_refs else "") or "repair"
        known = set(known_codes)
        fault_words = set(_words(fault.name_vi + " " + " ".join(fault.symptoms_vi))) - _GENERIC
        name_words = {w for a in kb.aliases_vi(fault.device_type) for w in _words(a)}
        extra = []
        for service in self.services.values():
            if service.code in known or service.code in {r.service_code for r in current}:
                continue
            kind = service.kind or kind_of(service.name_vi)
            if kind != wanted_kind or wanted_kind == "install":
                continue
            if fault.device_type not in self.devices_of(service, kb):
                continue
            overlap = (set(_words(service.name_vi)) - _GENERIC - name_words) & fault_words
            # Cleaning is cleaning: the same appliance cleaned is the same job.
            # A repair has to be about this fault ("Thay vòi sen" is not the
            # cure for a weak tap), unless nothing else is bookable for it and
            # the new service is the appliance's general repair.
            general_repair = _words(service.name_vi)[:1] == ["sua"]
            if wanted_kind == "repair" and not overlap and (current or not general_repair):
                continue
            extra.append((len(overlap), service))
        extra.sort(key=lambda pair: (-pair[0], pair[1].code))
        # A short list to choose from, not the catalogue.
        added = [self.ref_for(s.code) for _, s in extra[:3]]
        if current:
            return current + added
        default = kb.default_service_code(fault.device_type)
        stand_in = self.ref_for(default) if default else None
        if stand_in is not None and all(r.service_code != stand_in.service_code for r in added):
            added.append(stand_in)
        return added

    def service_named_in(self, text: str, kb) -> Optional[LiveService]:
        """A service for an appliance the knowledge base does not know, named in
        the text: "máy hút mùi kêu to" and Backend sells "Sửa máy hút mùi".

        Of the services for that appliance, the cleaning one only when the
        customer asks for cleaning."""
        folded = " " + " ".join(_words(text)) + " "
        wants = "clean" if any(f" {w} " in folded for w in _CLEANING) else "repair"
        best: Optional[LiveService] = None
        best_key = (0, False)
        for service in self.services.values():
            kind = service.kind or kind_of(service.name_vi)
            if kind == "install" or self.devices_of(service, kb):
                continue
            for match in _HEADS.finditer(" ".join(_words(service.name_vi))):
                phrase = match.group(0)
                if len(phrase.split()) < 2 or f" {phrase} " not in folded:
                    continue
                key = (len(phrase), kind == wants)
                if key > best_key:
                    best, best_key = service, key
        return best


@lru_cache(maxsize=1)
def snapshot() -> LiveCatalog:
    """The open services as of the last `tools/sync_catalog_v3.py` run."""
    try:
        rows = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))["services"]
    except (OSError, ValueError, KeyError):
        return LiveCatalog(enrich=False)
    return LiveCatalog(
        (
            LiveService(
                code=r["code"],
                name_vi=r["name_vi"],
                base_price=r.get("price_min_vnd"),
                price_max=r.get("price_max_vnd"),
                kind=r.get("kind", ""),
                device_types=tuple(r.get("device_types") or ()),
            )
            for r in rows
            if r.get("active")
        ),
        enrich=False,
    )


@lru_cache(maxsize=1)
def _questions() -> Dict[str, List[dict]]:
    try:
        rows = json.loads(_QUESTIONS.read_text(encoding="utf-8"))["questions"]
    except (OSError, ValueError, KeyError):
        return {}
    out: Dict[str, List[dict]] = {}
    for row in rows:
        out.setdefault(row["service_code"], []).append(row)
    return out


def questions_for(code: Optional[str]) -> List[dict]:
    """What settles which fixed-price variant of a service applies, in order."""
    return list(_questions().get(code or "", []))


_CATALOG = LiveCatalog()


def current() -> LiveCatalog:
    """Backend's catalogue as last fetched, else the snapshot."""
    return _CATALOG if _CATALOG.loaded else snapshot()


def install(catalog: LiveCatalog) -> None:
    """Replace the snapshot. Tests use this; so does the refresher."""
    global _CATALOG
    _CATALOG = catalog


def _price(value) -> Optional[int]:
    try:
        price = int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None
    # Catalogue V2 leaves basePrice at 0 and puts the labour in priceSummary;
    # 0 is not a price anyone pays.
    return price if price else None


def parse(payload) -> List[LiveService]:
    """Backend's `GET /services` or `GET /categories` body, or its `data` list,
    into services."""
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(rows, dict):
        rows = rows.get("items") or rows.get("data") or []
    flat = []
    for row in rows or []:
        if isinstance(row.get("services"), list):
            if row.get("isActive") is False:
                continue
            flat.extend(row["services"])
        else:
            flat.append(row)
    out: List[LiveService] = []
    for row in flat:
        code = (row.get("code") or "").strip()
        if not code or row.get("isActive") is False or code == "DICH_VU_KHAC":
            continue
        summary = row.get("priceSummary") or {}
        low = _price(summary.get("minLaborVnd")) or _price(summary.get("suggestedLaborVnd"))
        out.append(
            LiveService(
                code=code,
                name_vi=(row.get("name") or "").strip(),
                description_vi=(row.get("description") or "").strip(),
                base_price=low or _price(row.get("basePrice")),
                price_max=_price(summary.get("maxLaborVnd")),
            )
        )
    return out


async def fetch(url: str, timeout: float) -> List[LiveService]:
    import httpx

    services: List[LiveService] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        page = 1
        while page <= 50:
            response = await client.get(url, params={"page": page, "limit": 100})
            response.raise_for_status()
            body = response.json()
            services += parse(body)
            meta = (body.get("meta") or {}) if isinstance(body, dict) else {}
            if page >= int(meta.get("totalPages") or 1):
                break
            page += 1
    return services


async def refresh_forever(url: str, every_seconds: float, timeout: float) -> None:
    """Keep the snapshot current. A failed fetch keeps the last good one."""
    while True:
        try:
            services = await fetch(url, timeout)
            if services:
                install(LiveCatalog(services, loaded_at=time.time()))
                logger.info("Danh mục dịch vụ từ backend: %d dịch vụ", len(services))
        except Exception as exc:  # the service must keep answering without it
            logger.warning("Không đọc được danh mục dịch vụ từ backend: %s", exc)
        await asyncio.sleep(every_seconds)
