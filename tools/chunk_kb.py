"""Report on how the knowledge corpus splits into retrievable chunks.

The corpus is written to be chunked at `##` headings, so a section is the unit
that gets pulled out and handed to the model. That makes section length a real
engineering constraint rather than a style preference.

A section that is too long dilutes the context: the model receives a page when
it needed a paragraph, and the rest of the bundle — the candidate faults, the
price rows, what the customer already said — gets crowded out.

A section that is too short loses the links that make it mean anything. "Gió
yếu thì về phía nghẽn gió" retrieved alone, without the sentence naming the
appliance, is not an answer.

    python tools/chunk_kb.py                 # report
    python tools/chunk_kb.py --out chunks.json
    python tools/chunk_kb.py --show-outliers

The parsing itself lives in `app/services/pipeline/corpus.py`, because the
request path loads the same chunks and must not depend on a developer script.
This file is the report around it, and re-exports the names so existing callers
and tests keep working.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline.corpus import (  # noqa: E402
    KB_DIR,
    MAX_CHARS,
    MIN_CHARS,
    TARGET_HIGH,
    TARGET_LOW,
    Chunk,
    chunk_file,
    load_corpus,
    parse_front_matter,
    split_sections,
)

__all__ = [
    "KB_DIR",
    "MAX_CHARS",
    "MIN_CHARS",
    "TARGET_HIGH",
    "TARGET_LOW",
    "Chunk",
    "chunk_file",
    "load_corpus",
    "parse_front_matter",
    "split_sections",
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _bar(value: int, scale: int = 60) -> str:
    return "#" * max(1, round(value / scale))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write chunks to this JSON file")
    parser.add_argument("--show-outliers", action="store_true")
    parser.add_argument("--by-file", action="store_true")
    args = parser.parse_args()

    chunks = load_corpus()
    if not chunks:
        print("Chưa có file nào trong kho tri thức.")
        return

    sizes = [c.size for c in chunks]
    files = {c.source_file for c in chunks}

    print(f"{len(files)} file, {len(chunks)} chunk, {sum(sizes):,} ký tự\n")
    print(f"{'nhỏ nhất':<14}{min(sizes):>7}")
    print(f"{'trung vị':<14}{int(statistics.median(sizes)):>7}")
    print(f"{'trung bình':<14}{int(statistics.mean(sizes)):>7}")
    print(f"{'lớn nhất':<14}{max(sizes):>7}")

    buckets = [(0, 200), (200, 400), (400, 800), (800, 1500), (1500, 2500), (2500, 10**9)]
    print("\nphân bố cỡ chunk")
    for low, high in buckets:
        n = sum(1 for s in sizes if low <= s < high)
        label = f"{low}-{high}" if high < 10**9 else f"{low}+"
        flag = ""
        if high <= MIN_CHARS:
            flag = "  <- quá ngắn, thiếu liên kết"
        elif low >= TARGET_HIGH:
            flag = "  <- dài, cân nhắc tách"
        print(f"  {label:<12}{n:>5}  {_bar(n)}{flag}")

    by_type: Dict[str, int] = {}
    for c in chunks:
        by_type[c.doc_type or "(trống)"] = by_type.get(c.doc_type or "(trống)", 0) + 1
    print("\ntheo loại tài liệu")
    for name, n in sorted(by_type.items()):
        print(f"  {name:<12}{n:>5}")

    too_small = [c for c in chunks if c.size < MIN_CHARS]
    too_large = [c for c in chunks if c.size > MAX_CHARS]
    print(f"\nngoài ngưỡng cứng: {len(too_small)} quá ngắn, {len(too_large)} quá dài")

    if args.show_outliers:
        for title, group in [("QUÁ NGẮN", too_small), ("QUÁ DÀI", too_large)]:
            if not group:
                continue
            print(f"\n{title}")
            for c in sorted(group, key=lambda x: x.size):
                print(f"  {c.size:>6}  {c.source_file} :: {c.heading_vi}")

    if args.by_file:
        print("\ntheo file")
        per_file: Dict[str, List[int]] = {}
        for c in chunks:
            per_file.setdefault(c.source_file, []).append(c.size)
        for name in sorted(per_file):
            s = per_file[name]
            print(
                f"  {name:<42}{len(s):>4} chunk  "
                f"TB {int(statistics.mean(s)):>5}  max {max(s):>5}"
            )

    if args.out:
        Path(args.out).write_text(
            json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nĐã ghi {len(chunks)} chunk vào {args.out}")


if __name__ == "__main__":
    main()
