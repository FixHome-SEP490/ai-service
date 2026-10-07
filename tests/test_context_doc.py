"""docs/CONTEXT.md follows the rules written in its own section 0.

The same rules live in backend, web and mobile (TypeScript copies of
checkContext); change them everywhere or nowhere.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

REPO = "ai-service"
CONTEXT = Path(__file__).resolve().parents[1] / "docs" / "CONTEXT.md"

REQUIRED_SECTIONS = [
    "## 0. Quy tắc cập nhật file này (bắt buộc)",
    "## 1. Repo này là gì trong FixHome",
    "## 2. Liên kết với các repo khác",
    "## 3. Trạng thái hiện tại",
    "## 4. Kiến trúc và thư mục chính",
    "## 5. Hợp đồng với repo khác",
    "## 6. Chạy, kiểm thử và cổng chất lượng",
    "## 7. Quyết định đã chốt",
    "## 8. Việc đang dở và rủi ro đã biết",
    "## 9. Nhật ký cập nhật context",
]
MAX_LINES = 700
MAX_LOG_ENTRIES = 40

STAMP = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\+7\)"
HEADER = re.compile(
    rf"^> Cập nhật lần cuối: {STAMP} · Người cập nhật \(git\): ([^·]+?) · Nhánh: (\S+)$"
)
LOG_ENTRY = re.compile(rf"^- {STAMP} \| ([^|]+?) \| ([^|\s]+) \| (.{{10,}})$")

FORBIDDEN = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}"), "API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "cloud access key"),
    (re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@/]+@", re.I), "URL with credentials"),
    (
        re.compile(
            r"\b(password|passwd|mật khẩu|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=!@#$%^&*]{6,}",
            re.I,
        ),
        "credential value",
    ),
    (
        re.compile(r"\b(TODO|TBD|FIXME|FILL LATER|lorem ipsum)\b", re.I),
        "placeholder (write CHƯA KIỂM CHỨNG or leave it out)",
    ),
]
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0", "10.0.2.2"}
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _valid_stamp(stamp: str) -> bool:
    try:
        parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    return parsed.year >= 2026


def check_context(text: str, repo: str) -> list[str]:
    problems: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")

    if lines[0] != f"# Context repo {repo} — FixHome":
        problems.append(f'line 1 must be "# Context repo {repo} — FixHome"')
    if len(lines) > MAX_LINES:
        problems.append(f"file has {len(lines)} lines; keep it under {MAX_LINES}")

    header_line = next((line for line in lines[:6] if line.startswith("> Cập nhật lần cuối:")), None)
    header = HEADER.match(header_line) if header_line else None
    if not header:
        problems.append(
            'header must read "> Cập nhật lần cuối: YYYY-MM-DD HH:mm (UTC+7) · '
            'Người cập nhật (git): <git user.name> · Nhánh: <branch>" within the first 6 lines'
        )
    elif not _valid_stamp(header.group(1)):
        problems.append(f"header time {header.group(1)} is not a real date and time")

    cursor = -1
    for section in REQUIRED_SECTIONS:
        if section not in lines:
            problems.append(f'missing section "{section}"')
            continue
        at = lines.index(section)
        if at < cursor:
            problems.append(f'section "{section}" is out of order')
        cursor = at
        following = [i for i in range(at + 1, len(lines)) if lines[i].startswith("## ")]
        end = following[0] if following else len(lines)
        if not any(line.strip() for line in lines[at + 1 : end]):
            problems.append(f'section "{section}" is empty')
    for line in lines:
        if line.startswith("## ") and line not in REQUIRED_SECTIONS:
            problems.append(f'unexpected top-level section "{line}"; use ### inside a required section')

    if REQUIRED_SECTIONS[-1] in lines:
        start = lines.index(REQUIRED_SECTIONS[-1])
        entries = [line for line in lines[start + 1 :] if line.startswith("- ")]
        if len(entries) > MAX_LOG_ENTRIES:
            problems.append(f"log has {len(entries)} entries; keep the newest {MAX_LOG_ENTRIES}")
        parsed = [(line, LOG_ENTRY.match(line)) for line in entries]
        for line, match in parsed:
            if not match:
                problems.append(
                    'log entry does not follow "- YYYY-MM-DD HH:mm (UTC+7) | <git user.name> | '
                    f'<branch or PR> | <what changed>": {line}'
                )
            elif not _valid_stamp(match.group(1)):
                problems.append(f"log entry time {match.group(1)} is not a real date and time")
        stamps = [match.group(1) for _, match in parsed if match]
        if any(later > earlier for earlier, later in zip(stamps, stamps[1:])):
            problems.append("log entries must be newest first")
        top = parsed[0][1] if parsed else None
        if not top:
            problems.append("log must have at least one entry")
        elif header and (top.group(1) != header.group(1) or top.group(2).strip() != header.group(2).strip()):
            problems.append("the newest log entry must carry the same time and git name as the header")

    for number, line in enumerate(lines, start=1):
        for pattern, what in FORBIDDEN:
            if pattern.search(line):
                problems.append(f"line {number}: {what} is not allowed")
        for ip in IPV4.findall(line):
            if ip not in ALLOWED_IPS:
                problems.append(f"line {number}: IP address {ip} is not allowed")
    return problems


def test_context_passes_every_rule():
    assert check_context(CONTEXT.read_text(encoding="utf-8"), REPO) == []


def test_context_rules_reject_a_broken_file():
    text = CONTEXT.read_text(encoding="utf-8")
    broken = (
        re.sub(r"^> Cập nhật lần cuối: .*$", "> Cập nhật lần cuối: hôm qua", text, count=1, flags=re.M)
        .replace("## 7. Quyết định đã chốt", "## 7. Ghi chú linh tinh")
        + "\nmật khẩu: Abc12345678\nmáy GPU ở 203.0.113.7\n- hôm nay | ai đó | nhánh | sửa linh tinh\n"
    )
    problems = check_context(broken, REPO)
    assert any(p.startswith("header must read") for p in problems)
    assert any('missing section "## 7.' in p for p in problems)
    assert any("credential value" in p for p in problems)
    assert any("IP address 203.0.113.7" in p for p in problems)
    assert any(p.startswith("log entry does not follow") for p in problems)
