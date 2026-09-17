"""Copy the customer wording out of the written corpus into symptoms_vi.

The corpus already answers the question the retriever needs answered. Every
fault file carries sections listing, in quotation marks, what a customer
actually types for that fault: the blunt version, the version with no tone
marks, the version that describes a consequence instead of a symptom, the
version where the customer has already guessed wrong. That was written once,
per fault, against the trade. Retrieval was matching against a separate
four-to-seven item list maintained by hand, and the two had drifted.

The drift was not cosmetic. A sweep over every phrase the corpus attributes to
a HIGH-urgency fault found that a quarter of them did not reach that fault at
all, and several reached nothing whatsoever -- "ong nuoc bi be" and "am sieu
toc bi ro nuoc" among them. Those two are the cases where the answer has to
open with a warning, so failing to shortlist the fault means the warning is
never pinned and the customer is told nothing.

Run it after editing any fault file:

    python tools/sync_symptoms.py --check     # fail if the KB is behind
    python tools/sync_symptoms.py --write

Only symptoms_vi is touched. Prices, urgency, part codes and every review flag
are left exactly as the team set them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline.corpus import get_corpus  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KB_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "fault_knowledge_base.json"

PHRASING_HEADINGS = (
    "Khách nói thế nào",
    "Khách mô tả cụt",
    "Khách mô tả đầy đủ thì trông thế nào",
    "Khách mô tả bằng hệ quả",
    "Khách gõ không dấu, gõ tắt",
    "Khách tự chẩn đoán rồi nói kết luận",
    "Khách gọi tên bộ phận theo dân gian",
)
"""Sections that quote the customer, and only those.

The neighbouring sections quote other people. "Nói ngắn gọn cho khách" is the
technician's reply, "Khách hay hỏi thêm" and "Khách hỏi giá trước" are
questions rather than symptoms, and "Việc khách không nên tự làm" is a list of
things that must never be read as a description of what is wrong.
"""

MIN_CHARS = 6
MAX_CHARS = 60
"""Long quotes are whole sentences of narrative, not search terms."""


def phrases_by_fault() -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = {}
    for chunk in get_corpus():
        if chunk.doc_type != "fault" or not chunk.fault_code:
            continue
        if not chunk.heading_vi.startswith(PHRASING_HEADINGS):
            continue
        for quote in re.findall(r'"([^"]+)"', chunk.text):
            phrase = " ".join(quote.split())
            if MIN_CHARS <= len(phrase) <= MAX_CHARS:
                found.setdefault(chunk.fault_code, []).append(phrase)
    return found


def merged(existing: List[str], harvested: List[str]) -> List[str]:
    """Curated entries stay first, and stay. Order is what a reviewer reads."""
    out = list(existing)
    seen = {p.casefold() for p in existing}
    for phrase in harvested:
        if phrase.casefold() not in seen:
            seen.add(phrase.casefold())
            out.append(phrase)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="update the KB in place")
    parser.add_argument("--check", action="store_true", help="exit 1 if it is behind")
    args = parser.parse_args()

    data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    harvest = phrases_by_fault()

    behind: List[str] = []
    added = 0
    for fault in data["faults"]:
        code = fault["fault_code"]
        new = merged(fault["symptoms_vi"], harvest.get(code, []))
        if new != fault["symptoms_vi"]:
            behind.append(f"{code} (+{len(new) - len(fault['symptoms_vi'])})")
            added += len(new) - len(fault["symptoms_vi"])
            fault["symptoms_vi"] = new

    covered = sum(1 for f in data["faults"] if f["fault_code"] in harvest)
    print(f"{covered}/{len(data['faults'])} bệnh có mục trích lời khách trong corpus")

    if not behind:
        print("symptoms_vi đã khớp corpus")
        return 0

    print(f"{len(behind)} bệnh còn thiếu, tổng {added} cách nói")
    if args.check:
        for line in behind[:20]:
            print(f"  {line}")
        print("chạy: python tools/sync_symptoms.py --write")
        return 1
    if args.write:
        KB_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"đã ghi {KB_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
