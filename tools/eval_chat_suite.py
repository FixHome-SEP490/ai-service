"""Run every case in chat_cases.py against the live service and score it.

The point is not a number. It is the list at the bottom of what went wrong and
in which direction, because the two failures are not equally bad.

Answering when it should have asked is the expensive one: a confident fault and
a price, off the back of a sentence that settled nothing, is a wrong answer the
customer acts on. Asking when it should have answered is merely annoying.

    python -m uvicorn app.main:app --port 8000
    python tools/eval_chat_suite.py
    python tools/eval_chat_suite.py --only diagnose --show-replies

Each case runs in its own session, so nothing leaks between them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from chat_cases import CASES, Case  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8000")


def _device_of(fault_codes: List[str]) -> str | None:
    """Which appliance the chosen faults belong to."""
    from app.services.pipeline.knowledge_base import get_knowledge_base

    kb = get_knowledge_base()
    for code in fault_codes:
        fault = kb.fault(code)
        if fault is not None:
            return fault.device_type
    return None


def _classify(case: Case, result: Dict[str, Any]) -> str:
    """What the service actually did, in the same vocabulary as `expect`."""
    if "code" in result:
        return "error"

    status = result.get("status")
    if status == "ok" and result.get("suspectedFaults"):
        return "diagnose"
    if status == "needs_clarification":
        questions = (result.get("clarification") or {}).get("questionsVi") or []
        first = questions[0] if questions else ""
        # The out-of-scope reply travels as a clarification because the contract
        # has nowhere else to put a sentence. It is not a question.
        if "chỉ hỗ trợ được các vấn đề" in first:
            return "refuse"
        if result.get("device") and "đang gặp vấn đề gì" in first:
            return "identify"
        return "ask"
    if status in ("ok", "general_knowledge"):
        return "answer"
    if status == "no_grounding":
        return "refuse"
    return status or "unknown"


def _ask(case: Case) -> Dict[str, Any]:
    if case.expect == "answer":
        # Price and policy questions are the advisory surface. Sending them to
        # diagnosis is a routing decision the client makes, and this measures
        # the service, not the client.
        response = httpx.post(
            f"{SERVICE_URL}/api/v1/chat/ask",
            json={"question": case.text},
            timeout=180.0,
        )
        body = response.json()
        # Normalise so one classifier handles both surfaces.
        return {"status": body.get("status"), "answerVi": body.get("answerVi", "")}

    response = httpx.post(
        f"{SERVICE_URL}/api/v1/diagnosis/analyze-upload",
        data={"description": case.text},
        timeout=180.0,
    )
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="run one expectation: diagnose, ask, answer, refuse")
    parser.add_argument("--show-replies", action="store_true")
    parser.add_argument("--out", default="docs/chat-suite-results.json")
    args = parser.parse_args()

    cases = [c for c in CASES if not args.only or c.expect == args.only]
    print(f"{len(cases)} ca, gọi {SERVICE_URL}\n")

    rows: List[Dict[str, Any]] = []
    started = time.perf_counter()

    for index, case in enumerate(cases, start=1):
        try:
            result = _ask(case)
        except httpx.HTTPError as exc:
            result = {"code": "TRANSPORT", "message": str(exc)}

        got = _classify(case, result)
        ok = got == case.expect

        # The reported device is only ever one a photograph established, by
        # design, so a text-only diagnosis always reports none. Reading it from
        # the fault codes is what the service actually decided: scoring the
        # empty field marked all 52 correct diagnoses as the wrong appliance.
        device = (result.get("device") or {}).get("deviceType") or _device_of(
            [f["faultCode"] for f in result.get("suspectedFaults") or []]
        )
        device_ok = case.device is None or device == case.device
        faults = [f["faultCode"] for f in result.get("suspectedFaults") or []]
        fault_ok = not case.faults_any or any(f in case.faults_any for f in faults)

        rows.append(
            {
                "text": case.text,
                "expect": case.expect,
                "got": got,
                "ok": ok,
                "device_expected": case.device,
                "device_got": device,
                "device_ok": device_ok,
                "faults": faults,
                "fault_ok": fault_ok,
                "note": case.note,
                "reply": result.get("messageVi") or result.get("answerVi") or "",
            }
        )

        mark = "." if ok else "x"
        print(mark, end="", flush=True)
        if index % 40 == 0:
            print()

    elapsed = time.perf_counter() - started
    print(f"\n\n{elapsed:.0f}s\n")

    by_expect: Counter = Counter()
    right: Counter = Counter()
    for row in rows:
        by_expect[row["expect"]] += 1
        if row["ok"]:
            right[row["expect"]] += 1

    print(f"{'mong đợi':<12}{'đúng':>6}{'tổng':>6}")
    for kind in sorted(by_expect):
        print(f"{kind:<12}{right[kind]:>6}{by_expect[kind]:>6}")
    total_ok = sum(right.values())
    print(f"{'tất cả':<12}{total_ok:>6}{len(rows):>6}   {total_ok / len(rows):.0%}")

    wrong_device = [r for r in rows if r["ok"] and not r["device_ok"]]
    wrong_fault = [r for r in rows if r["ok"] and r["device_ok"] and not r["fault_ok"]]

    # Answering when it should have asked is the expensive direction: a
    # confident fault and a price off a sentence that settled nothing is a wrong
    # answer the customer acts on. Asking when it should have answered is merely
    # annoying, so the two are counted apart.
    over = [r for r in rows if not r["ok"] and r["expect"] == "ask" and r["got"] == "diagnose"]
    under = [r for r in rows if not r["ok"] and r["expect"] == "diagnose" and r["got"] == "ask"]
    refused = [r for r in rows if not r["ok"] and r["got"] == "refuse"]
    leaked = [r for r in rows if not r["ok"] and r["expect"] == "refuse"]

    for title, group in [
        ("ĐOÁN BỪA khi đáng lẽ phải hỏi", over),
        ("HỎI LẠI khi đáng lẽ trả lời được", under),
        ("TỪ CHỐI oan", refused),
        ("KHÔNG TỪ CHỐI câu ngoài phạm vi", leaked),
        ("Đúng loại nhưng SAI THIẾT BỊ", wrong_device),
        ("Đúng thiết bị nhưng SAI BỆNH", wrong_fault),
    ]:
        if not group:
            continue
        print(f"\n{title} ({len(group)})")
        for row in group[:12]:
            detail = f" -> {row['device_got']}" if not row["device_ok"] else ""
            if not row["fault_ok"] and row["faults"]:
                detail = f" -> {', '.join(row['faults'][:2])}"
            print(f"  {row['text'][:58]:<60}{detail}")
            if args.show_replies and row["reply"]:
                print(f"      {row['reply'][:160]}")

    Path(args.out).write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nChi tiết: {args.out}")


if __name__ == "__main__":
    main()
