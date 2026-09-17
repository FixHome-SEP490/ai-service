"""Map each fault to the Backend service a customer would book for it.

The mapping sat empty for weeks with a note saying it was waiting for Backend
to agree a catalogue. Backend had agreed one: twenty-nine services with codes,
names and prices, seeded in `backend/src/database/seeds/seed-catalog.ts`.

The rule, confirmed by the project owner: a fault with no service of its own
falls back to "Kiểm tra/chẩn đoán thiết bị tại nhà", which is a real service
at a real price and is what a technician does when nobody knows yet.

    python tools/map_services.py --check     # fail if the mapping is behind
    python tools/map_services.py --write

Regenerate whenever the seed changes. The output is committed so the service
does not read the Backend repository at runtime — it cannot, they deploy apart.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline.knowledge_base import get_knowledge_base  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
SEED = REPO.parent / "backend" / "src" / "database" / "seeds" / "seed-catalog.ts"
MAPPING = REPO / "app" / "data" / "service_mapping.json"

FALLBACK = "KIEM_TRA_CHAN_DOAN_THIET_BI"
"""What to book when the catalogue has nothing for this fault.

Not a placeholder: it is a real service at a real price, and it is what a
technician actually does when the fault is not yet settled. Six of the
seventeen appliances have no repair service of their own — a gas stove, a
kettle, a microwave, an oven, a toilet, a broken television — so this is the
honest answer for them rather than an admission of a gap.
"""

# Which service a fault leads to, most specific first. A fault matches the
# first rule whose device matches and whose predicate is true.
RULES: List[tuple] = [
    # Cleaning jobs are their own service and cost less than a repair, so a
    # dirty filter must not be booked as "sửa điều hòa".
    ("air_conditioner", lambda f: "DIRTY" in f or "DRAIN" in f, "VE_SINH_DIEU_HOA_1HP"),
    ("air_conditioner", lambda f: True, "SUA_DIEU_HOA"),
    ("refrigerator", lambda f: True, "SUA_TU_LANH"),
    ("washing_machine", lambda f: "SMELL" in f, "VE_SINH_MAY_GIAT_CUA_NGANG_LE9"),
    ("washing_machine", lambda f: True, "SUA_MAY_GIAT"),
    ("water_heater", lambda f: "SCALE" in f, "VE_SINH_BINH_NONG_LANH"),
    # A leaking or tripping water heater is electrical work near water, and the
    # catalogue has no service for it. The inspection is the honest booking.
    ("water_heater", lambda f: True, FALLBACK),
    ("power_outlet", lambda f: "SHORT" in f or "TRIPS" in f, "SUA_CHAP_DIEN"),
    ("power_outlet", lambda f: True, "THAY_O_CAM_DIEN"),
    ("light_bulb", lambda f: "SWITCH" in f, "THAY_CONG_TAC_DIEN"),
    ("light_bulb", lambda f: True, "LAP_DEN_TRAN_CO_BAN"),
    ("ceiling_fan", lambda f: True, "LAP_QUAT_TRAN_CO_BAN"),
    ("electric_fan", lambda f: True, "LAP_QUAT_TREO_TUONG"),
    ("faucet", lambda f: True, "THAY_VOI_NUOC"),
    ("sink", lambda f: "TRAP" in f or "DRAIN" in f, "THAY_SIPHON_LAVABO"),
    ("water_pipe", lambda f: True, "SUA_RO_RI_NUOC"),
]


def services_in_seed() -> Dict[str, str]:
    """Code to name, read from the Backend seed rather than retyped."""
    if not SEED.exists():
        raise SystemExit(f"Không thấy seed của Backend tại {SEED}")
    text = SEED.read_text(encoding="utf-8")
    found: Dict[str, str] = {}
    for block in re.finditer(r"\{[^{}]*?code:\s*'([A-Z0-9_]+)'[^{}]*?\}", text, re.S):
        name = re.search(r"name:\s*'([^']+)'", block.group(0))
        if name:
            found[block.group(1)] = name.group(1)
    return found


def service_for(fault_code: str, device_type: str) -> str:
    for device, predicate, service in RULES:
        if device == device_type and predicate(fault_code):
            return service
    return FALLBACK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    catalogue = services_in_seed()
    kb = get_knowledge_base()
    mappings = []
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            code = service_for(fault.fault_code, device)
            if code not in catalogue:
                raise SystemExit(f"{code} không có trong seed của Backend")
            mappings.append(
                {
                    "fault_code": fault.fault_code,
                    "services": [{"service_code": code, "name_vi": catalogue[code]}],
                }
            )

    generic = sum(1 for m in mappings if m["services"][0]["service_code"] == FALLBACK)
    print(f"{len(catalogue)} dịch vụ trong seed, {len(mappings)} bệnh đã ánh xạ")
    print(f"  {len(mappings) - generic} bệnh có dịch vụ riêng")
    print(f"  {generic} bệnh rơi về {FALLBACK}")

    current = json.loads(MAPPING.read_text(encoding="utf-8"))
    if current.get("mappings") == mappings:
        print("service_mapping.json đã khớp")
        return 0
    if args.check:
        print("chạy: python tools/map_services.py --write")
        return 1
    if args.write:
        current["mappings"] = mappings
        MAPPING.write_text(
            json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"đã ghi {MAPPING.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
