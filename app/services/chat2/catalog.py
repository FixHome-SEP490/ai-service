"""The services the chat may offer: Backend's catalogue as last fetched.

Until 07/11 the chat read `app/data/service_catalog.json`, a file written by
`tools/sync_catalog_v3.py`. A service the admin opened, closed or repriced
reached the chat only when someone ran that script and shipped a new image.
`service_catalog` already follows Backend's `GET /services` every few
minutes (`BACKEND_CATALOG_URL`) for the old pipeline and for prices; the chat
now reads the same thing:

    open services       the menu of each appliance, so the model can only
                        pick what Backend sells right now
    a new service       joins the appliance its name or description names
                        ("Vệ sinh quạt trần" -> ceiling fan), and a new repair
                        for one fault joins that fault when it names it
    a new appliance     ("Sửa máy hút bụi") is offered when the customer names
                        it, instead of "FixHome chưa nhận"
    the price tables    and the list of services the answer tier quotes are
                        written from it, never typed

With no URL configured, or before the first fetch, the snapshot file stands in,
so tests and a laptop behave exactly as before.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.services.pipeline import service_catalog
from app.services.pipeline.service_catalog import LiveCatalog, LiveService, kind_of

NOT_TAKEN_VI = "FixHome không nhận sửa laptop, máy tính, điện thoại, máy in, xe máy, ô tô."


def current() -> LiveCatalog:
    return service_catalog.current()


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower()).replace("đ", "d")
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).split()) + " "


def _order(catalog: LiveCatalog) -> List[LiveService]:
    """The snapshot's order first (it decides which repair is an appliance's
    general one), then services added since, by code."""
    known = list(service_catalog.snapshot().services)
    rank = {code: i for i, code in enumerate(known)}
    return sorted(catalog.services.values(), key=lambda s: (rank.get(s.code, len(rank)), s.code))


def named_device(text: str, names: Dict[str, Iterable[str]], not_names: Dict[str, Iterable[str]]) -> Optional[str]:
    """The one appliance a service's text names by its longest name, else None.

    "Vệ sinh máy hút mùi" names only the range hood; "Sửa bếp" names no one
    appliance and is not guessed."""
    folded = fold(text)
    best: Tuple[int, Set[str]] = (0, set())
    for device, words in names.items():
        if any(fold(n).strip() and fold(n) in folded for n in not_names.get(device, ())):
            continue
        for name in words:
            f = fold(name)
            if len(f.strip()) < 3 or f not in folded:
                continue
            if len(f) > best[0]:
                best = (len(f), {device})
            elif len(f) == best[0]:
                best[1].add(device)
    return next(iter(best[1])) if len(best[1]) == 1 else None


def devices_of(service: LiveService, names: Dict[str, Iterable[str]], not_names: Dict[str, Iterable[str]]) -> Set[str]:
    if service.device_types:
        return set(service.device_types)
    for text in (service.name_vi, service.description_vi):
        device = named_device(text, names, not_names) if text else None
        if device:
            return {device}
    return set()


def services_for(device_type: str, catalog: LiveCatalog, names, not_names, extra_codes: Iterable[str] = ()) -> List[LiveService]:
    extra = set(extra_codes)
    return [s for s in _order(catalog) if s.code in extra or device_type in devices_of(s, names, not_names)]


# Words a service name shares with every fault of its kind: they say nothing
# about which fault it is for.
_PLAIN = frozenset(
    "sua thay lap dat ve sinh bao duong tri tien cong co ban khong bi hong loi va hoac cho cua mot cai chiec may "
    "nha khan cap gia dinh su co thiet bi".split()
)


def fits_fault(service: LiveService, fault_name: str, device_words: Set[str]) -> bool:
    """A repair added in the admin screen that names this fault: "Thay gioăng
    cửa tủ lạnh" fits "Hở gioăng cửa"; "Sửa tủ lạnh" fits every fault and so
    names none. The fault's name, not its symptoms: a symptom list mentions
    the gasket under low gas too."""
    if (service.kind or kind_of(service.name_vi)) != "repair":
        return False
    words = set(fold(service.name_vi).split()) - _PLAIN - device_words
    return bool(words & (set(fold(fault_name).split()) - _PLAIN - device_words))


_HEADS = re.compile(
    r"\b(may|binh|noi|bep|lo|quat|tu|den|khoa|voi|o|ong|bon|chau|cua|am|tivi|ti vi|robot|rem|cong)\s+[a-z0-9]+(?:\s+[a-z0-9]+)?"
)


def unknown_appliance_service(text: str, catalog: LiveCatalog, names, not_names) -> Optional[LiveService]:
    """A service for an appliance the chat has no menu for, named in the text:
    Backend sells "Sửa máy hút bụi" and the customer writes "máy hút bụi nhà
    em không hút". Cleaning only when cleaning is asked for."""
    folded = fold(text)
    cleaning = any(f" {w} " in folded for w in ("ve sinh", "bao duong", "lam sach", "bao tri"))
    best: Optional[LiveService] = None
    best_key = (0, False)
    for service in _order(catalog):
        kind = service.kind or kind_of(service.name_vi)
        if kind == "install" or devices_of(service, names, not_names):
            continue
        for match in _HEADS.finditer(fold(service.name_vi)):
            phrase = match.group(0).strip()
            if len(phrase.split()) < 2 or f" {phrase} " not in folded:
                continue
            key = (len(phrase), (kind == "clean") == cleaning)
            if key > best_key:
                best, best_key = service, key
    return best


def _money(service: LiveService) -> str:
    low, high = service.base_price, service.price_max
    if not low:
        return "báo giá sau khi kiểm tra"
    text = f"{low:,}đ" + (f" đến {high:,}đ" if high and high != low else "")
    return text.replace(",", ".")


def _price_kind(service: LiveService) -> str:
    if service.price_kind == "fixed_range":
        return "giá cố định theo loại máy"
    return "giá tham khảo, thợ báo giá chính xác sau khi kiểm tra"


def passages(catalog: LiveCatalog, device_names: Dict[str, str], names, not_names) -> List[Dict[str, str]]:
    """The two kinds of passage written from the catalogue: what FixHome takes
    on, and each appliance's services with prices."""
    by_category: Dict[str, List[str]] = defaultdict(list)
    by_device: Dict[str, List[str]] = defaultdict(list)
    for s in _order(catalog):
        by_category[s.category_vi or "Dịch vụ khác"].append(s.name_vi)
        devices = devices_of(s, names, not_names)
        for device in (d for d in device_names if d in devices):
            by_device[device].append(f"- {s.name_vi}: {_money(s)} ({_price_kind(s)})")
    out = [{
        "id": "catalog:services",
        "scope": "platform",
        "doc_vi": "Danh mục dịch vụ FixHome",
        "section_vi": "FixHome đang nhận những dịch vụ gì",
        "text_vi": "FixHome đang nhận các dịch vụ sau, theo nhóm:\n"
        + "\n".join(f"- {c}: {', '.join(v)}" for c, v in by_category.items())
        + f"\n\n{NOT_TAKEN_VI}",
    }]
    for device in device_names:
        lines = by_device.get(device)
        if not lines:
            continue
        name = device_names[device].lower()
        out.append({
            "id": f"catalog:{device}",
            "scope": f"device:{device}",
            "doc_vi": "Bảng giá dịch vụ",
            "section_vi": f"Giá dịch vụ {name}",
            "text_vi": f"Dịch vụ {name} trên FixHome, giá là tiền công, chưa gồm linh kiện:\n" + "\n".join(lines),
        })
    return out
