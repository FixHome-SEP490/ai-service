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
    asked_before_last = None
    ranked_before_last: List[str] = []
    for index, turn in enumerate(dialogue.turns):
        last = index == len(dialogue.turns) - 1
        if last and response is not None:
            led = [f.fault_code for f in getattr(response, "suspected_faults", []) or []]
            led_before_last = led[0] if led else None
            clarification = getattr(response, "clarification", None)
            asked = getattr(clarification, "questions_vi", None) or []
            asked_before_last = asked[0] if asked else None
            # What the conversation pointed to before the last turn, so a "no"
            # can be checked against it: the next guess must come from here.
            held = pipeline._conversations.get_or_create(session)
            state = getattr(held, "state", None)
            try:
                before = pipeline._retriever.candidate_faults(
                    held.symptom_text(), held.device_type or dialogue.device, 5,
                    state.excluded_codes() or None if state else None,
                    state.factors() if state is not None and hasattr(state, "factors") else None,
                )
            except TypeError:
                before = pipeline._retriever.candidate_faults(held.symptom_text(), held.device_type or dialogue.device, 5)
            ranked_before_last = [c.fault.fault_code for c in before]
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
    top = faults[0] if faults else (ranked_codes[0] if ranked_codes else None)
    message = getattr(response, "message_vi", None) or getattr(response, "answer_vi", None) or ""

    # What else a conversation has to get right, beyond what was ruled out.
    checks: Dict[str, Optional[bool]] = {}
    if getattr(dialogue, "deny_last", False) and led_before_last and not getattr(dialogue, "expect_top3", None):
        # "Không phải đâu" and nothing else: the next guess is the next thing
        # the conversation already pointed to, not something new.
        nexts = [c for c in ranked_before_last if c != led_before_last][:3]
        if nexts and top:
            checks["next_guess"] = top in nexts
    if getattr(dialogue, "keep_top", False) and led_before_last:
        checks["keep_top"] = top == led_before_last
    if getattr(dialogue, "expect_device", ""):
        checks["device"] = chat.device_type == dialogue.expect_device and (
            top is None or kb.fault(top) is None or kb.fault(top).device_type == dialogue.expect_device
        )
    if getattr(dialogue, "expect_top3", None):
        checks["top3"] = bool(set(dialogue.expect_top3) & (set(faults) | set(ranked_codes[:3])))
    if getattr(dialogue, "expect_urgent", False):
        urgency = getattr(response, "urgency", None)
        checks["urgent"] = getattr(urgency, "value", urgency) == "HIGH"
    if getattr(dialogue, "answers", "") and asked_before_last:
        # Which faults the answer favours, from the same table the question came from.
        device = chat.device_type or dialogue.device
        wanted = set()
        for entry in kb.discriminators_for_device(device):
            if entry.question_vi.strip() == asked_before_last.strip():
                wanted = set(entry.favours_if_yes if dialogue.answers == "yes" else entry.favours_if_no)
        symptom = None
        if not wanted and asked_before_last.startswith("Thiết bị có hiện tượng "):
            symptom = asked_before_last[len("Thiết bị có hiện tượng "):].rstrip("?").rsplit(" không", 1)[0]
        lead = ranked_codes[0] if ranked_codes else None
        if wanted:
            in_play = wanted & {f.fault_code for f in kb.faults_for_device(device)}
            if in_play and lead:
                checks["answer"] = lead in in_play
        elif symptom and lead:
            has = symptom in (kb.fault(lead).symptoms_vi if kb.fault(lead) else [])
            checks["answer"] = has if dialogue.answers == "yes" else not has
    if getattr(dialogue, "expect_status", ""):
        status = getattr(response, "status", None)
        status = getattr(status, "value", status)
        if dialogue.expect_status == "refused":
            from app.core.config import settings

            asked = getattr(getattr(response, "clarification", None), "questions_vi", None) or []
            checks["status"] = settings.OUT_OF_SCOPE_MESSAGE_VI in [message, *asked]
        else:
            checks["status"] = status == dialogue.expect_status

    must_not = set(dialogue.must_not)
    if getattr(dialogue, "deny_last", False):
        if led_before_last is None:
            return None  # nothing was named, so there is nothing to deny
        try:
            from app.services.pipeline.dialogue_state import never_excluded_codes

            if led_before_last in never_excluded_codes():
                return None  # a safety fault is never ruled out by a sentence, by design
            if led_before_last in set(getattr(dialogue, "expect_top3", None) or []):
                return None  # the hint names the fault the answer already led with
        except ImportError:
            pass
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
        "checks": checks,
        "checks_ok": None if not checks else all(checks.values()),
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
    good = sum(1 for v in scored if v) if key in ("leader_ok", "heard", "checks_ok") else sum(
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
    print(f"{'giữ mạch hội thoại (loại mới)':36s} {_rate(rows, 'checks_ok')}")
    kinds: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for name, ok in row["checks"].items():
            kinds[name]["n"] += 1
            kinds[name]["ok"] += int(bool(ok))
    for name in sorted(kinds):
        c = kinds[name]
        print(f"  {name:34s} {c['ok']}/{c['n']} {100 * c['ok'] / c['n']:5.1f}%")

    by: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for label in ("category", "style", "region", "persona"):
            key = f"{label}:{row[label] or '-'}"
            by[key]["n"] += 1
            by[key]["bad"] += int(bool(row["repeated"] or row["wrongly_excluded"] or row["checks_ok"] is False))
    print("\ntheo loại / kiểu gõ / vùng miền / tính cách (sai = lặp lỗi đã loại hoặc loại nhầm):")
    for key in sorted(by):
        c = by[key]
        print(f"  {key:40s} {c['bad']:5d}/{c['n']:<6d} {100 * (1 - c['bad'] / c['n']):5.1f}% đúng")

    failures = [
        r for r in rows
        if r["repeated"] or r["service_bad"] or r["leader_ok"] is False or r["wrongly_excluded"]
        or r["checks_ok"] is False
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
                ("MẠCH: " + ",".join(k for k, v in row["checks"].items() if not v), row["checks_ok"] is False),
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
