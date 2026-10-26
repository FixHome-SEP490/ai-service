"""Turn the answers customers marked wrong into conversations for the test set.

    python tools/feedback_to_cases.py --api https://<backend>/api/v1 --token <admin JWT> --days 30
    python tools/feedback_to_cases.py --file quality.json

The backend keeps a customer's disagreement on the conversation, and an admin
reads them on /console/admin/ai-quality. This takes the same list (from the
backend, or a saved copy of GET /admin/ai-quality) and writes one draft
Dialogue per case to tools/feedback_cases_draft.py: the customer's turns as
they typed them, the reply they rejected, and their note. A person fills in
`must_not` / `expect_any` from the note and moves the case into
dialogue_cases.py; nothing is added to the test set unreviewed, because the
note says what was wrong but not always what is right.

The customer's words are used as they are, with no names, phone numbers or
addresses added: the backend summary holds only what was typed to the assistant.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).resolve().parent / "feedback_cases_draft.py"

_PHONE = re.compile(r"(?<!\d)(?:\+?84|0)\d{8,10}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _scrub(text: str) -> str:
    """Contact details typed into the chat stay out of the repository."""
    return _EMAIL.sub("<email>", _PHONE.sub("<sđt>", text or ""))


def _load(args) -> List[Dict]:
    if args.file:
        body = json.loads(Path(args.file).read_text(encoding="utf-8"))
    else:
        import httpx

        response = httpx.get(
            f"{args.api.rstrip('/')}/admin/ai-quality",
            params={"days": args.days},
            headers={"Authorization": f"Bearer {args.token}"},
            timeout=60.0,
        )
        response.raise_for_status()
        body = response.json()
    while isinstance(body, dict) and "data" in body and "recentWrong" not in body:
        body = body["data"]
    return list(body.get("recentWrong") or [])


def render(cases: List[Dict]) -> str:
    lines = [
        '"""Draft cases from answers customers marked wrong. Review each, then move it',
        'into dialogue_cases.py with must_not / expect_any filled in."""',
        "",
        "from dialogue_cases import Dialogue",
        "",
        "DRAFTS = [",
    ]
    for case in cases:
        turns = [t.strip() for t in _scrub(case.get("customerText") or "").lstrip("…").split(" / ") if t.strip()]
        if not turns:
            continue
        lines.append("    Dialogue(")
        lines.append(f"        device={json.dumps(case.get('deviceName') or '', ensure_ascii=False)},  # đổi sang mã thiết bị")
        lines.append(f"        turns={json.dumps(turns, ensure_ascii=False)},")
        lines.append("        must_not=[],  # điền theo góp ý")
        lines.append("        expect_any=[],")
        note = _scrub(case.get("note") or "")
        reply = _scrub(case.get("reply") or "")
        lines.append(f"        note={json.dumps(('Khách góp ý: ' + note + ' | Trả lời bị chê: ' + reply)[:400], ensure_ascii=False)},")
        lines.append("    ),")
    lines.append("]")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--file", default="")
    args = parser.parse_args()
    if not args.file and not (args.api and args.token):
        raise SystemExit("Cần --file, hoặc --api và --token của tài khoản admin.")
    cases = _load(args)
    OUT.write_text(render(cases), encoding="utf-8")
    print(f"{len(cases)} câu trả lời bị báo chưa đúng -> {OUT.name}")


if __name__ == "__main__":
    main()
