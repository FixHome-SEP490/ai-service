"""Run the conversation suite against a running service, with the real model.

`eval_dialogue.py` runs in-process with stub models, which measures everything
the team controls and nothing the model writes. This one talks HTTP to a served
instance - a rented GPU box with Qwen loaded - so it also measures the words:
whether the reply the customer reads brings back what they ruled out.

    AI_SERVICE_URL=http://host:port python tools/eval_dialogue_live.py --generated 300
    python tools/eval_dialogue_live.py --url http://host:port --out run.json

Only what a client can see is scored, from the JSON the service returns:

    repeated     a ruled-out fault among the suspected faults
    said_again   the reply's prose, after the acknowledgement sentence, names a
                 ruled-out fault or repeats the fix the customer already made
    device       the appliance the reply is about, where the dialogue says
    keep_top     the leading fault survived "đúng rồi", "cảm ơn", a question
    urgent       HIGH urgency where danger was described
    refused      an off-topic aside was refused
    next_guess   after "không phải đâu", the new leader was among the faults
                 the previous reply already listed

Every reply is written to --out, so the prose can be read, not just counted.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent))

import httpx  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in lowered if unicodedata.category(c) != "Mn").replace("đ", "d")


def _post(client: httpx.Client, url: str, via: str, text: str, session: Optional[str]) -> Dict[str, Any]:
    if via == "ask":
        body = {"question": text[:1000]}
        path = "/api/v1/chat/ask"
    else:
        body = {"description": text[:2000]}
        path = "/api/v1/diagnosis/analyze"
    if session:
        body["sessionId"] = session
    started = time.time()
    response = client.post(f"{url}{path}", json=body, timeout=180.0)
    reply = response.json() if response.content else {}
    reply["_status_code"] = response.status_code
    reply["_ms"] = int((time.time() - started) * 1000)
    return reply


def _prose(reply: Dict[str, Any]) -> str:
    text = reply.get("messageVi") or reply.get("answerVi") or ""
    # The acknowledgement names the ruled-out fault on purpose; everything after
    # it is what is checked.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s for s in sentences if "loại khả năng" not in s and not s.startswith("Khả năng còn lại"))


def _said_again(kb, cues: Dict[str, dict], must_not: List[str], prose: str) -> bool:
    folded = f" {_fold(prose)} "
    for code in must_not:
        fault = kb.fault(code)
        if fault and f" {_fold(fault.name_vi)} " in folded:
            return True
        for phrase in (cues.get(code) or {}).get("done", []):
            if f" {_fold(phrase)} " in folded:
                return True
    return False


def run(url: str, dialogues, kb, cues) -> List[Dict[str, Any]]:
    from app.core.config import settings

    rows = []
    with httpx.Client() as client:
        for number, dialogue in enumerate(dialogues, start=1):
            session = None
            replies = []
            via_last = dialogue.via
            for index, turn in enumerate(dialogue.turns):
                last = index == len(dialogue.turns) - 1
                via = via_last if last else "diagnose"
                try:
                    reply = _post(client, url, via, turn, session)
                except httpx.HTTPError as error:
                    reply = {"_error": str(error), "_status_code": 0, "_ms": 0}
                replies.append(reply)
                session = reply.get("sessionId") or session
            final = replies[-1]
            before = replies[-2] if len(replies) > 1 else {}
            faults = [f.get("faultCode") for f in final.get("suspectedFaults") or []]
            led_before = [f.get("faultCode") for f in before.get("suspectedFaults") or []]
            must_not = set(dialogue.must_not)
            if dialogue.deny_last and led_before:
                must_not.add(led_before[0])
            checks: Dict[str, bool] = {}
            if must_not:
                checks["repeated"] = not (must_not & set(faults))
                checks["said_again"] = not _said_again(kb, cues, sorted(must_not), _prose(final))
            if dialogue.expect_device:
                device = ((final.get("device") or {}).get("deviceType")) or (
                    kb.fault(faults[0]).device_type if faults and kb.fault(faults[0]) else None
                )
                if device is not None:  # the advisory route names no device
                    checks["device"] = device == dialogue.expect_device
            if dialogue.keep_top and led_before and faults:
                checks["keep_top"] = faults[0] == led_before[0]
            if dialogue.expect_urgent:
                checks["urgent"] = final.get("urgency") == "HIGH"
            if dialogue.expect_status == "refused":
                asked = (final.get("clarification") or {}).get("questionsVi") or []
                checks["refused"] = settings.OUT_OF_SCOPE_MESSAGE_VI in [final.get("answerVi"), *asked]
            if dialogue.deny_last and not dialogue.expect_top3 and len(led_before) > 1 and faults:
                checks["next_guess"] = faults[0] in led_before[1:]
            errors = [r for r in replies if r.get("_status_code") != 200]
            rows.append({
                "category": dialogue.category or "viết tay",
                "device": dialogue.device,
                "region": dialogue.region,
                "style": dialogue.style,
                "turns": dialogue.turns,
                "replies": [
                    {k: r.get(k) for k in ("status", "messageVi", "answerVi", "suspectedFaults", "recommendedServices", "urgency", "clarification", "_status_code", "_ms")}
                    for r in replies
                ],
                "must_not": sorted(must_not),
                "checks": checks,
                "ok": all(checks.values()) and not errors,
                "errors": len(errors),
                "ms": [r.get("_ms", 0) for r in replies],
            })
            if number % 25 == 0:
                done = sum(1 for r in rows if r["ok"])
                print(f"  {number}/{len(dialogues)}  ok {done}", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--generated", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--no-hand-written", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    from app.services.pipeline.knowledge_base import get_knowledge_base
    from dialogue_cases import DIALOGUES
    from dialogue_corpus import generate

    kb = get_knowledge_base()
    cues = json.loads((TOOLS.parent / "app" / "data" / "dialogue_knowledge.json").read_text(encoding="utf-8"))["faults"]
    dialogues = ([] if args.no_hand_written else list(DIALOGUES)) + generate(args.generated, args.seed, interleave=True)
    random.Random(0).shuffle(dialogues)

    started = time.time()
    rows = run(args.url.rstrip("/"), dialogues, kb, cues)
    print(f"\n{len(rows)} hội thoại, {time.time() - started:.0f}s, {args.url}\n")

    kinds: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for name, ok in row["checks"].items():
            kinds[name]["n"] += 1
            kinds[name]["ok"] += int(ok)
    for name in sorted(kinds):
        c = kinds[name]
        print(f"  {name:12s} {c['ok']}/{c['n']}  {100 * c['ok'] / c['n']:5.1f}%")
    ms = sorted(m for r in rows for m in r["ms"] if m)
    if ms:
        print(f"\n  độ trễ mỗi lượt: trung vị {ms[len(ms) // 2]} ms, p95 {ms[int(len(ms) * 0.95)]} ms, lỗi HTTP {sum(r['errors'] for r in rows)}")
    cats: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        cats[row["category"]]["n"] += 1
        cats[row["category"]]["ok"] += int(row["ok"])
    print("\ntheo loại:")
    for name in sorted(cats):
        c = cats[name]
        print(f"  {name:20s} {c['ok']}/{c['n']}")
    if args.out:
        Path(args.out).write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nchi tiết: {args.out}")


if __name__ == "__main__":
    main()
