# app/services/pipeline/corpus.py
"""Loads the written knowledge corpus as retrievable chunks.

The corpus is 132 markdown files under `app/data/knowledge/`: one per fault, one
per appliance, plus the persona and business layers. It is prose, written to be
cut at `##` headings, and each section is meant to stand on its own once
retrieval pulls it away from its neighbours.

This module only reads and splits. Scoring lives in `retriever.py`, the same
split as `knowledge_base.py` — data here, ranking there — so that swapping
lexical matching for embeddings later touches one file.

It used to live in `tools/chunk_kb.py`, which meant the request path depended on
a developer script. The script now imports from here instead, so there is one
parser and the tests keep checking the same code the service runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

KB_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"

MIN_CHARS = 200
"""Below this a section has been cut off from what gives it meaning."""

MAX_CHARS = 4000
"""Above this one section starts to crowd out the rest of the bundle."""

TARGET_LOW = 400
TARGET_HIGH = 2500
"""Comfortable band. Outside it is worth a look; outside MIN/MAX fails a test."""


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
    safety_heading: Optional[str] = None
    """Which section of this file has to be said before diagnosing.

    Declared in the frontmatter rather than inferred from the wording, because
    a safety mechanism should not depend on guessing. The first attempt matched
    headings by pattern and reached 13 of the 25 dangerous faults: the corpus
    words the instruction differently per cluster — "Bốn việc phải nói ngay",
    "Câu trả lời đầu tiên, trước mọi câu hỏi", "Ca khẩn nhất của cụm điện" — and
    the twelve it missed included a burst pipe and a gas regulator.
    """

    @property
    def size(self) -> int:
        return len(self.text)

    @property
    def is_safety(self) -> bool:
        return bool(self.safety_heading) and self.heading_vi == self.safety_heading

    def as_passage_vi(self) -> str:
        """Heading and body together, the way it should reach the model.

        The heading is half the meaning of a section — "Vì sao lửa đỏ", "Câu
        phải nói ngay" — and dropping it hands over a paragraph with no label
        saying what question it answers.
        """
        return f"{self.heading_vi}\n{self.text}"


def parse_front_matter(raw: str) -> Tuple[Dict[str, str], str]:
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


def split_sections(body: str) -> Iterator[Tuple[str, str]]:
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


def chunk_file(path: Path, kb_dir: Path = KB_DIR) -> List[Chunk]:
    raw = path.read_text(encoding="utf-8")
    fields, body = parse_front_matter(raw)
    try:
        rel = path.relative_to(kb_dir).as_posix()
    except ValueError:
        rel = path.name
    return [
        Chunk(
            doc_id=fields.get("doc_id", ""),
            doc_type=fields.get("doc_type", ""),
            source_file=rel,
            heading_vi=heading,
            text=text,
            device_type=fields.get("device_type"),
            fault_code=fields.get("fault_code"),
            safety_heading=fields.get("safety_heading"),
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
        chunks.extend(chunk_file(path, kb_dir))
    return chunks


@lru_cache(maxsize=1)
def get_corpus() -> Tuple[Chunk, ...]:
    """The corpus, parsed once per process.

    Two megabytes of markdown across 132 files: cheap enough to hold in memory,
    far too slow to re-read per request.
    """
    return tuple(load_corpus())
