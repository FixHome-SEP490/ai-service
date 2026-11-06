"""Freestyle test: a simulated customer talks to the chat brain until it concludes.

    python tools/sim_chat2.py --base-url http://host:port/v1 --model m --api-key k --out sim.json --md sim.md

The scenarios (tools/chat2_freestyle.py) each hide a truth. The customer is
played by the served model with one instruction: answer the assistant's
question using only the scenario's facts, briefly, the way a person would,
and say "không rõ" to anything the facts do not cover. The assistant is never
told the truth. Every conversation is scored on what a customer would judge:

    right        the final answer names an acceptable fault and service
    turns        assistant turns until the conclusion
    asked_again  a question repeated, or a question about something already said
    safety       for a dangerous fault, the reply opens with the safe step
    length       characters of each assistant reply

and each failure is filed under the layer that caused it (see `classify`), so
the report says where the reasoning breaks, not only how often.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from app.services.chat2.brain import ChatBrain, Turn  # noqa: E402
from app.services.chat2.menu import menu_for  # noqa: E402
from chat2_freestyle import S as SCENARIOS  # noqa: E402

MAX_TURNS = 4

CUSTOMER = """Bạn đóng vai một khách hàng đang nhắn tin với trợ lý của dịch vụ sửa chữa FixHome.
Những điều bạn biết về chiếc máy, và CHỈ những điều này:
{facts}

Trợ lý vừa hỏi bạn. Trả lời ngắn như người thật nhắn tin (dưới 20 chữ), không giải thích thêm.
Nếu câu hỏi không nằm trong những điều bạn biết, trả lời "không rõ" hoặc "em không để ý".
Không tự đoán bệnh, không nhắc lại toàn bộ câu chuyện."""


async def customer_reply(client: httpx.AsyncClient, args, facts: List[str], question: str) -> str:
    body = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": CUSTOMER.format(facts="\n".join(f"- {f}" for f in facts) or "- (không biết gì thêm)")},
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 60,
        **(json.loads(args.extra) if args.extra else {}),
    }
    r = await client.post(args.base_url.rstrip("/") + "/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {args.api_key}"}, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip().split("\n")[0][:200]


def classify(s: Dict[str, Any], final, turns: List[Dict[str, Any]]) -> List[str]:
    """The layer each failure belongs to. Empty when the conversation went right."""
    truth = s["truth"]
    problems: List[str] = []
    if truth.get("decision") == "not_repair":
        return [] if final.decision == "not_repair" else ["scope: answered an out-of-scope request"]
    if final.decision == "not_repair":
        return ["scope: declined a household repair"]
    if s["device"] is None and final.device_type is None:
        problems.append("routing: no appliance found")
    booked = [final.service_code] + [o.service_code for o in final.others]
    faults = [final.fault_code] + [o.fault_code for o in final.others]
    want_faults = truth.get("fault")
    want_services = truth.get("service") or ()
    if want_faults is None:
        if final.fault_code:
            problems.append(f"reasoning: named {final.fault_code} where no catalogue fault applies")
    elif not set(faults) & set(want_faults):
        if final.fault_code is None and set(booked) & set(want_services):
            # The right service with no fault named: books the right technician.
            problems.append("detail: right service, fault not named")
        else:
            menu = menu_for(final.device_type) if final.device_type else None
            known = bool(menu and any(f.code in want_faults for f in menu.faults))
            problems.append(("reasoning" if known else "routing") + f": fault {final.fault_code}, wanted {'/'.join(want_faults)}")
    if want_services and not set(booked) & set(want_services):
        problems.append(f"service: {final.service_code}, wanted {'/'.join(want_services)}")
    if len(want_services) > 1 and "multi_device" in s["tags"] and not set(want_services) <= set(booked):
        problems.append(f"routing: booked {booked}, wanted all of {'/'.join(want_services)}")
    if final.decision != "conclude":
        problems.append("dialogue: never concluded")
    asked = [t["bot"] for t in turns if t["decision"] == "ask"]
    if len(set(asked)) < len(asked):
        problems.append("dialogue: asked the same question twice")
    if "vague" not in s["tags"] and asked:
        problems.append("dialogue: asked although the opening described the problem")
    if "vague" in s["tags"] and not asked:
        problems.append("dialogue: concluded on a message that described nothing")
    if any(len(t["bot"]) > 320 for t in turns):
        problems.append("style: reply over 320 characters")
    menu = menu_for(final.device_type) if final.device_type else None
    fault = menu.fault(final.fault_code) if menu else None
    if fault and fault.urgency == "HIGH" and not final.reply_vi.startswith("Trước tiên"):
        problems.append("safety: dangerous fault without the safe step first")
    return problems


async def run_one(client, brain: ChatBrain, args, s: Dict[str, Any]) -> Dict[str, Any]:
    history = [Turn("user", s["opening"])]
    turns: List[Dict[str, Any]] = []
    final = None
    for _ in range(MAX_TURNS):
        v = await brain.turn(client, history, s["device"])
        turns.append({"customer": history[-1].text, "bot": v.reply_vi, "decision": v.decision,
                      "fault": v.fault_code, "service": v.service_code, "options": v.options_vi,
                      "need": v.need_vi, "kind": v.need_kind, "device": v.device_type,
                      "others": [(o.device_type, o.fault_code, o.service_code, o.reply_vi) for o in v.others],
                      "latency": round(v.latency_s, 2)})
        final = v
        if v.decision != "ask":
            break
        history.append(Turn("assistant", v.reply_vi))
        history.append(Turn("user", await customer_reply(client, args, s["facts"], v.reply_vi)))
    problems = classify(s, final, turns)
    return {"id": s["id"], "tags": s["tags"], "truth": s["truth"], "turns": turns, "problems": problems,
            "right": not [p for p in problems if p.split(":")[0] in ("reasoning", "routing", "scope", "service")]}


async def main_async(args) -> Dict[str, Any]:
    brain = ChatBrain(args.base_url, args.model, args.api_key, timeout_s=90,
                      extra_body=json.loads(args.extra) if args.extra else None)
    sem = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient() as client:
        async def guarded(s):
            async with sem:
                try:
                    return await run_one(client, brain, args, s)
                except Exception as exc:
                    return {"id": s["id"], "tags": s["tags"], "turns": [], "right": False,
                            "problems": [f"infra: {type(exc).__name__}: {str(exc)[:120]}"]}
        rows = await asyncio.gather(*(guarded(s) for s in SCENARIOS * args.repeat))
    layers = Counter(p.split(":")[0] for r in rows for p in r["problems"])
    lengths = [len(t["bot"]) for r in rows for t in r["turns"]]
    summary = {
        "scenarios": len(rows),
        "right": round(sum(r["right"] for r in rows) / len(rows), 3),
        "clean": round(sum(not r["problems"] for r in rows) / len(rows), 3),
        "turns_mean": round(statistics.mean(len(r["turns"]) for r in rows if r["turns"]), 2),
        "reply_chars_p50": int(statistics.median(lengths)) if lengths else 0,
        "problems_by_layer": dict(layers.most_common()),
        "by_tag": {t: round(statistics.mean(r["right"] for r in rows if t in r["tags"]), 2)
                   for t in sorted({t for r in rows for t in r["tags"]})},
    }
    return {"summary": summary, "rows": rows}


def markdown(report: Dict[str, Any]) -> str:
    out = ["# Freestyle chat test", "", "```", json.dumps(report["summary"], ensure_ascii=False, indent=1), "```", ""]
    for r in sorted(report["rows"], key=lambda r: (r["right"], r["id"])):
        out.append(f"## {'OK' if r['right'] else 'SAI'} {r['id']} ({', '.join(r['tags'])})")
        for p in r["problems"]:
            out.append(f"- **{p}**")
        for t in r["turns"]:
            out.append(f"> Khách: {t['customer']}")
            out.append(f"> Bot [{t.get('device')} {t.get('kind')} {t['decision']} {t['fault']} {t['service']}]: {t['bot']}" + (f" {t['options']}" if t["options"] else ""))
            for other in t.get("others") or []:
                out.append(f">   + [{other[0]} {other[1]} {other[2]}]: {other[3]}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default="EMPTY")
    p.add_argument("--extra", default="")
    p.add_argument("--concurrency", type=int, default=12)
    p.add_argument("--repeat", type=int, default=1, help="run every scenario this many times (the customer varies)")
    p.add_argument("--out")
    p.add_argument("--md")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = asyncio.run(main_async(args))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
