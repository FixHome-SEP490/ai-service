"""Several appliances in one message, against a running service.

    python tools/eval_multi_device.py --url http://host:port --trials 60 --out multi.json
    python tools/eval_multi_device.py --url ... --data <folder with one sub-folder per appliance>

Each trial picks two or three photographs of different appliances from
datasets/collected/<device>/, sends them with a message about the first one,
and checks what came back: which appliances devices[] names and in which
photograph, the service each is offered, and how long it took. Photographs are
shrunk to 1024 px on the long edge, as the web does before sending.
"""

import argparse
import base64
import io
import json
import random
import statistics
import time
from pathlib import Path

import httpx
from PIL import Image

DATA = Path(__file__).resolve().parents[1] / "datasets" / "collected"
SAY = {
    "air_conditioner": "máy lạnh nhà em không mát", "washing_machine": "máy giặt không vắt được",
    "refrigerator": "tủ lạnh không lạnh", "electric_fan": "quạt không quay", "ceiling_fan": "quạt trần kêu to",
    "water_heater": "bình nóng lạnh không nóng", "gas_stove": "bếp gas không lên lửa",
    "induction_hob": "bếp từ không nóng", "television": "tivi không lên hình", "microwave_oven": "lò vi sóng không nóng",
    "toilet": "bồn cầu xả yếu", "sink": "lavabo bị tắc", "faucet": "vòi nước bị rỉ", "kettle": "ấm siêu tốc không sôi",
    "light_bulb": "bóng đèn không sáng", "power_outlet": "ổ cắm bị lỏng", "water_purifier": "máy lọc nước ra nước chậm",
    "oven": "lò nướng không nóng", "dishwasher": "máy rửa bát không sạch", "clothes_dryer": "máy sấy không nóng",
    "smart_lock": "khóa cửa không mở được", "water_pipe": "ống nước bị rò",
}


def photo(path: Path) -> str:
    image = Image.open(path).convert("RGB")
    image.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--seed", type=int, default=12)
    parser.add_argument("--out", default="multi.json")
    parser.add_argument("--data", default=str(DATA))
    args = parser.parse_args()
    rng = random.Random(args.seed)
    data = Path(args.data)
    devices = sorted(d.name for d in data.iterdir() if d.is_dir() and d.name in SAY and any(d.iterdir()))
    rows = []
    with httpx.Client(timeout=120) as client:
        for trial in range(args.trials):
            n = 3 if trial % 2 == 0 else 2
            chosen = rng.sample(devices, n)
            files = [rng.choice(sorted((data / d).glob("*.jp*g"))) for d in chosen]
            body = {"description": SAY[chosen[0]], "images": [photo(f) for f in files], "includeTrace": True}
            start = time.time()
            try:
                reply = client.post(f"{args.url}/api/v1/diagnosis/analyze", json=body).json()
            except Exception as exc:  # recorded, not fatal
                rows.append({"chosen": chosen, "error": str(exc)})
                continue
            ms = int((time.time() - start) * 1000)
            seen = next((s.get("detail", {}).get("seen", []) for s in reply.get("trace", []) if s.get("name") == "detector"), [])
            got = {d["deviceType"]: d.get("imageIndex") for d in reply.get("devices", [])}
            if not got and reply.get("device"):
                got = {reply["device"]["deviceType"]: 0}
            per_image = [any(s["image"] == i and s["device"] == d for s in seen) for i, d in enumerate(chosen)]
            rows.append({
                "chosen": chosen, "files": [f.name for f in files], "ms": ms, "status": reply.get("status"),
                "seen": seen, "devices": got, "per_image": per_image,
                "lead_ok": bool(reply.get("devices")) and reply["devices"][0]["deviceType"] == chosen[0]
                or (not reply.get("devices") and (reply.get("device") or {}).get("deviceType") == chosen[0]),
                "services": [(s.get("serviceCode"), s.get("deviceType")) for s in reply.get("recommendedServices", [])],
                "message": reply.get("messageVi"),
            })
            print(trial, n, chosen, per_image, ms, "ms")
    ok = [r for r in rows if "error" not in r]
    images = [hit for r in ok for hit in r["per_image"]]
    every = [all(r["per_image"]) for r in ok]
    listed = [all(d in r["devices"] for d, hit in zip(r["chosen"], r["per_image"]) if hit) for r in ok]
    summary = {
        "trials": len(rows), "errors": len(rows) - len(ok),
        "photo_detected_right": f"{sum(images)}/{len(images)}",
        "all_photos_right": f"{sum(every)}/{len(every)}",
        "every_detected_appliance_listed": f"{sum(listed)}/{len(listed)}",
        "lead_is_the_one_talked_about": f"{sum(r['lead_ok'] for r in ok)}/{len(ok)}",
        "median_ms": statistics.median(r["ms"] for r in ok) if ok else None,
        "p90_ms": sorted(r["ms"] for r in ok)[int(len(ok) * 0.9) - 1] if ok else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    Path(args.out).write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
