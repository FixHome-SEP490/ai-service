"""Photographs the detector is unsure of: does the second look help? Needs a running service.

    python tools/eval_photo_check.py --url http://host:port --per-device 15 --out photo_check.json

Each photograph of datasets/collected/<device>/ is sent alone with a message
that names nothing ("xem giúp em cái này"), so the photograph decides. From
the trace it reads what the detector said before the second look and what
the turn settled on, and from photos[] whether the reply calls it a guess.

Counted:
    detector     the detector alone named the right appliance
    final        the turn settled on the right appliance
    fixed        the second look turned a wrong or empty reading into the right one
    broken       the second look turned a right reading into a wrong one
    flagged      a wrong final reading was marked as a guess (the customer is told)
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(__file__).resolve().parents[1] / "datasets" / "collected"


def ask(url: str, path: Path) -> dict:
    image = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    body = {"description": "xem giúp em cái này", "images": [image], "includeTrace": True}
    started = time.time()
    try:
        reply = httpx.post(f"{url}/api/v1/diagnosis/analyze", json=body, timeout=90).json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:80]}
    detector = next((s for s in reply.get("trace") or [] if s.get("name") == "detector"), {})
    detail = detector.get("detail") or {}
    photos = reply.get("photos") or [{}]
    return {
        "said": detail.get("detector_said") if detail.get("checked") else detail.get("device"),
        "final": detail.get("device"),
        "checked": detail.get("checked"),
        "uncertain": bool(photos[0].get("uncertain")),
        "ms": int(1000 * (time.time() - started)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--data", default=str(DATA))
    parser.add_argument("--per-device", type=int, default=15)
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--out", default="photo_check.json")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    cases = []
    for folder in sorted(Path(args.data).iterdir()):
        if not folder.is_dir():
            continue
        files = sorted(folder.glob("*.jp*g"))
        cases += [(folder.name, f) for f in rng.sample(files, min(args.per_device, len(files)))]
    with ThreadPoolExecutor(args.concurrency) as pool:
        rows = list(pool.map(lambda c: {"device": c[0], "file": c[1].name, **ask(args.url, c[1])}, cases))

    ok = [r for r in rows if "error" not in r]
    count = Counter()
    for r in ok:
        right_before = r["said"] == r["device"]
        right_after = r["final"] == r["device"]
        count["detector"] += right_before
        count["final"] += right_after
        count["fixed"] += (not right_before) and right_after
        count["broken"] += right_before and not right_after
        count["asked"] += bool(r["checked"])
        if not right_after and r["final"]:
            count["wrong"] += 1
            count["flagged"] += r["uncertain"]
    n = len(ok) or 1
    print(f"{len(rows)} ảnh, lỗi gọi {len(rows) - len(ok)}")
    print(f"  bộ dò một mình đúng      {count['detector']:4d}/{n}  {100 * count['detector'] / n:5.1f}%")
    print(f"  sau khi xem lại đúng     {count['final']:4d}/{n}  {100 * count['final'] / n:5.1f}%")
    print(f"  xem lại sửa đúng ra      {count['fixed']:4d}    làm sai đi {count['broken']:4d}    số lần xem lại {count['asked']}")
    print(f"  đọc sai mà có báo 'đoán' {count['flagged']:4d}/{count['wrong'] or 1}")
    print(f"  trung vị {sorted(r['ms'] for r in ok)[len(ok) // 2] if ok else 0} ms")
    Path(args.out).write_text(json.dumps({"rows": rows, "count": count}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
