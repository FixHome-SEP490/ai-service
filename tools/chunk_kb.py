"""Split the knowledge corpus into retrievable chunks and report on their size.

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

The same parsing is used by tests/test_knowledge_chunks.py, so the bounds below
are enforced rather than merely reported.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

KB_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "knowledge"

MIN_CHARS = 200
"""Below this a section has been cut off from what gives it meaning."""

MAX_CHARS = 4000
"""Above this one section starts to crowd out the rest of the bundle."""

TARGET_LOW = 400
TARGET_HIGH = 2500
"""Comfortable band. Outside it is worth a look; outside MIN/MAX fails a test."""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Chunk:
    """One `##` section, standing on its own."""

    doc_id: str
    doc_type: str
    source_file: str
    heading_vi: str
    text: str
    device_type: Optional[str] = None
    fault_code: Optional[str] = None

    @property
    def size(self) -> int:
        return len(self.text)


def parse_front_matter(raw: str) -> tuple[Dict[str, str], str]:
    """Pull the YAML block off the top without needing a YAML parser.

    Only flat `key: value` lines are read. List and block values are recorded as
    present but not parsed, because nothing here needs their contents — the
    tests check that required keys exist and that the scalar ones are sane.
    """
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    block = raw[3:end]
    body = raw[end + 4 :]

    fields: Dict[str, str] = {}
    for line in block.splitlines():
        if not line or line.startswith(("  ", "-", "#")):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, body


def split_sections(body: str) -> Iterator[tuple[str, str]]:
    """Yield (heading, text) for every `##` section.

    The `#` title and anything before the first `##` are skipped: the title is
    a label, not a retrievable unit, and prose above the first section would
    arrive with no heading to say what it is about.
    """
    parts = re.split(r"^## +(.+)$", body, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        text = parts[i + 1].strip()
        if heading and text:
            yield heading, text


def chunk_file(path: Path) -> List[Chunk]:
    raw = path.read_text(encoding="utf-8")
    fields, body = parse_front_matter(raw)
    rel = path.relative_to(KB_DIR).as_posix()
    return [
        Chunk(
            doc_id=fields.get("doc_id", ""),
            doc_type=fields.get("doc_type", ""),
            source_file=rel,
            heading_vi=heading,
            text=text,
            device_type=fields.get("device_type"),
            fault_code=fields.get("fault_code"),
        )
        for heading, text in split_sections(body)
    ]


def load_corpus(kb_dir: Path = KB_DIR) -> List[Chunk]:
    """Every chunk in the corpus, in a stable order.

    README.md is skipped: it documents the pattern for whoever writes the next
    file, and retrieving it would put instructions to authors in front of a
    customer.
    """
    chunks: List[Chunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        if path.name == "README.md":
            continue
        chunks.extend(chunk_file(path))
    return chunks


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
