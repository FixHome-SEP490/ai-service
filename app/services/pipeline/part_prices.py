# app/services/pipeline/part_prices.py
"""What each FixHome part sells for, read from Backend while the service runs.

PO 26/10/2026: the top of a price estimate is the service plus the parts the
fault usually needs, so the parts have to be priced the way a technician is
charged for them. Backend keeps one selling price per SKU (`fixhome_parts`) and
publishes it at the public `GET /parts/prices`; it is fetched every few minutes
like the service catalogue (see `service_catalog`).

What a part is (its kind and the appliances it fits) comes from
`app/data/parts_catalog.json`, which Backend's list does not carry. Its
`price` field is the snapshot of Backend's prices used before the first fetch,
written by `tools/sync_part_prices.py`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "parts_catalog.json"


@dataclass(frozen=True)
class Part:
    code: str
    name_vi: str
    kind: str
    """Lower-cased: the catalogue spells one kind two ways ("Filter Drier")."""
    device_types: Tuple[str, ...]


@dataclass
class PartPrices:
    prices: Dict[str, int] = field(default_factory=dict)
    loaded_at: float = 0.0

    @property
    def loaded(self) -> bool:
        return bool(self.prices)

    def price(self, code: str) -> Optional[int]:
        return self.prices.get(code)


@lru_cache(maxsize=1)
def parts() -> Dict[str, Part]:
    rows = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))["parts"]
    return {
        r["code"]: Part(
            code=r["code"],
            name_vi=r["name_vi"],
            kind=(r.get("kind") or "").strip().lower(),
            device_types=tuple(r.get("device_types") or ()),
        )
        for r in rows
    }


@lru_cache(maxsize=1)
def snapshot() -> PartPrices:
    rows = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))["parts"]
    return PartPrices({r["code"]: int(r["price"]) for r in rows if r.get("price")})


@lru_cache(maxsize=1)
def reference() -> Dict[str, int]:
    """The V3 table's top price, for a part Backend does not sell yet.

    26/10/2026: sockets, breakers, switches, bulbs and LED drivers (36 codes)
    are in the V3 table and in the faults' parts, but not in `fixhome_parts`.
    Leaving them out would price "ổ cắm chập cháy" as labour alone; their
    V3 figure stands in until Backend sells them, and then Backend's wins."""
    rows = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))["parts"]
    return {r["code"]: int(r["price_max"]) for r in rows if not r.get("price") and r.get("price_max")}


_LIVE = PartPrices()


def current() -> PartPrices:
    """Backend's prices as last fetched, else the snapshot."""
    return _LIVE if _LIVE.loaded else snapshot()


def install(prices: PartPrices) -> None:
    """Replace the snapshot. Tests use this; so does the refresher."""
    global _LIVE
    _LIVE = prices


def url_from_catalog(catalog_url: str) -> str:
    """`…/api/v1/services` -> `…/api/v1/parts/prices`, so one setting serves both."""
    base = (catalog_url or "").rstrip("/")
    if not base.endswith("/services"):
        return ""
    return base[: -len("/services")] + "/parts/prices"


def parse(payload) -> Dict[str, int]:
    body = payload.get("data", payload) if isinstance(payload, dict) else payload
    items: List[dict] = body.get("items", []) if isinstance(body, dict) else (body or [])
    out: Dict[str, int] = {}
    for row in items:
        sku = str(row.get("sku") or "").strip()
        try:
            price = int(round(float(row.get("price"))))
        except (TypeError, ValueError):
            continue
        if sku and price > 0:
            out[sku] = price
    return out


async def fetch(url: str, timeout: float) -> Dict[str, int]:
    import httpx

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return parse(response.json())


async def refresh_forever(url: str, every_seconds: float, timeout: float) -> None:
    """Keep the prices current. A failed fetch keeps the last good ones."""
    while True:
        try:
            prices = await fetch(url, timeout)
            if prices:
                install(PartPrices(prices, loaded_at=time.time()))
                logger.info("Giá linh kiện từ backend: %d mã", len(prices))
        except Exception as exc:  # the service must keep answering without it
            logger.warning("Không đọc được giá linh kiện từ backend: %s", exc)
        await asyncio.sleep(every_seconds)
