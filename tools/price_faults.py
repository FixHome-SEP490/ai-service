"""Turn the fault-to-part mapping into the price range each fault shows.

Until now every fault in the knowledge base carried a price I had estimated by
hand, flagged `price_reviewed: false` to say so. This replaces those numbers
with ones derived from the two tables the team owns.

The rule, from docs/PRICING-DESIGN.md:

    floor   = the technician's labour, because they travel and work whether or
              not a part is replaced
    ceiling = labour plus the estimated parts

and the three things that keep the ceiling from frightening people off: a fault
maps to a representative part rather than the dearest variant, the ceiling takes
the **middle** of each part's range rather than its top, and a fault whose cost
is genuinely open-ended shows no ceiling at all and says a technician must look.

    python tools/price_faults.py apply      # rewrite the knowledge base
    python tools/price_faults.py preview    # print what would change

The output is JSON in app/data. Nothing here runs at request time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "app" / "data"
KB_PATH = DATA_DIR / "fault_knowledge_base.json"
MAP_PATH = DATA_DIR / "fault_pricing_map.json"
PARTS_PATH = DATA_DIR / "parts_catalog.json"
LABOUR_PATH = DATA_DIR / "labour_catalog.json"

ROUNDING = 10_000
"""Prices are shown to the nearest ten thousand dong.

Nobody quotes 347.500d. Rounding also stops the figure looking computed, which
it is, and which would imply a precision the estimate does not have.
"""


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _round_up(value: int) -> int:
    return -(-value // ROUNDING) * ROUNDING


def _round_down(value: int) -> int:
    return (value // ROUNDING) * ROUNDING


def compute(
    entry: dict,
    parts: Dict[str, dict],
    labour: Dict[str, dict],
) -> Tuple[int, int, bool, List[str]]:
    """Return (floor, ceiling, requires_assessment, problems).

    A missing code is reported rather than skipped: a fault priced off a code
    that no longer exists would quietly quote labour alone, which reads as a
    cheap job and is the most expensive kind of mistake to make here.
    """
    problems: List[str] = []

    service = labour.get(entry["labour"])
    if service is None:
        problems.append(f"unknown labour code {entry['labour']}")
        floor = 0
    else:
        floor = service["price"]

    parts_mid = 0
    for code in entry.get("parts", []):
        part = parts.get(code)
        if part is None:
            problems.append(f"unknown part code {code}")
            continue
        parts_mid += (part["price_min"] + part["price_max"]) // 2

    # A fault with no labour row of its own and no part is one the two tables
    # cannot price. Left alone it would quote the 100.000d inspection fee as a
    # single confident figure, so "nghẹt bồn cầu" would read as costing a
    # hundred thousand — cheap, precise-looking and wrong. Say a technician must
    # look instead, which is what the data actually supports.
    unpriceable = entry["labour"] == "DIAGNOSE_ONSITE" and parts_mid == 0
    assess = bool(entry.get("assess")) or unpriceable
    return _round_down(floor), _round_up(floor + parts_mid), assess, problems


def run(apply: bool) -> None:
    kb = _load(KB_PATH)
    mapping = _load(MAP_PATH)["map"]
    parts = {p["code"]: p for p in _load(PARTS_PATH)["parts"]}
    labour = {s["service_code"]: s for s in _load(LABOUR_PATH)["services"]}

    codes = {f["fault_code"] for f in kb["faults"]}
    missing = sorted(codes - set(mapping))
    extra = sorted(set(mapping) - codes)
    if missing:
        raise SystemExit(
            "These faults have no pricing entry, so they would keep their\n"
            "hand-estimated numbers while the rest move to real ones:\n  "
            + "\n  ".join(missing)
        )
    if extra:
        raise SystemExit(
            "These pricing entries name faults that do not exist:\n  " + "\n  ".join(extra)
        )

    problems: List[str] = []
    changes: List[tuple] = []

    for fault in kb["faults"]:
        entry = mapping[fault["fault_code"]]
        floor, ceiling, assess, found = compute(entry, parts, labour)
        problems.extend(f"{fault['fault_code']}: {p}" for p in found)

        before = (fault["price_min"], fault["price_max"])
        fault["price_min"] = floor
        fault["price_max"] = 0 if assess else ceiling
        fault["price_reviewed"] = True
        fault["requires_assessment"] = assess
        fault["labour_code"] = entry["labour"]
        fault["part_codes"] = entry.get("parts", [])
        if entry.get("note_vi"):
            fault["price_note_vi"] = entry["note_vi"]
        else:
            fault.pop("price_note_vi", None)

        changes.append((fault["fault_code"], before, (floor, ceiling), assess))

    if problems:
        raise SystemExit("The mapping names codes that are not in the catalogues:\n  " + "\n  ".join(problems))

    width = max(len(c[0]) for c in changes)
    for code, before, after, assess in changes:
        tail = "  cần khảo sát" if assess else ""
        print(
            f"{code:<{width}}  {before[0]:>9,} - {before[1]:<9,}"
            f"  ->  {after[0]:>9,} - {after[1]:<9,}{tail}"
        )

    floors = [c[2][0] for c in changes]
    spans = [c[2][1] - c[2][0] for c in changes if not c[3]]
    print(f"\n{len(changes)} faults priced")
    print(f"  floor  {min(floors):,}d to {max(floors):,}d")
    print(f"  spread {min(spans):,}d to {max(spans):,}d")
    print(f"  {sum(1 for c in changes if c[3])} need an on-site assessment instead of a ceiling")

    at_floor = [c[0] for c in changes if c[2][1] == c[2][0] and not c[3]]
    if at_floor:
        print(f"\n{len(at_floor)} are pure labour, so they show one figure rather than a range:")
        for code in at_floor:
            print(f"  {code}")

    if not apply:
        print("\nPreview only; nothing written. Run `apply` to keep this.")
        return

    KB_PATH.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWritten to {KB_PATH.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preview", help="print what would change, write nothing")
    sub.add_parser("apply", help="rewrite the knowledge base")
    args = parser.parse_args()
    run(apply=args.command == "apply")


if __name__ == "__main__":
    main()
