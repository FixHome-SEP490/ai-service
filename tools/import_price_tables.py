"""Turn the two supplied price tables into data the service can read.

Prices were estimated by hand until now and carried `price_reviewed: false` to
say so. These two tables replace the guessing with figures the team owns.

**Labour** comes from the fixed-price service catalogue in the business
document: twenty services with one price each, Admin-managed and snapshotted at
booking. That is the floor of any quote, because a technician travels and works
whether or not a part is replaced.

**Parts** come from the 500-item table, each with a range because the real price
depends on the model. That is what pushes the ceiling up.

    python tools/import_price_tables.py parts --from <file.md>
    python tools/import_price_tables.py services
    python tools/import_price_tables.py check

The output is JSON in app/data. Nothing here runs at request time.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "app" / "data"
PARTS_PATH = DATA_DIR / "parts_catalog.json"
SERVICES_PATH = DATA_DIR / "labour_catalog.json"

DEFAULT_PARTS_FILE = (
    REPO_ROOT / "docs" / "reference" / "FIXHOME-BANG-LINH-KIEN-VA-VAT-TU-791-ITEMS-v4.0.md"
)

# Section heading in the parts table -> device types it covers. One section can
# serve several classes: "Đồ điện gia dụng" holds stove, kettle and fan parts.
SECTION_DEVICES: Dict[str, List[str]] = {
    "Điều hòa / Máy lạnh": ["air_conditioner"],
    "Máy giặt": ["washing_machine"],
    "TV / Smart TV": ["television"],
    "Tủ lạnh": ["refrigerator"],
    "Tủ lạnh — linh kiện bổ sung chi tiết": ["refrigerator"],
    "Bồn rửa / Chậu rửa": ["sink"],
    "Vòi nước / Sen vòi": ["faucet"],
    "Bồn cầu / Thiết bị vệ sinh": ["toilet"],
    "Ống nước & phụ kiện PVC/PPR": ["water_pipe"],
    "Lò vi sóng — linh kiện chi tiết": ["microwave_oven"],
    "Lò nướng — linh kiện chi tiết": ["oven"],
    "Bếp gas — linh kiện chi tiết": ["gas_stove"],
    "Ấm đun / Ấm siêu tốc": ["kettle"],
    # Mixed: induction hob, fan, water heater, rice cooker, water purifier,
    # plus generic electrical consumables. Only the classes this project models
    # are listed; parts for the rest simply go unused. The section is a coarse
    # filter — precision comes from the fault-to-part mapping, not from here.
    "Đồ điện gia dụng": [
        "electric_fan",
        "ceiling_fan",
        "water_heater",
        "light_bulb",
        "power_outlet",
    ],
}

_PRICE = re.compile(r"([\d.]+)\s*đ\s*[–\-]\s*([\d.]+)\s*đ")
_SINGLE_PRICE = re.compile(r"([\d.]+)\s*đ")


def _to_dong(text: str) -> Optional[int]:
    """"1.800.000" -> 1800000. Dots are thousands separators here, not decimals."""
    digits = text.replace(".", "").strip()
    return int(digits) if digits.isdigit() else None


def _parse_price(cell: str) -> Optional[tuple[int, int]]:
    ranged = _PRICE.search(cell)
    if ranged:
        low, high = _to_dong(ranged.group(1)), _to_dong(ranged.group(2))
        if low is not None and high is not None and low <= high:
            return low, high
        return None
    single = _SINGLE_PRICE.search(cell)
    if single:
        value = _to_dong(single.group(1))
        if value is not None:
            return value, value
    return None


def cmd_parts(args: argparse.Namespace) -> None:
    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Not found: {source}")

    section = ""
    items: List[dict] = []
    skipped = 0

    for line in source.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            continue
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 9 or cells[0] in ("Mã", ""):
            continue

        price = _parse_price(cells[7])
        if price is None:
            skipped += 1
            continue

        items.append(
            {
                "code": cells[0],
                "name_vi": cells[1],
                "group_vi": cells[2],
                "kind": cells[4],
                "price_min": price[0],
                "price_max": price[1],
                "unit_vi": cells[8],
                "section_vi": section,
                "device_types": SECTION_DEVICES.get(section, []),
            }
        )

    unmapped = sorted({i["section_vi"] for i in items if not i["device_types"]})
    if unmapped:
        raise SystemExit(
            "These sections are not mapped to device types, so their parts could\n"
            "never be priced against a fault:\n  " + "\n  ".join(unmapped)
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PARTS_PATH.write_text(
        json.dumps(
            {
                "version": source.stem,
                "_comment_vi": (
                    "Bang linh kien do team cung cap. Gia la khoang tham khao vi phu "
                    "thuoc model. Day la phan day tran gia len; san la tien cong tho "
                    "trong labour_catalog.json."
                ),
                "parts": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    by_section = Counter(i["section_vi"] for i in items)
    print(f"parts: {len(items)} written to {PARTS_PATH.name}, {skipped} without a price")
    for name, count in by_section.most_common():
        print(f"  {name:<24}{count:>5}")

    lows = [i["price_min"] for i in items]
    highs = [i["price_max"] for i in items]
    print(f"\nprice range across all parts: {min(lows):,}d to {max(highs):,}d")


# Transcribed from section 8.3.1 of the business document. Kept here rather than
# parsed, because that table is prose in a Word export and would need a fragile
# reader for twenty rows that change rarely.
LABOUR: List[dict] = [
    ("AC_CLEAN_WALL_SMALL", "Vệ sinh điều hòa treo tường 1–1.5 HP", "air_conditioner", 180000, "Máy"),
    ("AC_CLEAN_WALL_LARGE", "Vệ sinh điều hòa treo tường 2–2.5 HP", "air_conditioner", 220000, "Máy"),
    ("AC_CLEAN_CASSETTE", "Vệ sinh điều hòa âm trần", "air_conditioner", 500000, "Máy"),
    ("WM_CLEAN_TOP_SMALL", "Vệ sinh máy giặt cửa trên ≤ 9kg", "washing_machine", 350000, "Máy"),
    ("WM_CLEAN_TOP_LARGE", "Vệ sinh máy giặt cửa trên > 9kg", "washing_machine", 450000, "Máy"),
    ("WM_CLEAN_FRONT_SMALL", "Vệ sinh máy giặt cửa ngang ≤ 9kg", "washing_machine", 550000, "Máy"),
    ("WM_CLEAN_FRONT_LARGE", "Vệ sinh máy giặt cửa ngang > 9kg", "washing_machine", 650000, "Máy"),
    ("WH_CLEAN", "Vệ sinh, bảo dưỡng bình nóng lạnh", "water_heater", 250000, "Bình"),
    ("ELEC_SWITCH_REPLACE", "Thay công tắc điện, tiền công", "light_bulb", 100000, "Cái"),
    ("ELEC_OUTLET_REPLACE", "Thay ổ cắm điện, tiền công", "power_outlet", 100000, "Cái"),
    ("ELEC_CEILING_LIGHT", "Lắp đèn trần cơ bản, tiền công", "light_bulb", 120000, "Cái"),
    ("ELEC_WALL_FAN", "Lắp quạt treo tường, tiền công", "electric_fan", 150000, "Cái"),
    ("ELEC_CEILING_FAN", "Lắp quạt trần cơ bản, tiền công", "ceiling_fan", 250000, "Cái"),
    ("TV_MOUNT", "Lắp TV lên giá treo có sẵn", "television", 100000, "TV"),
    ("PLUMB_FAUCET_REPLACE", "Thay vòi nước, tiền công", "faucet", 120000, "Cái"),
    ("PLUMB_SHOWER_REPLACE", "Thay vòi sen, tiền công", "faucet", 150000, "Bộ"),
    ("PLUMB_SIPHON_REPLACE", "Thay siphon, chống rò lavabo, tiền công", "sink", 150000, "Bộ"),
    ("DIAGNOSE_ONSITE", "Kiểm tra, chẩn đoán thiết bị tại nhà", None, 100000, "Lần"),
]


def cmd_services(args: argparse.Namespace) -> None:
    services = [
        {
            "service_code": code,
            "name_vi": name,
            "device_type": device,
            "price": price,
            "unit_vi": unit,
        }
        for code, name, device, price, unit in LABOUR
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SERVICES_PATH.write_text(
        json.dumps(
            {
                "version": "SEP490 8.3.1",
                "_comment_vi": (
                    "Gia cong tho co dinh, Admin quan ly, snapshot khi Booking. Day la "
                    "san cua moi khoang gia: tho van di lai va lam viec du co thay linh "
                    "kien hay khong. DIAGNOSE_ONSITE la muc toi thieu khi chua ro benh."
                ),
                "services": services,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"labour: {len(services)} services written to {SERVICES_PATH.name}")
    print(f"  cheapest {min(s['price'] for s in services):,}d")
    print(f"  dearest  {max(s['price'] for s in services):,}d")


def cmd_check(args: argparse.Namespace) -> None:
    """Which device types have parts, labour, both or neither."""
    if not PARTS_PATH.exists() or not SERVICES_PATH.exists():
        raise SystemExit("Run the parts and services commands first.")

    catalog = json.loads(
        (DATA_DIR / "device_catalog.json").read_text(encoding="utf-8")
    )
    parts = json.loads(PARTS_PATH.read_text(encoding="utf-8"))["parts"]
    labour = json.loads(SERVICES_PATH.read_text(encoding="utf-8"))["services"]

    part_counts: Counter = Counter()
    for item in parts:
        for device in item["device_types"]:
            part_counts[device] += 1
    labour_counts = Counter(s["device_type"] for s in labour if s["device_type"])

    print(f"{'device':<20}{'parts':>7}{'labour':>8}")
    gaps = []
    for device in catalog["devices"]:
        name = device["device_type"]
        p, lab = part_counts.get(name, 0), labour_counts.get(name, 0)
        print(f"{name:<20}{p:>7}{lab:>8}")
        if p == 0 or lab == 0:
            gaps.append((name, p, lab))

    if gaps:
        print("\nWithout both, a quote for these falls back to the on-site")
        print("inspection fee alone, which is honest but not very useful:")
        for name, p, lab in gaps:
            missing = []
            if not p:
                missing.append("parts")
            if not lab:
                missing.append("labour")
            print(f"  {name:<20} missing {' and '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    parts = sub.add_parser("parts", help="parse the supplied parts table")
    parts.add_argument("--from", dest="source", default=str(DEFAULT_PARTS_FILE))

    sub.add_parser("services", help="write the fixed-price labour catalogue")
    sub.add_parser("check", help="which devices have parts, labour, both or neither")

    args = parser.parse_args()
    {"parts": cmd_parts, "services": cmd_services, "check": cmd_check}[args.command](args)


if __name__ == "__main__":
    main()
