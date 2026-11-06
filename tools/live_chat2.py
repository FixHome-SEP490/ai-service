"""Talk to a served ai-service the way Backend does, and print what the customer would read.

    python tools/live_chat2.py --url http://host:port [--photo path.jpg]

Each conversation sends its customer turns one by one through
/api/v1/diagnosis/analyze with the session the service returns, so the model,
the detector, the session store and the response mapping are all on the path.
A conversation passes when its last reply books one of the expected services
(or declines, for out-of-scope ones). Every reply is printed in full: the
point of a live run is reading it.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

# (name, customer turns, acceptable services; () means it should decline or ask)
CONVERSATIONS: List[Tuple[str, List[str], Tuple[str, ...]]] = [
    ("PO 06/11 rơi xuống đất", ["Điều hoà nhà tôi bị rơi xuống", "Máy đã rơi hẳn xuống đất rồi"], ("AC-01", "AC-03")),
    ("PO 06/11 mùi hôi, bẩn", ["máy lạnh tôi có mùi hôi như thối tỏa ra , và tôi nhìn rất bẩn"], ("AC-02",)),
    ("BUG 52 vệ sinh tủ lạnh", ["tôi còn 1 tủ lạnh xuất hiện mùi hôi khó chịu cần thêm dịch vụ vệ sinh tủ lạnh"], ("FR-02",)),
    ("BUG 54 nhiều lượt", ["máy lạnh chảy nước và không lạnh", "Không.", "Bên phải dàn lạnh.", "Vậy giờ em thấy sao?"], ("AC-01", "AC-02")),
    ("mơ hồ rồi trả lời", ["máy giặt bị sao á", "bấm giặt thì kêu tít tít mà không có nước vào"], ("WM-01",)),
    ("mùi gas", ["bếp nhà em có mùi gas"], ("KT-07",)),
    ("hai máy", ["máy giặt không vắt được, tiện vệ sinh luôn máy lạnh phòng ngủ"], ("WM-01", "AC-02")),
    ("lạc đề", ["laptop em vô nước bật không lên"], ()),
]


def _image(path: Optional[str]) -> List[str]:
    if not path:
        return []
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return [f"data:image/jpeg;base64,{data}"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", required=True)
    p.add_argument("--photo", help="sent with the first turn of every conversation")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    passed, latencies = 0, []
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=60) as client:
        for name, turns, want in CONVERSATIONS:
            print(f"\n=== {name}")
            session, last = None, {}
            for i, text in enumerate(turns):
                body = {"description": text, **({"sessionId": session} if session else {})}
                if i == 0 and args.photo:
                    body["images"] = _image(args.photo)
                started = time.perf_counter()
                r = client.post("/api/v1/diagnosis/analyze", json=body)
                latencies.append(time.perf_counter() - started)
                last = r.json()
                if r.status_code != 200:
                    print(f"  HTTP {r.status_code}: {json.dumps(last, ensure_ascii=False)[:200]}")
                    break
                session = last.get("sessionId")
                question = (last.get("clarification") or {}).get("questionsVi") or []
                options = (last.get("clarification") or {}).get("answerOptionsVi") or []
                services = [s["serviceCode"] for s in last.get("recommendedServices") or []]
                print(f"  Khách: {text}")
                print(f"  Bot [{last.get('status')} {(last.get('device') or {}).get('deviceType')} {services}]: "
                      f"{last.get('messageVi') or ''}{' ' + question[0] if question else ''}{' ' + str(options) if options else ''}")
            services = [s["serviceCode"] for s in last.get("recommendedServices") or []]
            ok = bool(set(services) & set(want)) if want else not services
            passed += ok
            print(f"  -> {'OK' if ok else 'SAI'}")
    lat = sorted(latencies)
    print(f"\n{passed}/{len(CONVERSATIONS)} conversations; latency p50 {lat[len(lat) // 2]:.2f}s max {lat[-1]:.2f}s")


if __name__ == "__main__":
    main()
