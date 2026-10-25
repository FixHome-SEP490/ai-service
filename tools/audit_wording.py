"""How the served model's answers read: count the wording faults in saved answers.

    python tools/audit_wording.py suite.json live.json multi_message.json understanding.json
    python tools/audit_wording.py --fix ...     # the same answers after app's own clean-up

The JSON files are what eval_chat_suite.py, eval_dialogue_live.py,
eval_multi_message.py --url and eval_understanding.py --url write. Every
customer-facing answer in them is checked against the faults seen on the
served model: letters from another script, the customer talked about in the
third person, verdicts the assistant cannot have reached, actions it cannot
take, its own instructions read back, broken price phrases, English, the same
sentence twice. With --fix each answer is first passed through the clean-up
the service applies (qwen_client), which measures that clean-up on real text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECKS = {
    "chữ nước ngoài (Trung/Nhật/Hàn)": re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]"),
    "gọi khách ngôi thứ ba": re.compile(r"(?<![\"“])\b[Kk]hách(?!\s*:)(?! hàng)\b"),
    "khẳng định quá chắc": re.compile(
        r"(?i)\b(?:(?:em|tôi)(?: đã)?(?: kiểm tra và)? (?:xác nhận|khẳng định)|chắc chắn là|chắc chắn rằng|em đã kiểm tra)\b"
    ),
    "hứa việc AI không làm được": re.compile(
        r"(?i)\b(?:em|tôi) (?:sẽ|đã) (?:giúp (?:anh/chị |bác |cô |chú )?)?(?:đặt|gửi|cử|liên hệ|gọi|sắp xếp|điều)\b"
        r"(?! (?:câu|thêm câu))"
    ),
    "đọc lại chỉ dẫn": re.compile(
        r"(?i)\b(?:em đã đọc|dựa trên (?:tài liệu|thông tin)|theo tài liệu(?! của hãng)|anh/chị đang nói về|thông tin anh/chị gửi|thông tin khách|đúng tên dịch vụ|tên gọi \"FixHome)\b"
    ),
    "câu giá gãy": re.compile(r"(?i)\b(?:từ\s+[\d.]+\s*đ?\s*đến khi|khoảng\s+[\d.]+đ?,\s*phần còn lại)\b"),
    "xưng tôi / gọi bạn": re.compile(r"\b(?:[Tt]ôi|[Bb]ạn)\b"),
    "tiếng Anh lẫn": re.compile(r"(?i)\b(?:the|and|please|sorry|check|repair|service|technician)\b"),
    "gấp gáp, cường điệu": re.compile(r"(?i)\b(?:ngay lập tức|khẩn cấp ngay|tuyệt đối không bao giờ)\b"),
}


def sentences(text: str) -> list:
    return [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 25]


def answers(path: Path):
    """Every customer-facing answer a saved run holds."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows", data) if isinstance(data, dict) else data
    for row in rows:
        for key in ("reply", "message_vi", "messageVi", "answer"):
            if isinstance(row.get(key), str) and row[key].strip():
                yield row[key]
        for turn in row.get("turns_out", []) or row.get("replies", []) or []:
            if isinstance(turn, str) and turn.strip():
                yield turn
            elif isinstance(turn, dict):
                for key in ("reply", "message", "messageVi", "answer"):
                    if isinstance(turn.get(key), str) and turn[key].strip():
                        yield turn[key]


def audit(texts, fix=False, show=4):
    if fix:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app.services.pipeline.qwen_client import _fix_pronouns, _fix_spelling, _tidy_answer

        texts = [_tidy_answer(_fix_spelling(_fix_pronouns(t))) for t in texts]
    found = Counter()
    examples = {}
    for text in texts:
        hit = False
        for name, pattern in CHECKS.items():
            m = pattern.search(text)
            if m:
                found[name] += 1
                hit = True
                examples.setdefault(name, []).append(text[max(0, m.start() - 60): m.end() + 60].replace("\n", " "))
        said = sentences(text)
        if len(said) != len(set(said)):
            found["lặp nguyên câu"] += 1
            hit = True
        found["câu có ít nhất một lỗi"] += hit
    n = len(texts) or 1
    print(f"{len(texts)} câu trả lời" + (" (sau bước làm sạch của service)" if fix else ""))
    for name, count in found.most_common():
        print(f"  {name:34} {count:5d}  {100 * count / n:5.1f}%")
    for name, items in examples.items():
        for item in items[:show]:
            print(f"    [{name}] ...{item}...")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--show", type=int, default=3)
    args = parser.parse_args()
    texts = [t for f in args.files for t in answers(Path(f))]
    texts = list(dict.fromkeys(texts))
    audit(texts, fix=args.fix, show=args.show)


if __name__ == "__main__":
    main()
