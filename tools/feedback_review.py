"""Learn from what customers marked wrong: pull, review, teach, keep as a regression case.

    python tools/feedback_review.py pull --api https://api.fixhome.sbs --email admin@... --days 30 --out review.json
    (a person opens review.json, writes the right fault code in "fault" and sets "approve": true)
    python tools/feedback_review.py apply review.json
    python tools/feedback_review.py check

PO 26/10/2026: the customers' own words are the one source of phrasings the
generated sentences cannot replace. The web shows "Đúng ý / Chưa đúng" under
every answer and Backend keeps the verdict (GET /admin/ai-quality lists the
latest twenty marked wrong, with what the customer had said).

`pull` turns them into a review file, each with what the assistant answers
today. `apply` takes only the reviewed ones (approve true, a fault code that
exists): their words go into app/data/learned_phrasings.json through
tools/learn_phrasings.py, which refuses anything from the test half of the
understanding bank, and each becomes a case in tools/feedback_cases.json.
`check` runs every case: the fault a person settled on has to be among the
three the assistant names. tests/test_feedback_cases.py runs the same check
in CI, so a fault taught once is not lost again.

The password is read from the environment (FIXHOME_ADMIN_PASSWORD) when not
given, so it does not end up in shell history.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tools" / "feedback_cases.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _pipeline():
    sys.path.insert(0, str(ROOT))
    logging.disable(logging.WARNING)
    from app.services.pipeline import service_catalog as sc
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm

    class _NoDetector:
        async def detect(self, image):
            return []

    kb = get_knowledge_base()
    sc.install(sc.LiveCatalog())
    return LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb), kb


def answer_now(pipeline, text: str) -> dict:
    """What the assistant (retrieval and rules, no model) makes of the words today."""
    from app.schemas.diagnosis import DiagnosisRequest

    reply = asyncio.run(pipeline.diagnose(DiagnosisRequest(description=text[:2000])))
    ranked = [f.fault_code for f in reply.suspected_faults]
    if len(ranked) < 3:
        session = pipeline._conversations.get_or_create(reply.session_id)
        device = session.device_type
        if device:
            ranked += [c.fault.fault_code for c in pipeline._retriever.candidate_faults(text, device, 5) if c.fault.fault_code not in ranked]
    return {"device": reply.device.device_type if reply.device else pipeline._conversations.get_or_create(reply.session_id).device_type, "faults": ranked[:3]}


def pull(args) -> None:
    import httpx

    password = args.password or os.environ.get("FIXHOME_ADMIN_PASSWORD", "")
    if not password:
        raise SystemExit("Password: --password or FIXHOME_ADMIN_PASSWORD")
    base = args.api.rstrip("/") + "/api/v1"
    with httpx.Client(timeout=30) as client:
        login = client.post(f"{base}/auth/login", json={"identifier": args.email, "password": password})
        login.raise_for_status()
        body = login.json()
        token = (body.get("data") or body).get("accessToken")
        quality = client.get(f"{base}/admin/ai-quality", params={"days": args.days}, headers={"Authorization": f"Bearer {token}"})
        quality.raise_for_status()
        data = quality.json()
    wrong = (data.get("data") or data).get("recentWrong") or []
    pipeline, _kb = _pipeline()
    review = []
    for row in wrong:
        text = (row.get("customerText") or "").strip()
        if not text:
            continue
        review.append({
            "sessionId": row.get("sessionId"),
            "at": row.get("at"),
            "customerText": text,
            "deviceName": row.get("deviceName"),
            "aiReply": row.get("reply"),
            "customerNote": row.get("note"),
            "now": answer_now(pipeline, text),
            "fault": "",
            "approve": False,
        })
    Path(args.out).write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(review)} câu bị báo sai -> {args.out}. Điền 'fault' (mã lỗi đúng) và 'approve': true cho câu đã duyệt.")


def apply(args) -> None:
    pipeline, kb = _pipeline()
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    taken = [r for r in review if r.get("approve") and kb.fault(r.get("fault") or "") is not None]
    skipped = [r for r in review if r.get("approve") and kb.fault(r.get("fault") or "") is None]
    for r in skipped:
        print(f"  bỏ: mã lỗi không có '{r.get('fault')}' cho '{r['customerText'][:60]}'")
    if not taken:
        print("Không có câu nào đã duyệt.")
        return
    phrasings: dict = {}
    for r in taken:
        phrasings.setdefault(r["fault"], []).append(r["customerText"])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(phrasings, handle, ensure_ascii=False)
    subprocess.run([sys.executable, str(ROOT / "tools" / "learn_phrasings.py"), "--add", handle.name], check=True)
    cases = json.loads(CASES.read_text(encoding="utf-8")) if CASES.exists() else {"cases": []}
    known = {c["text"] for c in cases["cases"]}
    for r in taken:
        if r["customerText"] in known:
            continue
        cases["cases"].append({
            "text": r["customerText"],
            "device": kb.fault(r["fault"]).device_type,
            "fault": r["fault"],
            "from": f"phản hồi khách {r.get('at') or ''}".strip(),
        })
    CASES.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(taken)} câu đã dạy và thêm vào {CASES.name}; chạy lại: python tools/feedback_review.py check")


def check(_args=None) -> int:
    if not CASES.exists():
        print("Chưa có ca nào.")
        return 0
    pipeline, _kb = _pipeline()
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    failed = 0
    for c in cases:
        now = answer_now(pipeline, c["text"])
        ok = c["fault"] in now["faults"]
        failed += not ok
        if not ok:
            print(f"  SAI '{c['text'][:70]}' cần {c['fault']}, được {now['faults']}")
    print(f"{len(cases) - failed}/{len(cases)} ca phản hồi khách đúng")
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull")
    p.add_argument("--api", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", default="")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--out", default="review.json")
    a = sub.add_parser("apply")
    a.add_argument("review")
    sub.add_parser("check")
    args = parser.parse_args()
    if args.cmd == "pull":
        pull(args)
    elif args.cmd == "apply":
        apply(args)
    else:
        sys.exit(1 if check(args) else 0)


if __name__ == "__main__":
    main()
