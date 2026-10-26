# app/services/pipeline/pricing.py
"""The price estimate a customer is shown (PO 26/10/2026).

    low   the price of the service itself, exactly as the booking form shows it:
          "Tham khảo 249.000đ" for a repair priced on site, "199.000đ – 449.000đ"
          for a fixed price per variant, or the variant's own price once known
    high  the service's top plus the parts the suspected fault usually needs,
          at FixHome's selling price

Before this the low end was the cheapest labour row plus the cheapest part, so
the assistant said 399.000đ for a low refrigerant while the form the customer
was sent to said 249.000đ for the same service.

Which parts a fault needs comes from `fault_pricing_map.json`. Each listed
part stands for its kind on that appliance: a failed compressor is priced on
every compressor sold for air conditioners (9.000 to 24.000 BTU, mono or
inverter), not only on the 12.000 BTU one, because the customer's machine
could be any of them. Parts listed for a fault are alternatives, and the
dearest one counts; a fault marked `together` needs one of each kind (a
refrigerant leak takes the gas and the filter drier). Codes under `exact` are
priced as themselves, for a kind that holds parts which do not stand in for
each other.

Booking is not affected: the form books the service, and the customer sees the
service's own price there. The estimate only says what the visit may come to.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.schemas.diagnosis import PriceEstimate
from app.services.pipeline import part_prices, service_catalog

_MAP = Path(__file__).resolve().parents[2] / "data" / "fault_pricing_map.json"


@lru_cache(maxsize=1)
def _map() -> Dict[str, dict]:
    return json.loads(_MAP.read_text(encoding="utf-8"))["map"]


@lru_cache(maxsize=None)
def part_groups(fault_code: str, device_type: Optional[str]) -> Tuple[Tuple[str, ...], ...]:
    """The fault's parts, each widened to every part of its kind for the appliance."""
    entry = _map().get(fault_code) or {}
    catalogue = part_prices.parts()
    groups: List[Tuple[str, ...]] = []
    seen_kinds = set()
    for code in entry.get("parts") or ():
        part = catalogue.get(code)
        if part is None:
            continue
        if not part.kind or part.kind in seen_kinds:
            if not part.kind:
                groups.append((code,))
            continue
        seen_kinds.add(part.kind)
        fits = {device_type} if device_type else set(part.device_types)
        siblings = tuple(
            sorted(
                other.code
                for other in catalogue.values()
                if other.kind == part.kind and fits & set(other.device_types)
            )
        )
        groups.append(siblings or (code,))
    # Priced as themselves: a kind that also holds parts which do not replace
    # each other (the indoor and the outdoor DC fan motors).
    groups += [(code,) for code in entry.get("exact") or () if code in catalogue]
    return tuple(groups)


def parts_ceiling(fault_code: str, device_type: Optional[str] = None) -> int:
    """The most the parts of this fault usually come to, at today's prices."""
    prices = part_prices.current()
    fallback = part_prices.reference()
    tops = []
    for group in part_groups(fault_code, device_type):
        known = [p for p in (prices.price(code) or fallback.get(code) for code in group) if p]
        if known:
            tops.append(max(known))
    if not tops:
        return 0
    return sum(tops) if (_map().get(fault_code) or {}).get("together") else max(tops)


def service_price(code: Optional[str], variant_code: Optional[str] = None) -> Optional[Tuple[int, int, bool]]:
    """(low, high, priced on site) for a service, as the booking form shows it."""
    if not code:
        return None
    live = service_catalog.current().services.get(code)
    if live is None or not live.base_price:
        return None
    if variant_code:
        fixed = dict(live.variant_prices).get(variant_code)
        if fixed:
            return fixed, fixed, False
    if live.price_kind == "fixed_range":
        return live.base_price, max(live.price_max or live.base_price, live.base_price), False
    return live.base_price, live.base_price, True


def estimate(
    service_code: Optional[str],
    fault_codes: Iterable[str] = (),
    device_type: Optional[str] = None,
    variant_code: Optional[str] = None,
) -> Optional[PriceEstimate]:
    """The service's price to its price plus the dearest fault's parts."""
    service = service_price(service_code, variant_code)
    if service is None:
        return None
    low, high, on_site = service
    parts = max((parts_ceiling(code, device_type) for code in fault_codes), default=0)
    return PriceEstimate(
        min=low,
        max=high + parts,
        requires_assessment=on_site or parts > 0,
        labour_min=low,
        labour_max=high,
        parts_max=parts,
    )
