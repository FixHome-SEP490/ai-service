"""Bring the AI's service, price and parts tables in line with Backend's catalogue.

    python tools/sync_catalog_v3.py --v3 ../../FIXHOME_CATALOG_V3_NHAP_20261019.json
    python tools/sync_catalog_v3.py --v3 <file> --live https://<backend>/api/v1/categories

Backend replaced the old service list (SUA_DIEU_HOA, KIEM_TRA_CHAN_DOAN_THIET_BI,
VE_SINH_DIEU_HOA_1HP...) with catalogue V2/V3 codes (AC-01 "Sửa điều hòa",
AC-02 "Vệ sinh điều hòa" with variants by mounting and horsepower...). Every
code the assistant recommended stopped resolving to a bookable service, and the
prices it quoted were the old ones.

Nothing is typed in again by hand. Read from Backend's own sources:

    src/database/catalog-v2/catalog-v2-review.ts             services, categories, rollout phase
    src/database/catalog-v2/catalog-v2-approved-price-tiers.ts fixed variants, inspection references

and from the V3 working file the team agreed on 19/10/2026, which maps each of
the 134 faults to a service and estimates labour plus likely parts. A service
is offered when its phase is M1 or M2 (that is what `seed:catalog-v3` turns
on); `--live` replaces that with exactly the codes Backend serves now.

Writes: app/data/service_catalog.json, service_mapping.json, labour_catalog.json,
parts_catalog.json (V3 additions and fixes), fault_pricing_map.json,
service_questions.json, and in fault_knowledge_base.json each fault's price
range, labour code, likely parts and bookable variants; device_catalog.json
gets each appliance's default repair service.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data"
BACKEND = ROOT.parent / "backend" / "src" / "database" / "catalog-v2"
REMOVED = {"PU-01", "PU-02"}  # deleted from the database with the pump category

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def kind_of(name: str) -> str:
    low = name.lower()
    if low.startswith(("vệ sinh", "thay lõi")):
        return "clean"
    if low.startswith(("lắp", "tháo")):
        return "install"
    return "repair"


def read_backend(backend: Path) -> dict:
    review = (backend / "catalog-v2-review.ts").read_text(encoding="utf-8")
    tiers = (backend / "catalog-v2-approved-price-tiers.ts").read_text(encoding="utf-8")
    categories = dict(re.findall(r"\['(CAT_[A-Z_]+)',\s*'([^']+)'\]", review))
    services = {}
    for code, cat, name, ref, mode, phase in re.findall(
        r"item\('([A-Z]{2}-\d{2})','(CAT_[A-Z_]+)','([^']+)','([^']*)','([A-Z_]+)','([A-Z0-9]+)'\)", review
    ):
        services[code] = {
            "code": code, "name_vi": name, "category_code": cat, "category_vi": categories.get(cat, ""),
            "phase": phase, "pricing": "fixed" if mode == "FIXED_TIER_PENDING" else "inspection",
            "kind": kind_of(name), "reference_text_vi": ref, "variants": [], "type_refs": [],
            "reference_vnd": None,
        }
    for svc, var, cond, price in re.findall(
        r"serviceCode: '([A-Z]{2}-\d{2})', variantCode: '([A-Z]{2}-\d{2}-\d{2})', conditionVi: \"([^\"]+)\", laborPriceVnd: (\d+)", tiers
    ):
        if svc in services:
            services[svc]["variants"].append({"code": var, "condition_vi": cond, "price_vnd": int(price)})
    for svc, price in re.findall(r"serviceCode: '([A-Z]{2}-\d{2})', suggestedLaborVnd: (\d+)", tiers):
        if svc in services:
            services[svc]["reference_vnd"] = int(price)
    for svc, body in re.findall(r"'([A-Z]{2}-\d{2})': \[(.*?)\],\n", tiers):
        if svc in services:
            services[svc]["type_refs"] = [
                {"condition_vi": c, "price_vnd": int(p)}
                for c, p in re.findall(r"conditionVi: '([^']+)', laborVnd: (\d+)", body)
            ]
    return services


def live_codes(url_or_file: str) -> set:
    if url_or_file.startswith("http"):
        import httpx

        body = httpx.get(url_or_file, timeout=30).json()
    else:
        body = json.loads(Path(url_or_file).read_text(encoding="utf-8"))
    data = body.get("data", body)
    return {s["code"] for c in data for s in (c.get("services") or []) if s.get("isActive", True)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3", required=True)
    parser.add_argument("--backend", default=str(BACKEND))
    parser.add_argument("--live", default="")
    args = parser.parse_args()

    v3 = json.loads(Path(args.v3).read_text(encoding="utf-8"))
    services = read_backend(Path(args.backend))
    active = {c for c, s in services.items() if s["phase"] in ("M1", "M2")} - REMOVED
    if args.live:
        active = live_codes(args.live)
    devices_of: dict = {}
    for d in v3["ai_devices"]:
        for code in d["services"]:
            devices_of.setdefault(code, []).append(d["device_type"])
    for code, s in services.items():
        s["active"] = code in active
        s["device_types"] = devices_of.get(code, [])
        prices = [v["price_vnd"] for v in s["variants"]] + [r["price_vnd"] for r in s["type_refs"]]
        if s["reference_vnd"]:
            prices.append(s["reference_vnd"])
        s["price_min_vnd"] = min(prices) if prices else None
        s["price_max_vnd"] = max(prices) if prices else None
    missing = sorted(active - set(services))
    if missing:
        sys.exit(f"Backend sells codes this tool cannot read: {missing}")

    now = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    (DATA / "service_catalog.json").write_text(json.dumps({
        "version": now,
        "_comment_vi": "Danh mục dịch vụ của backend (catalog V2/V3), sinh bởi tools/sync_catalog_v3.py từ mã nguồn backend. active = backend đang mở. Giá là tiền công, chưa gồm linh kiện.",
        "services": [services[c] for c in sorted(services) if c not in REMOVED],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # Each appliance's own repair service, and whether anything is bookable for it now.
    default_service = {}
    for d in v3["ai_devices"]:
        repair = d["default_repair"]
        if repair not in active:
            repair = next((c for c in d["services"] if c in active and services[c]["kind"] == "repair"), repair)
        default_service[d["device_type"]] = repair

    def ref(code: str) -> dict:
        s = services[code]
        return {
            "service_code": code, "name_vi": s["name_vi"], "base_price": s["price_min_vnd"],
            "active": s["active"], "kind": s["kind"],
            "variant_codes": [v["code"] for v in s["variants"]],
        }

    mappings = []
    for f in v3["ai_fault_map"]:
        code = f["service_code"]
        refs = [ref(code)]
        alt = default_service.get(f["device_type"])
        if code not in active and alt and alt != code and alt in active:
            refs.append(ref(alt))
        mappings.append({"fault_code": f["fault_code"], "services": refs})
    (DATA / "service_mapping.json").write_text(json.dumps({
        "version": now,
        "_comment_vi": "Mỗi lỗi -> dịch vụ backend (mã catalog V2/V3), sinh bởi tools/sync_catalog_v3.py từ bảng V3 đội đã chốt 19/10/2026. active=false là dịch vụ backend chưa mở: không gợi ý cho tới khi backend bật (đọc danh mục sống bằng BACKEND_CATALOG_URL).",
        "mappings": mappings,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    labour_rows = []
    for code in sorted(services):
        s = services[code]
        if not s["active"]:
            continue
        device = (s["device_types"] or [""])[0]
        if s["variants"]:
            for v in s["variants"]:
                labour_rows.append({"service_code": v["code"], "name_vi": f"{s['name_vi']}: {v['condition_vi']}", "device_type": device, "device_types": s["device_types"], "price": v["price_vnd"], "unit_vi": "máy"})
        elif s["type_refs"]:
            for i, r in enumerate(s["type_refs"], 1):
                labour_rows.append({"service_code": f"{code}-T{i}", "name_vi": f"{s['name_vi']}: {r['condition_vi']} (công tham khảo)", "device_type": device, "device_types": s["device_types"], "price": r["price_vnd"], "unit_vi": "lần"})
        elif s["reference_vnd"]:
            labour_rows.append({"service_code": code, "name_vi": f"{s['name_vi']} (công tham khảo)", "device_type": device, "device_types": s["device_types"], "price": s["reference_vnd"], "unit_vi": "lần"})
    (DATA / "labour_catalog.json").write_text(json.dumps({
        "version": now,
        "_comment_vi": "Tiền công theo danh mục backend (catalog V2/V3), sinh bởi tools/sync_catalog_v3.py. Dịch vụ giá cố định ghi theo từng biến thể; dịch vụ sửa ghi công tham khảo theo loại máy, thợ chốt khi tới. Chưa gồm linh kiện.",
        "services": labour_rows,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    parts = json.loads((DATA / "parts_catalog.json").read_text(encoding="utf-8"))
    by_code = {p["code"]: p for p in parts["parts"]}
    for p in v3["parts_new"]:
        if p["code"] not in by_code:
            row = {k: p[k] for k in ("code", "name_vi", "group_vi", "kind", "price_min", "price_max", "unit_vi", "section_vi", "device_types")}
            parts["parts"].append(row)
            by_code[p["code"]] = row
    for fix in v3["parts_price_fixes"]:
        if fix["code"] in by_code:
            by_code[fix["code"]]["price_min"], by_code[fix["code"]]["price_max"] = fix["new_min"], fix["new_max"]
    for tag in v3["parts_retag"]:
        if tag["code"] in by_code:
            by_code[tag["code"]]["device_types"] = tag["new"]
    (DATA / "parts_catalog.json").write_text(json.dumps(parts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kb_path = DATA / "fault_knowledge_base.json"
    kb = json.loads(kb_path.read_text(encoding="utf-8"))
    by_fault = {f["fault_code"]: f for f in v3["ai_fault_map"]}
    for fault in kb["faults"]:
        f = by_fault.get(fault["fault_code"])
        if not f:
            continue
        fault["labour_code"] = f["service_code"]
        fault["part_codes"] = list(f.get("likely_parts") or [])
        # Only variants Backend books by code; inspection references are not.
        bookable = {v["code"] for v in services[f["service_code"]]["variants"]}
        fault["candidate_variants"] = [v for v in f.get("candidate_variants") or [] if v in bookable]
        fault["price_min"] = int(f["estimate_min_vnd"])
        fault["price_max"] = 0 if fault.get("requires_assessment") else int(f["estimate_max_vnd"])
    kb_path.write_text(json.dumps(kb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (DATA / "fault_pricing_map.json").write_text(json.dumps({
        "version": now,
        "_comment_vi": "Mỗi lỗi -> dịch vụ backend (tiền công S) và linh kiện hay thay (P), theo bảng V3 đội chốt 19/10/2026. Giá sàn = S thấp nhất + P thấp nhất, giá trần = S cao nhất + P cao nhất. Sinh bởi tools/sync_catalog_v3.py.",
        "map": {
            f["fault_code"]: {
                "labour": f["service_code"], "parts": list(f.get("likely_parts") or []),
                "labour_min": int(f["s_min_vnd"]), "labour_max": int(f["s_max_vnd"]),
                "parts_min": int(f["p_min_vnd"]), "parts_max": int(f["p_max_vnd"]),
                "note_vi": f.get("note") or f.get("no_part_reason") or "",
            }
            for f in v3["ai_fault_map"]
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    questions = [
        {
            "service_code": q["service_code"], "attribute": q["attribute"], "question_vi": q["question_vi"],
            "options": [{"value": o["value"], "label_vi": o["label"], "variants": o.get("variants", [])} for o in q["options"]],
        }
        for q in v3["ai_attribute_questions"]
        if q["service_code"] in services and services[q["service_code"]]["variants"]
    ]
    (DATA / "service_questions.json").write_text(json.dumps({
        "version": now,
        "_comment_vi": "Câu hỏi để chọn đúng biến thể giá cố định (loại máy, công suất...), theo bảng V3. Chỉ dịch vụ có biến thể backend đặt theo mã. Sinh bởi tools/sync_catalog_v3.py.",
        "questions": questions,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    catalog_path = DATA / "device_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for d in catalog["devices"]:
        if d["device_type"] in default_service:
            d["default_service"] = default_service[d["device_type"]]
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    off = sorted({m["services"][0]["service_code"] for m in mappings if not m["services"][0]["active"]})
    print(f"{len(services) - len(REMOVED & set(services))} dịch vụ, {len(active)} đang mở; {len(mappings)} lỗi; {len(labour_rows)} dòng tiền công; {len(parts['parts'])} linh kiện")
    print("lỗi trỏ dịch vụ chưa mở:", off)


if __name__ == "__main__":
    main()
