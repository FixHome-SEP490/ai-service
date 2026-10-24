"""Grow `app/data/learned_phrasings.json`: how customers describe each fault.

This is how the assistant learns new wording without anyone training a model.
The retriever reads the file at start-up and matches a customer's message
against it beside the curated symptom lists (`Retriever._learned_evidence`), so
adding phrasings is an edit and a restart.

Two sources:

    python tools/learn_phrasings.py --from-bank          # the dev half of understanding_bank.json
    python tools/learn_phrasings.py --add reviewed.json   # {"FAULT_CODE": ["câu khách tả", ...]}

`--add` is for what a person has checked: a reply a customer marked as wrong,
rewritten into the fault it really was, or a technician's note of how people
describe a fault. Nothing is added unless the fault code exists.

One rule is enforced, because without it every number this project reports
about understanding would be worthless: no phrasing from the `test` half of the
understanding bank may enter the file. A phrase that collides with one is
refused and printed. `tests/test_learned_phrasings.py` checks the same.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "data" / "learned_phrasings.json"
KB = ROOT / "app" / "data" / "fault_knowledge_base.json"
BANK = ROOT / "tools" / "understanding_bank.json"

sys.path.insert(0, str(ROOT / "tools"))
from eval_understanding import split_of  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _key(text: str) -> str:
    return " ".join(text.lower().split())


def held_out() -> set:
    """Every phrase of the understanding bank's test half, normalised."""
    if not BANK.exists():
        return set()
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    out = set()
    for info in bank["devices"].values():
        for phrases in info["faults"].values():
            for kind in ("clear", "indirect"):
                out |= {_key(p) for p in phrases.get(kind, []) if split_of(p) == "test"}
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-bank", action="store_true")
    parser.add_argument("--add", default="")
    args = parser.parse_args()

    codes = {f["fault_code"] for f in json.loads(KB.read_text(encoding="utf-8"))["faults"]}
    current = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"faults": {}}
    faults = {code: list(phrases) for code, phrases in current.get("faults", {}).items()}
    forbidden = held_out()
    added = refused = unknown = 0

    def take(code: str, phrase: str) -> None:
        nonlocal added, refused, unknown
        phrase = " ".join(phrase.split())
        if code not in codes:
            unknown += 1
            print(f"  bỏ: không có lỗi {code}")
            return
        if _key(phrase) in forbidden:
            refused += 1
            print(f"  bỏ: thuộc nửa test của bộ kiểm tra hiểu ý: {phrase}")
            return
        bucket = faults.setdefault(code, [])
        if _key(phrase) not in {_key(p) for p in bucket}:
            bucket.append(phrase)
            added += 1

    if args.from_bank:
        bank = json.loads(BANK.read_text(encoding="utf-8"))
        for info in bank["devices"].values():
            for code, phrases in info["faults"].items():
                for kind in ("clear", "indirect"):
                    for phrase in phrases.get(kind, []):
                        if split_of(phrase) == "dev":
                            take(code, phrase)
    if args.add:
        for code, phrases in json.loads(Path(args.add).read_text(encoding="utf-8")).items():
            for phrase in phrases:
                take(code, phrase)

    now = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    data = {
        "version": now,
        "_comment_vi": (
            "Cách khách đã tả từng lỗi, dùng làm bằng chứng tìm kiếm bên cạnh symptoms_vi. "
            "Không hiện cho khách. Thêm bằng tools/learn_phrasings.py, không sửa tay nửa test "
            "của tools/understanding_bank.json vào đây."
        ),
        "faults": {code: faults[code] for code in sorted(faults)},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(len(v) for v in faults.values())
    print(f"thêm {added}, bỏ vì thuộc test {refused}, bỏ vì sai mã {unknown}; tổng {total} câu cho {len(faults)} lỗi")


if __name__ == "__main__":
    main()
