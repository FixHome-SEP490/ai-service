# tools/map_services.py
"""Map every fault code to the Backend service a customer would actually book.

Backend owns the catalogue. Until this ran, ``app/data/service_mapping.json``
was empty and every recommendation fell back to the labour table — which names
the work correctly but with our code, not Backend's, so the mobile app could
not turn it into a booking.

Service names are read out of ``seed-catalog.ts`` rather than retyped here, so
the text a customer sees is the text the catalogue holds.

Faults with no matching service fall to ``KIEM_TRA_CHAN_DOAN_THIET_BI`` — the
PO's rule: a technician goes out, looks, and quotes on the spot.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT.parent / "backend" / "src" / "database" / "seeds" / "seed-catalog.ts"
OUT = ROOT / "app" / "data" / "service_mapping.json"
KB = ROOT / "app" / "data" / "fault_knowledge_base.json"

FALLBACK = "KIEM_TRA_CHAN_DOAN_THIET_BI"

# By fault, where the fault names work the catalogue sells outright. Anything
# absent falls back. Cleaning and repair are deliberately kept apart: they are
# different services at different prices, and quoting the repair to someone who
# asked for a clean is a complaint waiting to happen.
BY_FAULT = {
    # Điều hòa — bẩn và tắc nước là vệ sinh, còn lại là sửa.
    "AC_DIRTY_FILTER": "VE_SINH_DIEU_HOA_1HP",
    "AC_DRAIN_BLOCKED": "VE_SINH_DIEU_HOA_1HP",
    "AC_ICING": "SUA_DIEU_HOA",
    "AC_LOW_REFRIGERANT": "SUA_DIEU_HOA",
    "AC_COMPRESSOR_FAULT": "SUA_DIEU_HOA",
    "AC_PCB_FAULT": "SUA_DIEU_HOA",
    "AC_INDOOR_FAN_MOTOR": "SUA_DIEU_HOA",
    "AC_OUTDOOR_FAN_MOTOR": "SUA_DIEU_HOA",
    "AC_CAPACITOR": "SUA_DIEU_HOA",
    "AC_NOISY_INDOOR": "SUA_DIEU_HOA",
    "AC_SMELL_BURNT": "SUA_DIEU_HOA",
    # Tủ lạnh — catalog chỉ có một dòng sửa chung.
    "FRIDGE_LOW_GAS": "SUA_TU_LANH",
    "FRIDGE_DEFROST_FAULT": "SUA_TU_LANH",
    "FRIDGE_COMPRESSOR": "SUA_TU_LANH",
    "FRIDGE_DOOR_GASKET": "SUA_TU_LANH",
    "FRIDGE_FAN_FAULT": "SUA_TU_LANH",
    "FRIDGE_DRAIN_BLOCKED": "SUA_TU_LANH",
    "FRIDGE_LIGHT_FAULT": "SUA_TU_LANH",
    "FRIDGE_NOISY": "SUA_TU_LANH",
    # Máy giặt — mốc là vệ sinh lồng, còn lại là sửa.
    "WM_SMELL_MOLD": "VE_SINH_MAY_GIAT_CUA_TREN_LE9",
    "WM_DRAIN_PUMP": "SUA_MAY_GIAT",
    "WM_NO_SPIN": "SUA_MAY_GIAT",
    "WM_NO_WATER_INLET": "SUA_MAY_GIAT",
    "WM_BEARING_NOISE": "SUA_MAY_GIAT",
    "WM_PCB_FAULT": "SUA_MAY_GIAT",
    "WM_DOOR_SEAL_LEAK": "SUA_MAY_GIAT",
    "WM_DOOR_LOCK": "SUA_MAY_GIAT",
    "WM_MOTOR_FAULT": "SUA_MAY_GIAT",
    "WM_OVERFLOW": "SUA_MAY_GIAT",
    # Quạt trần treo lỏng là việc lắp lại, không phải sửa máy.
    "CEILFAN_MOUNT_LOOSE": "LAP_QUAT_TRAN_CO_BAN",
    # Ổ cắm và aptomat.
    "OUTLET_SHORT_CIRCUIT": "SUA_CHAP_DIEN",
    "OUTLET_TRIPS_BREAKER": "SUA_CHAP_DIEN",
    "OUTLET_NO_POWER": "SUA_CHAP_DIEN",
    "OUTLET_OVERLOAD": "SUA_CHAP_DIEN",
    "OUTLET_LOOSE_CONTACT": "THAY_O_CAM_DIEN",
    "OUTLET_BROKEN_FACE": "THAY_O_CAM_DIEN",
    # Đèn và công tắc.
    "LIGHT_BULB_DEAD": "LAP_DEN_TRAN_CO_BAN",
    "LIGHT_DIM": "LAP_DEN_TRAN_CO_BAN",
    "LIGHT_FLICKERING": "LAP_DEN_TRAN_CO_BAN",
    "LIGHT_FIXTURE_LEAK": "LAP_DEN_TRAN_CO_BAN",
    "LIGHT_SWITCH_FAULT": "THAY_CONG_TAC_DIEN",
    # Vòi và lavabo.
    "FAUCET_DRIP": "THAY_VOI_NUOC",
    "FAUCET_CARTRIDGE": "THAY_VOI_NUOC",
    "FAUCET_BASE_LEAK": "THAY_VOI_NUOC",
    "SINK_TRAP_LEAK": "THAY_SIPHON_LAVABO",
    "SINK_DRAIN_CORRODED": "THAY_SIPHON_LAVABO",
    # Đường ống rò và vỡ.
    "PIPE_JOINT_LEAK": "SUA_RO_RI_NUOC",
    "PIPE_BURST": "SUA_RO_RI_NUOC",
    "TOILET_BASE_LEAK": "SUA_RO_RI_NUOC",
    # Bình nóng lạnh đóng cặn là bảo dưỡng.
    "WH_SCALE_BUILDUP": "VE_SINH_BINH_NONG_LANH",
    # Bếp từ, máy rửa bát, máy sấy, máy lọc nước và khoá thông minh — năm thiết
    # bị Backend có dịch vụ riêng, nên không cái nào rơi về kiểm tra chung.
    "HOB_NO_PAN_DETECT": "SUA_BEP_TU",
    "HOB_ERROR_CODE": "SUA_BEP_TU",
    "HOB_FAN_NOISY": "SUA_BEP_TU",
    "HOB_TOUCH_FAULT": "SUA_BEP_TU",
    "HOB_NO_POWER": "SUA_BEP_TU",
    "HOB_GLASS_CRACKED": "SUA_BEP_TU",
    "DW_NOT_CLEAN": "SUA_MAY_RUA_CHEN",
    "DW_NOT_DRAINING": "SUA_MAY_RUA_CHEN",
    "DW_NO_WATER": "SUA_MAY_RUA_CHEN",
    "DW_DOOR_LEAK": "SUA_MAY_RUA_CHEN",
    "DW_NO_POWER": "SUA_MAY_RUA_CHEN",
    "DRYER_NOT_HEATING": "KIEM_TRA_CHAN_DOAN_THIET_BI",
    "DRYER_LINT_CLOGGED": "VE_SINH_MAY_SAY",
    "DRYER_NOISY": "KIEM_TRA_CHAN_DOAN_THIET_BI",
    "DRYER_NOT_SPINNING": "KIEM_TRA_CHAN_DOAN_THIET_BI",
    "DRYER_NO_POWER": "KIEM_TRA_CHAN_DOAN_THIET_BI",
    "PURIFIER_NO_WATER": "LAP_MAY_LOC_NUOC",
    "PURIFIER_LEAK": "LAP_MAY_LOC_NUOC",
    "PURIFIER_FILTER_DUE": "LAP_MAY_LOC_NUOC",
    "PURIFIER_PUMP_RUNS_ON": "LAP_MAY_LOC_NUOC",
    "PURIFIER_NO_POWER": "LAP_MAY_LOC_NUOC",
    "LOCK_FINGERPRINT_FAIL": "SUA_KHOA_THONG_MINH",
    "LOCK_LOW_BATTERY": "SUA_KHOA_THONG_MINH",
    "LOCK_MOTOR_FAULT": "SUA_KHOA_THONG_MINH",
    "LOCK_LOCKED_OUT": "MO_KHOA_KHAN_CAP",
    "LOCK_CARD_FAULT": "SUA_KHOA_THONG_MINH",
}


def read_catalog() -> dict:
    """service_code -> (name, basePrice), straight out of the seed file.

    Split rather than matched with a lookahead: the last service in the file
    has no next "code:" to look ahead to, and a bounded one silently dropped
    MO_KHOA_KHAN_CAP — the emergency lock-opening service, which is exactly
    the one somebody locked out of their house needs.
    """
    text = SEED.read_text(encoding="utf-8")
    catalog = {}
    for chunk in text.split("code: '")[1:]:
        code, _, tail = chunk.partition("'")
        if not re.fullmatch(r"[A-Z0-9_]+", code):
            continue
        name = re.search(r"name: '([^']+)'", tail)
        price = re.search(r"basePrice: (\d+)", tail)
        if name is None:
            continue
        catalog[code] = (
            name.group(1),
            int(price.group(1)) if price else None,
        )
    return catalog

def main() -> None:
    catalog = read_catalog()
    if FALLBACK not in catalog:
        raise SystemExit(f"{FALLBACK} khong co trong seed-catalog.ts")

    faults = json.loads(KB.read_text(encoding="utf-8"))["faults"]
    mappings = []
    specific = 0
    for fault in faults:
        code = BY_FAULT.get(fault["fault_code"], FALLBACK)
        if code not in catalog:
            raise SystemExit(f"{code} khong co trong seed-catalog.ts")
        if code != FALLBACK:
            specific += 1
        mappings.append(
            {
                "fault_code": fault["fault_code"],
                "services": [
                    {
                        "service_code": code,
                        "name_vi": catalog[code][0],
                        "base_price": catalog[code][1],
                    }
                ],
            }
        )

    OUT.write_text(
        json.dumps(
            {
                "version": "2026-09-17",
                "_comment_vi": (
                    "Sinh boi tools/map_services.py tu backend seed-catalog.ts. "
                    "Loi khong co dich vu rieng thi roi ve KIEM_TRA_CHAN_DOAN_THIET_BI."
                ),
                "mappings": mappings,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(mappings)} loi: {specific} dich vu rieng, {len(mappings)-specific} roi ve kiem tra")


if __name__ == "__main__":
    main()
