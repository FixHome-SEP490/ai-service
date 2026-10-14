"""Score multi-turn conversations against the real pipeline, without a model.

    python tools/eval_dialogue.py                      # hand-written dialogues
    python tools/eval_dialogue.py --generated 20000    # plus generated ones
    python tools/eval_dialogue.py --app-root ../other  # score another checkout

Every dialogue runs in its own session through `LocalPipeline` with the stub
detector and stub language model, so what is measured is everything the team
controls: reading the conversation, retrieval, ranking and the services
offered. The appliance is seeded as if a photograph had identified it, which is
how the case that started this arrived, unless the dialogue says otherwise.

Five numbers, in order of how much they matter:

    repeated     the final answer named a fault the customer had ruled out.
                 The failure this exists for. Target: zero.

    kept         the customer said something that is not an exclusion ("chưa
                 vệ sinh", "có nên vệ sinh không", a new symptom) and the
                 service ruled a fault out anyway. The opposite failure, and
                 the one an over-eager fix for the first would cause.

    service      the services offered still belong only to ruled-out faults,
                 so the customer is sent to book the thing they denied.

    leader       where the dialogue says which faults are right once the
                 ruled-out ones are gone, whether retrieval's leader is one.

    heard        when the last turn ruled something out, whether the reply
                 said so ("... nên em loại khả năng ... ra ạ").

`--app-root` points the scorer at another checkout of this repository, so the
same dialogues can be run against the code before a change and after it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _bootstrap(app_root: Path) -> None:
    sys.path.insert(0, str(TOOLS))
    sys.path.insert(0, str(app_root))


class _NoDetector:
    async def detect(self, image):
        return []


async def _run_one(pipeline, kb, dialogue, ChatRequest, DiagnosisRequest) -> Optional[Dict[str, Any]]:
    chat = pipeline._conversations.get_or_create(None)
    if getattr(dialogue, "seed_device", True):
        chat.remember_device(dialogue.device, 0.9, "image")
    session = chat.session_id
    response = None
    led_before_last = None
    for index, turn in enumerate(dialogue.turns):
        last = index == len(dialogue.turns) - 1
        if last and response is not None:
            led = [f.fault_code for f in getattr(response, "suspected_faults", []) or []]
            led_before_last = led[0] if led else None
        if last and dialogue.via == "ask":
            response = await pipeline.answer(ChatRequest(question=turn, sessionId=session))
        else:
            response = await pipeline.diagnose(DiagnosisRequest(description=turn, sessionId=session))
        session = response.session_id or session

    chat = pipeline._conversations.get_or_create(session)
    state = getattr(chat, "state", None)
    excluded = state.excluded_codes() if state is not None else set()
    factors = state.factors() if state is not None and hasattr(state, "factors") else None
    device = chat.device_type or dialogue.device
    try:
        ranked = pipeline._retriever.candidate_faults(
            chat.symptom_text(), device, 5, excluded or None, factors
        )
    except TypeError:  # the code before the change takes no exclusions
        ranked = pipeline._retriever.candidate_faults(chat.symptom_text(), device, 5)
    ranked_codes = [c.fault.fault_code for c in ranked]

    faults = [f.fault_code for f in getattr(response, "suspected_faults", []) or []]
    services = [s.service_code for s in getattr(response, "recommended_services", []) or []]
    message = getattr(response, "message_vi", None) or getattr(response, "answer_vi", None) or ""

    must_not = set(dialogue.must_not)
    if getattr(dialogue, "deny_last", False):
        if led_before_last is None:
            return None  # nothing was named, so there is nothing to deny
        must_not.add(led_before_last)
    repeated = bool(must_not & set(faults)) or bool(ranked_codes and ranked_codes[0] in must_not)

    denied_services = {
        ref.service_code for code in must_not for ref in kb.services_for_fault(code)
    }
    allowed_services = {
        ref.service_code
        for code in ranked_codes[:3]
        if code not in must_not
        for ref in kb.services_for_fault(code)
    }
    service_bad = bool(services) and all(
        s in denied_services and s not in allowed_services for s in services
    )

    leader_ok = None
    if dialogue.expect_any:
        top = faults[0] if faults else (ranked_codes[0] if ranked_codes else None)
        leader_ok = top in set(dialogue.expect_any)

    heard = None
    if must_not:
        heard = "loại khả năng" in message

    # A false exclusion: the customer said "chưa vệ sinh", or asked whether to,
    # or added a symptom, and the service read it as ruling a fault out.
    must_keep = set(getattr(dialogue, "must_keep", None) or [])
    wrongly_excluded = bool(must_keep & set(excluded)) if must_keep else None

    return {
        "turns": dialogue.turns,
        "device": dialogue.device,
        "via": dialogue.via,
        "category": getattr(dialogue, "category", "") or "viết tay",
        "persona": dialogue.persona,
        "region": dialogue.region,
        "style": dialogue.style,
        "must_not": sorted(must_not),
        "must_keep": sorted(must_keep),
        "excluded": sorted(excluded),
        "faults": faults,
        "ranked": ranked_codes,
        "services": services,
        "message": message,
        "repeated": repeated,
        "wrongly_excluded": wrongly_excluded,
        "service_bad": service_bad,
        "leader_ok": leader_ok,
        "heard": heard,
        "note": dialogue.note,
    }


async def run_dialogues(dialogues, app_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    from app.schemas.chat import ChatRequest
    from app.schemas.diagnosis import DiagnosisRequest
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm

    kb = get_knowledge_base()
    pipeline = LocalPipeline(
        detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb
    )
    rows = []
    for dialogue in dialogues:
        row = await _run_one(pipeline, kb, dialogue, ChatRequest, DiagnosisRequest)
        if row is not None:
            rows.append(row)
        # Sessions are kept in memory; tens of thousands of them are not the
        # point of this run.
        conversations = getattr(pipeline._conversations, "_sessions", None)
        if isinstance(conversations, dict) and len(conversations) > 500:
            conversations.clear()
    return rows


def _rate(rows, key) -> str:
    scored = [r[key] for r in rows if r[key] is not None]
    if not scored:
        return "   -"
    good = sum(1 for v in scored if v) if key in ("leader_ok", "heard") else sum(
        1 for v in scored if not v
    )
    return f"{good}/{len(scored)} {100 * good / len(scored):5.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", default=str(TOOLS.parent))
    parser.add_argument("--generated", type=int, default=0, help="add this many generated dialogues")
    parser.add_argument("--only-generated", action="store_true")
    parser.add_argument("--seed", type=int, default=20261014)
    parser.add_argument("--out", default="")
    parser.add_argument("--show", type=int, default=25, help="failures to print")
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    _bootstrap(app_root)
    from dialogue_cases import DIALOGUES

    dialogues = [] if args.only_generated else list(DIALOGUES)
    if args.generated:
        from dialogue_corpus import generate

        dialogues += generate(limit=args.generated, seed=args.seed)

    started = time.time()
    rows = asyncio.run(run_dialogues(dialogues, app_root))
    elapsed = time.time() - started

    print(f"\n{len(rows)} hội thoại, {elapsed:.0f}s, mã nguồn: {app_root}\n")
    print(f"{'chỉ số':36s} kết quả")
    print(f"{'không lặp lỗi khách đã loại':36s} {_rate(rows, 'repeated')}")
    print(f"{'không loại nhầm (chưa làm, hỏi...)':36s} {_rate(rows, 'wrongly_excluded')}")
    print(f"{'dịch vụ không dính lỗi đã loại':36s} {_rate(rows, 'service_bad')}")
    print(f"{'lỗi đứng đầu đúng':36s} {_rate(rows, 'leader_ok')}")
    print(f"{'có câu ghi nhận lời khách':36s} {_rate(rows, 'heard')}")

    by: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for label in ("category", "style", "region", "persona"):
            key = f"{label}:{row[label] or '-'}"
            by[key]["n"] += 1
            by[key]["bad"] += int(bool(row["repeated"] or row["wrongly_excluded"]))
    print("\ntheo loại / kiểu gõ / vùng miền / tính cách (sai = lặp lỗi đã loại hoặc loại nhầm):")
    for key in sorted(by):
        c = by[key]
        print(f"  {key:40s} {c['bad']:5d}/{c['n']:<6d} {100 * (1 - c['bad'] / c['n']):5.1f}% đúng")

    failures = [
        r for r in rows
        if r["repeated"] or r["service_bad"] or r["leader_ok"] is False or r["wrongly_excluded"]
    ]
    print(f"\nlỗi ({len(failures)}), in {min(args.show, len(failures))}:")
    for row in failures[: args.show]:
        tags = [
            t
            for t, bad in (
                ("LẶP", row["repeated"]),
                ("LOẠI NHẦM", row["wrongly_excluded"]),
                ("DỊCH VỤ", row["service_bad"]),
                ("ĐẦU SAI", row["leader_ok"] is False),
            )
            if bad
        ]
        print(f"  [{', '.join(tags)}] ({row['category']}/{row['region']}/{row['style']}) {row['device']}: {' | '.join(row['turns'])}")
        print(f"      loại={row['must_not']} giữ={row['must_keep']} đã loại={row['excluded']} faults={row['faults'][:3]} ranked={row['ranked'][:3]}")

    if args.out:
        Path(args.out).write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nchi tiết: {args.out}")


if __name__ == "__main__":
    random.seed(0)
    main()
