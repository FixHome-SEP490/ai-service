"""Score the chat brain (app/services/chat2) on one served model.

    python tools/eval_chat2.py --base-url http://host:port/v1 --model <name> --out result.json
    python tools/eval_chat2.py ... --suites scripted,service --show

Suites, all on the test half of understanding_bank.json where the bank is used:

    scripted   tools/chat2_cases.py, conversations customers and the PO reported
    clear      a clear description of one fault, appliance known from a photo:
               should conclude on that fault
    vague      "máy có vấn đề" kinds of message: should ask
    service    the work asked for outright (tools/service_understanding_cases.py)
    offtopic   not a household repair: should decline

Reported per suite: pass rate, and for `clear` also how often it concluded,
how often a conclusion named the wrong fault, median reply length and latency.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from app.services.chat2.brain import ChatBrain, Turn  # noqa: E402
from chat2_cases import CASES as SCRIPTED  # noqa: E402
from eval_understanding import split_of  # noqa: E402
from service_understanding_cases import CASES as SERVICE  # noqa: E402


def _bank() -> dict:
    return json.loads((ROOT / "tools" / "understanding_bank.json").read_text(encoding="utf-8"))


def build(suites: List[str], split: str) -> List[Dict[str, Any]]:
    bank = _bank()
    out: List[Dict[str, Any]] = []
    if "scripted" in suites:
        for c in SCRIPTED:
            out.append({"suite": "scripted", **c})
    if "clear" in suites:
        for device, v in bank["devices"].items():
            for code, kinds in v["faults"].items():
                for kind in ("clear", "indirect"):
                    for phrase in kinds.get(kind, []):
                        if split_of(phrase) != split:
                            continue
                        out.append({
                            "suite": "clear", "id": f"{code}:{kind}", "device": device,
                            "turns": [phrase], "kind": kind,
                            "expect": {"fault": code},
                        })
    if "vague" in suites:
        for device, v in bank["devices"].items():
            for phrase in v.get("vague", []):
                out.append({"suite": "vague", "id": device, "device": device, "turns": [phrase], "expect": {"decision": "ask"}})
    if "service" in suites:
        for text, code in SERVICE:
            out.append({"suite": "service", "id": code, "device": None, "turns": [text], "expect": {"decision": "conclude", "service": code}})
    if "offtopic" in suites:
        for text in bank.get("offtopic", []):
            out.append({"suite": "offtopic", "id": "offtopic", "device": None, "turns": [text], "expect": {"decision": "not_repair"}})
    return out


def _ok(value: Any, want: Any) -> bool:
    if want is None:
        return True
    return value in want if isinstance(want, tuple) else value == want


def judge(case: Dict[str, Any], v) -> Dict[str, Any]:
    e = case["expect"]
    fault = v.fault_code or ("NONE" if v.decision == "conclude" else None)
    if case["suite"] == "clear":
        concluded = v.decision == "conclude"
        right = fault == e["fault"]
        return {"pass": concluded and right, "concluded": concluded, "wrong": concluded and not right}
    if case["suite"] == "offtopic":
        # A bare "alo", "ok" is a greeting: asking what they need is right too.
        return {"pass": v.decision == "not_repair" or (v.intent == "greeting" and not v.device_type)}
    ok = _ok(v.decision, e.get("decision"))
    if ok and "fault" in e and v.decision == "conclude":
        ok = _ok(fault, e["fault"])
    if ok and "service" in e and v.decision == "conclude":
        ok = _ok(v.service_code, e["service"])
    return {"pass": ok}


async def run(args) -> Dict[str, Any]:
    extra = json.loads(args.extra) if args.extra else {}
    brain = ChatBrain(args.base_url, args.model, args.api_key, timeout_s=args.timeout, extra_body=extra, with_cards=not args.no_cards)
    cases = build(args.suites.split(","), args.split)
    sem = asyncio.Semaphore(args.concurrency)
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        async def one(case):
            history = [Turn("user" if i % 2 == 0 else "assistant", t) for i, t in enumerate(case["turns"])]
            async with sem:
                try:
                    v = await brain.turn(client, history, case.get("device"))
                except Exception as exc:  # scored as a failure, reported by kind
                    results.append({**case, "error": type(exc).__name__ + ": " + str(exc)[:200], "pass": False})
                    return
            results.append({
                **case, **judge(case, v), "decision": v.decision, "fault": v.fault_code,
                "service": v.service_code, "reply": v.reply_vi, "booking": v.booking_vi, "options": v.options_vi,
                "latency": round(v.latency_s, 3), "device_out": v.device_type,
            })

        started = time.perf_counter()
        await asyncio.gather(*(one(c) for c in cases))
        wall = time.perf_counter() - started

    summary: Dict[str, Any] = {"model": args.model, "cards": not args.no_cards, "split": args.split, "cases": len(results), "wall_s": round(wall, 1)}
    for suite in sorted({r["suite"] for r in results}):
        rows = [r for r in results if r["suite"] == suite]
        s: Dict[str, Any] = {"n": len(rows), "pass": round(sum(r["pass"] for r in rows) / len(rows), 3)}
        s["errors"] = sum(1 for r in rows if "error" in r)
        if suite == "clear":
            s["concluded"] = round(sum(r.get("concluded", False) for r in rows) / len(rows), 3)
            s["wrong_confident"] = round(sum(r.get("wrong", False) for r in rows) / len(rows), 3)
        summary[suite] = s
    ok_rows = [r for r in results if "error" not in r]
    if ok_rows:
        lat = sorted(r["latency"] for r in ok_rows)
        summary["latency_p50"] = round(statistics.median(lat), 2)
        summary["latency_p95"] = round(lat[int(len(lat) * 0.95) - 1], 2)
        summary["reply_chars_p50"] = int(statistics.median(len(r["reply"]) for r in ok_rows))
        summary["reply_chars_max"] = max(len(r["reply"]) for r in ok_rows)
    return {"summary": summary, "results": sorted(results, key=lambda r: (r["suite"], r["id"]))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default="EMPTY")
    p.add_argument("--suites", default="scripted,clear,vague,service,offtopic")
    p.add_argument("--split", default="test", choices=["dev", "test"])
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--extra", default="", help="JSON merged into each request body")
    p.add_argument("--no-cards", action="store_true", help="leave the fault cards out of the prompt")
    p.add_argument("--out")
    p.add_argument("--show", action="store_true", help="print every scripted reply and every failure")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = asyncio.run(run(args))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=1))
    if args.show:
        for r in report["results"]:
            if r["suite"] == "scripted" or not r["pass"]:
                mark = "OK " if r["pass"] else "FAIL"
                print(f"{mark} [{r['suite']}] {r['id']} :: {r['turns'][-1][:70]}")
                print(f"     -> {r.get('decision')} {r.get('fault')} {r.get('service')} | {r.get('reply', r.get('error', ''))[:260]}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
