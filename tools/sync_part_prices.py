"""Copy Backend's part prices into the snapshot, and reprice every fault with them.

    python tools/sync_part_prices.py --api https://api.fixhome.sbs
    python tools/sync_part_prices.py --file prices.json      # { "items": [{sku, name, price}] }

PO 26/10/2026: an estimate runs from the service's own price to that price
plus the parts the fault usually needs. The running service reads the prices
from Backend (`GET /api/v1/parts/prices`, see app/services/pipeline/part_prices.py);
this writes the same figures into `app/data/parts_catalog.json` (`price`) so a
service that cannot reach Backend, and the tests, use today's prices too.

It then rewrites each fault's `price_min`/`price_max` in
`fault_knowledge_base.json` and `parts_max` in `fault_pricing_map.json` with
`pricing.estimate`, so nothing that still reads those fields says a different
number from the answer. Parts Backend no longer sells lose their `price` and
stop counting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data"
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--api", help="Backend origin, e.g. https://api.fixhome.sbs")
    source.add_argument("--file", help="a saved GET /parts/prices body")
    args = parser.parse_args()

    from app.services.pipeline import part_prices

    if args.api:
        import httpx

        body = httpx.get(args.api.rstrip("/") + "/api/v1/parts/prices", timeout=30).json()
    else:
        body = json.loads(Path(args.file).read_text(encoding="utf-8"))
    live = part_prices.parse(body)
    if not live:
        raise SystemExit("Không đọc được giá nào.")

    catalogue_path = DATA / "parts_catalog.json"
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    changed = gone = 0
    for row in catalogue["parts"]:
        price = live.get(row["code"])
        if price is None:
            row.pop("price", None)
            gone += 1
            continue
        changed += row.get("price") != price
        row["price"] = price
    catalogue["_price_comment_vi"] = (
        "price: giá bán FixHome của mã (bảng fixhome_parts của backend), chép bằng tools/sync_part_prices.py; "
        "price_min/price_max là khoảng giá bảng V3 cũ, chỉ để tham khảo."
    )
    _write(catalogue_path, catalogue)

    part_prices.parts.cache_clear()
    part_prices.snapshot.cache_clear()
    part_prices.install(part_prices.PartPrices())
    from app.services.pipeline import pricing
    from app.services.pipeline.knowledge_base import get_knowledge_base

    pricing.part_groups.cache_clear()
    kb = get_knowledge_base()
    kb_path = DATA / "fault_knowledge_base.json"
    faults = json.loads(kb_path.read_text(encoding="utf-8"))
    map_path = DATA / "fault_pricing_map.json"
    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    repriced = 0
    for fault in faults["faults"]:
        code = fault["fault_code"]
        refs = kb.services_for_fault(code)
        estimate = pricing.estimate(refs[0].service_code if refs else None, [code], fault["device_type"])
        if estimate is None:
            continue
        if (fault["price_min"], fault["price_max"]) != (estimate.min, estimate.max):
            repriced += 1
        fault["price_min"], fault["price_max"] = estimate.min, estimate.max
        if code in mapping["map"]:
            mapping["map"][code]["parts_max"] = estimate.parts_max
            fault["part_codes"] = list(mapping["map"][code]["parts"])
    _write(kb_path, faults)
    _write(map_path, mapping)
    print(f"{len(live)} giá từ backend; {changed} mã đổi giá, {gone} mã backend chưa bán (dùng giá bảng V3); {repriced} lỗi tính lại giá")


if __name__ == "__main__":
    main()
