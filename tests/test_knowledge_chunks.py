"""The knowledge corpus, checked as data rather than read as prose.

Four things are worth holding still.

Chunk size, because a `##` section is what retrieval actually hands to the
model. Too long and one section crowds out the candidate faults, the price rows
and what the customer already said; too short and the section arrives without
the sentence that gave it meaning.

No prices anywhere in the corpus, because the price tables are the single
source. A number written into prose would contradict them and the model would
quote whichever it saw last. This is the rule most likely to be broken by
accident while writing, so it is checked mechanically.

Frontmatter, because it is what lets retrieval narrow by device before it
scores anything, and a typo in a fault code fails silently otherwise.

And the codes themselves, because a file named after a fault that no longer
exists in the fault table is dead weight nobody notices.
"""

import re
from collections import Counter

import pytest

from app.services.pipeline.knowledge_base import get_knowledge_base

from tools.chunk_kb import (  # noqa: E402  (tools/ is a sibling package)
    KB_DIR,
    MAX_CHARS,
    MIN_CHARS,
    chunk_file,
    load_corpus,
    parse_front_matter,
)

KB_FILES = sorted(p for p in KB_DIR.rglob("*.md") if p.name != "README.md")


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


def _rel(path) -> str:
    return path.relative_to(KB_DIR).as_posix()


# -- there is a corpus at all ---------------------------------------------


def test_corpus_is_not_empty(corpus):
    assert KB_FILES, "không tìm thấy file nào trong app/data/knowledge"
    assert corpus


# -- chunk size ------------------------------------------------------------


def test_no_chunk_is_too_long(corpus):
    """One section should not swallow the whole context window."""
    over = [(c.source_file, c.heading_vi, c.size) for c in corpus if c.size > MAX_CHARS]
    assert not over, f"chunk quá dài, nên tách nhỏ: {over[:5]}"


def test_no_chunk_is_too_short(corpus):
    """A section has to carry enough context to stand on its own."""
    under = [(c.source_file, c.heading_vi, c.size) for c in corpus if c.size < MIN_CHARS]
    assert not under, f"chunk quá ngắn, thiếu liên kết: {under[:5]}"


def test_median_chunk_stays_in_the_comfortable_band(corpus):
    """Guards against the corpus drifting long or short as it grows.

    Not a hard rule about any one section — a spot check that the writing habit
    has not changed across a hundred files.
    """
    import statistics

    median = statistics.median(c.size for c in corpus)
    assert 400 <= median <= 1500, f"trung vị chunk lệch khỏi dải quen thuộc: {median}"


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_every_file_splits_into_several_chunks(path):
    """A file that yields one chunk is a file that was not written to be chunked."""
    chunks = chunk_file(path)
    assert len(chunks) >= 3, f"{_rel(path)} chỉ ra {len(chunks)} chunk"


# -- no prices in the corpus ----------------------------------------------

_MONEY = re.compile(
    r"""
    \d{1,3}(?:[.,]\d{3})+            # 100.000  1,200,000
    | \d+\s*(?:đ\b|đồng|vnđ|vnd)     # 500đ  500 đồng
    | \d+\s*(?:nghìn|ngàn|triệu)\b   # 500 nghìn  2 triệu
    """,
    re.VERBOSE | re.IGNORECASE,
)

_MONEY_SHORTHAND = re.compile(
    r"(?:giá|tiền|phí|chi phí|khoảng|hết|mất|tốn)\D{0,20}\b\d+\s*k\b",
    re.IGNORECASE,
)
"""The bare "k" suffix needs a money word beside it to count.

In Vietnamese appliance talk it is ambiguous on its own: "máy lạnh 9k" is nine
thousand BTU, not nine thousand đồng, and the corpus quotes customers saying
exactly that. A rule that fails on correct text is a rule that gets switched
off, so this one only fires on "khoảng 500k" and leaves "máy lạnh 9k" alone."""


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_no_money_amounts_anywhere_in_the_corpus(path):
    """The price tables are the only source of a number a customer is told.

    Prose that names a figure creates a second source that drifts, and the model
    has no way to know which one is current. The corpus explains what moves a
    price instead.
    """
    raw = path.read_text(encoding="utf-8")
    hits = _MONEY.findall(raw) + _MONEY_SHORTHAND.findall(raw)
    assert not hits, (
        f"{_rel(path)} có con số tiền: {hits[:5]}. "
        "Giá chỉ lấy từ bảng giá của hệ thống."
    )


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_fault_and_device_files_say_where_prices_come_from(path):
    """Every fault and device file carries the rule on its face."""
    fields, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    if fields.get("doc_type") not in ("fault", "device"):
        return
    assert "price_policy" in fields, f"{_rel(path)} thiếu price_policy"


# -- frontmatter -----------------------------------------------------------


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_frontmatter_has_the_required_keys(path):
    fields, body = parse_front_matter(path.read_text(encoding="utf-8"))
    assert fields, f"{_rel(path)} không có frontmatter"
    for key in ("doc_id", "doc_type", "last_reviewed"):
        assert fields.get(key), f"{_rel(path)} thiếu {key}"
    assert body.strip(), f"{_rel(path)} không có nội dung"


def test_doc_ids_are_unique(corpus):
    counts = Counter(c.doc_id for c in corpus)
    dupes = [doc_id for doc_id, n in counts.items() if doc_id and n and False]
    # doc_id repeats once per chunk by design; uniqueness is per file.
    per_file = {}
    for c in corpus:
        per_file.setdefault(c.doc_id, set()).add(c.source_file)
    dupes = [doc_id for doc_id, files in per_file.items() if len(files) > 1]
    assert not dupes, f"doc_id dùng cho nhiều file: {dupes}"


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_doc_type_is_one_of_the_known_kinds(path):
    fields, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    assert fields.get("doc_type") in {"fault", "device", "system", "persona", "policy"}


# -- codes point at things that exist -------------------------------------


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_fault_code_exists_in_the_fault_table(path, kb):
    fields, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    code = fields.get("fault_code")
    if not code:
        return
    assert kb.fault(code) is not None, f"{_rel(path)}: mã bệnh {code} không có trong bảng"


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_device_type_exists_in_the_catalog(path, kb):
    fields, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    device = fields.get("device_type")
    if not device:
        return
    assert kb.device_name_vi(device), f"{_rel(path)}: thiết bị {device} không có trong catalog"


@pytest.mark.parametrize("path", KB_FILES, ids=_rel)
def test_fault_file_is_named_after_its_code(path):
    fields, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    code = fields.get("fault_code")
    if not code:
        return
    assert path.stem == code, f"{_rel(path)} tên file khác mã bệnh {code}"


# -- the corpus knows what it still owes ----------------------------------


def test_every_written_fault_file_belongs_to_a_written_device_file(corpus):
    """A fault whose appliance has no overview leaves the model without the
    airflow trees and the golden question that make the fault readable."""
    devices = {c.device_type for c in corpus if c.doc_type == "device"}
    orphans = sorted(
        {
            c.device_type
            for c in corpus
            if c.doc_type == "fault" and c.device_type and c.device_type not in devices
        }
    )
    assert not orphans, f"có file bệnh nhưng chưa có file thiết bị: {orphans}"


def test_persona_and_system_layers_are_present(corpus):
    """These two layers are what keep answers in voice and inside the business
    rules; retrieval without them produces a correct lookup table."""
    kinds = {c.doc_type for c in corpus}
    assert "persona" in kinds, "chưa có tài liệu persona"
    assert "system" in kinds, "chưa có tài liệu tổng quan hệ thống"
