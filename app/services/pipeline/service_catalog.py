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

With no URL configured, or before the first fetch succeeds, everything behaves
exactly as the static mapping says.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveService:
    code: str
    name_vi: str
    description_vi: str = ""
    base_price: Optional[int] = None


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

    def __init__(self, services: Iterable[LiveService] = (), loaded_at: float = 0.0) -> None:
        self.services: Dict[str, LiveService] = {s.code: s for s in services}
        self.loaded_at = loaded_at

    @property
    def loaded(self) -> bool:
        return bool(self.services)

    def refreshed(self, ref, fallback_code: str):
        """The same reference with Backend's current name and price, or None if
        Backend no longer sells it."""
        live = self.services.get(ref.service_code)
        if live is None:
            return None
        return replace(
            ref,
            name_vi=live.name_vi or ref.name_vi,
            base_price=live.base_price if live.base_price is not None else ref.base_price,
        )

    def device_of(self, service: LiveService, kb) -> Optional[str]:
        """The one appliance a service names, by its name first, then its description."""
        from app.services.pipeline import device_hint

        for text in (service.name_vi, service.description_vi):
            if not text:
                continue
            devices = {h.device_type for h in device_hint.devices_named_in(text, kb)}
            if len(devices) == 1:
                return devices.pop()
            if devices:
                return None
        return None

    def services_for(self, fault, static_refs: List, kb, known_codes: Iterable[str], fallback_code: str) -> List:
        """What to offer for a fault: the static choice kept current, plus new
        services that fit it."""
        from app.services.pipeline.knowledge_base import ServiceRef

        current = [r for r in (self.refreshed(ref, fallback_code) for ref in static_refs) if r]
        specific = [r for r in current if r.service_code != fallback_code]
        wanted_kind = kind_of(specific[0].name_vi) if specific else "repair"
        known = set(known_codes) | {fallback_code}
        fault_words = set(_words(fault.name_vi + " " + " ".join(fault.symptoms_vi))) - _GENERIC
        name_words = {w for a in kb.aliases_vi(fault.device_type) for w in _words(a)}
        extra = []
        for service in self.services.values():
            if service.code in known or service.code in {r.service_code for r in current}:
                continue
            if kind_of(service.name_vi) != wanted_kind or wanted_kind == "install":
                continue
            if self.device_of(service, kb) != fault.device_type:
                continue
            overlap = (set(_words(service.name_vi)) - _GENERIC - name_words) & fault_words
            # Cleaning is cleaning: the same appliance cleaned is the same job
            # in another size or model ("treo tường 2-2.5 HP", "âm trần",
            # "cửa ngang > 9kg"), so they are offered side by side.
            # A repair has to be about this fault ("Thay vòi sen" is not the
            # cure for a weak tap), unless the fault so far could only be
            # booked as an inspection and the new service is the appliance's
            # general repair ("Sửa lò vi sóng").
            general_repair = _words(service.name_vi)[:1] == ["sua"]
            if wanted_kind == "repair" and not overlap and (specific or not general_repair):
                continue
            extra.append((len(overlap), service))
        extra.sort(key=lambda pair: (-pair[0], pair[1].code))
        # A short list to choose from, not the catalogue.
        extra = extra[:3]
        added = [
            ServiceRef(service_code=s.code, name_vi=s.name_vi, base_price=s.base_price)
            for _, s in extra
        ]
        if not specific:
            fallback = [r for r in current if r.service_code == fallback_code]
            return added + fallback
        return specific + added

    def service_named_in(self, text: str, kb) -> Optional[LiveService]:
        """A service for an appliance the knowledge base does not know, named in
        the text: "máy hút mùi kêu to" and Backend sells "Sửa máy hút mùi"."""
        folded = " " + " ".join(_words(text)) + " "
        best: Optional[LiveService] = None
        best_len = 0
        for service in self.services.values():
            if kind_of(service.name_vi) == "install" or self.device_of(service, kb) is not None:
                continue
            for match in _HEADS.finditer(" ".join(_words(service.name_vi))):
                phrase = match.group(0)
                if len(phrase.split()) >= 2 and f" {phrase} " in folded and len(phrase) > best_len:
                    best, best_len = service, len(phrase)
        return best


_CATALOG = LiveCatalog()


def current() -> LiveCatalog:
    return _CATALOG


def install(catalog: LiveCatalog) -> None:
    """Replace the snapshot. Tests use this; so does the refresher."""
    global _CATALOG
    _CATALOG = catalog


def parse(payload) -> List[LiveService]:
    """Backend's `GET /services` body, or its `data` list, into services."""
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(rows, dict):
        rows = rows.get("items") or rows.get("data") or []
    out: List[LiveService] = []
    for row in rows or []:
        code = (row.get("code") or "").strip()
        if not code or row.get("isActive") is False or code == "DICH_VU_KHAC":
            continue
        price = row.get("basePrice")
        try:
            price = int(float(price)) if price is not None else None
        except (TypeError, ValueError):
            price = None
        out.append(
            LiveService(
                code=code,
                name_vi=(row.get("name") or "").strip(),
                description_vi=(row.get("description") or "").strip(),
                base_price=price,
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
