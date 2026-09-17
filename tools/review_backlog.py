# tools/review_backlog.py
"""Gather everything the corpus says a technician still has to confirm.

Eight hundred and nineteen items are spread across a hundred and fifty-seven
files, four or five at a time, in a section at the bottom that nobody reads end
to end. A technician asked to "review the knowledge base" has no way in.

The number was quoted as 176 and then 240 for weeks, because both counts only
looked at the short labels in the frontmatter and not at the written section
below, which is where the actual questions are. This reads both and prefers the
written one.

It turns them into one ordered list grouped by appliance, so the work can be
done in sittings: an hour on air conditioners settles sixty-nine questions
rather than sixty-nine separate visits to twelve files.

    python tools/review_backlog.py                    # print it
    python tools/review_backlog.py --out docs/CAN-THO-XAC-NHAN.md

Ordered by how many customers each appliance is likely to bring: a question
about an air conditioner is worth more than the same question about a water
purifier, because more people own one and more people call about it. Within an
appliance, faults marked HIGH come first — a wrong answer there costs more than
a wrong price.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline.knowledge_base import get_knowledge_base  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "app" / "data" / "knowledge"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_ITEMS = re.compile(r"^needs_technician_review:\s*\n((?:  - .*\n)+)", re.M)
_FIELD = re.compile(r"^(device_type|fault_code|name_vi|urgency|title_vi):\s*(.+)$", re.M)

_URGENCY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "": 3}


_SECTION = re.compile(
    r"^## Chỗ cần (?:thợ )?xác nhận\s*\n(.*?)(?=\n## |\Z)", re.S | re.M
)


def _questions(text: str, head: str) -> list[str]:
    """The written section if there is one, else the frontmatter labels.

    The frontmatter carries a three-word label; the section carries the whole
    question and usually says why it matters. Where both exist the section is
    the one a technician can act on, so the label is dropped rather than
    listed twice.
    """
    section = _SECTION.search(text)
    if section:
        paragraphs = [
            " ".join(p.split())
            for p in section.group(1).strip().split("\n\n")
            if p.strip()
        ]
        if paragraphs:
            return paragraphs
    # A trailing newline, because the frontmatter capture stops before the
    # closing --- and the item pattern needs one after every line. Without it
    # the last item of every list was dropped, and a list of one vanished
    # entirely: 240 items came out as 83.
    block = _ITEMS.search(head + "\n")
    if block:
        return [
            line.strip().lstrip("- ").strip()
            for line in block.group(1).strip().splitlines()
        ]
    return []


def harvest() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(KNOWLEDGE.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        head = _FRONTMATTER.match(text)
        if not head:
            continue
        fields = dict(_FIELD.findall(head.group(1)))
        for item in _questions(text, head.group(1)):
            rows.append(
                {
                    "file": path.relative_to(KNOWLEDGE).as_posix(),
                    "device": fields.get("device_type", ""),
                    "fault": fields.get("fault_code", ""),
                    "name": fields.get("name_vi") or fields.get("title_vi", ""),
                    "urgency": fields.get("urgency", ""),
                    "item": item,
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    kb = get_knowledge_base()
    rows = harvest()
    by_device: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_device[row["device"] or "chung"].append(row)

    # Appliances with more faults are the ones customers ask about most, and
    # that is the closest thing to a priority order available without traffic
    # data. Said plainly in the document rather than left implied.
    order = sorted(
        by_device,
        key=lambda d: (-len(kb.faults_for_device(d)) if d != "chung" else 1, d),
    )

    lines: list[str] = []
    lines.append("# Những chỗ kho tri thức cần thợ xác nhận")
    lines.append("")
    lines.append(
        f"{len(rows)} mục, trải trên {len({r['file'] for r in rows})} tài liệu. "
        "Danh sách này được sinh ra từ chính kho tri thức bằng "
        "`python tools/review_backlog.py`, nên nó không bao giờ lệch với file gốc."
    )
    lines.append("")
    lines.append(
        "Xếp theo thiết bị, thiết bị nhiều mã bệnh lên trước, vì đó cũng là "
        "thiết bị khách hỏi nhiều nhất. Trong mỗi thiết bị, mã bệnh nguy hiểm "
        "lên trước: trả lời sai ở đó tốn hơn trả lời sai một cái giá."
    )
    lines.append("")
    lines.append(
        "Cách dùng: mỗi lần ngồi xuống xử lý trọn một thiết bị. Trả lời xong "
        "thì sửa thẳng vào tài liệu tương ứng và xoá dòng đó khỏi "
        "`needs_technician_review` ở đầu file."
    )
    lines.append("")

    for device in order:
        group = sorted(
            by_device[device],
            key=lambda r: (_URGENCY_RANK.get(r["urgency"], 3), r["file"]),
        )
        title = kb.device_name_vi(device) or device
        lines.append(f"## {title} — {len(group)} mục")
        lines.append("")
        current = None
        for row in group:
            if row["file"] != current:
                current = row["file"]
                mark = " (KHẨN)" if row["urgency"] == "HIGH" else ""
                label = row["name"] or row["fault"] or row["file"]
                lines.append(f"**{label}**{mark} — `{row['file']}`")
                lines.append("")
            lines.append(f"- {row['item']}")
        lines.append("")

    out = "\n".join(lines) + "\n"
    if args.out:
        path = ROOT / args.out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out, encoding="utf-8", newline="\n")
        print(f"{len(rows)} mục -> {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
