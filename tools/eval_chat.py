"""Score the advisory chatbot against a fixed question set.

Two numbers, and the second matters more than people expect.

Retrieval accuracy asks whether the right policy passage was found. Refusal
accuracy asks whether the questions no document covers were declined. A bot
that answers everything scores full marks on the first and zero on the second,
and that bot is the one that invents a warranty term nobody wrote.

    python tools/eval_chat.py retrieval          # no model needed
    python tools/eval_chat.py end-to-end --url http://127.0.0.1:8000

`retrieval` runs offline against the knowledge base, so it can be part of every
change. `end-to-end` needs the service running with a real model behind it and
measures what a customer would actually receive.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "tests" / "data" / "chat_eval.json"


def load_cases() -> List[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def _summarise(rows: List[dict]) -> Dict[str, float]:
    answerable = [r for r in rows if r["expect"] == "answer"]
    refusable = [r for r in rows if r["expect"] == "refuse"]
    return {
        "answer_correct": sum(1 for r in answerable if r["pass"]),
        "answer_total": len(answerable),
        "refuse_correct": sum(1 for r in refusable if r["pass"]),
        "refuse_total": len(refusable),
    }


def _report(rows: List[dict], title: str) -> None:
    failures = [r for r in rows if not r["pass"]]
    stats = _summarise(rows)

    print(f"\n{title}")
    print(
        f"  answerable  {stats['answer_correct']}/{stats['answer_total']}"
        f"   refusals  {stats['refuse_correct']}/{stats['refuse_total']}"
    )

    if failures:
        print("\n  Failures:")
        for row in failures:
            print(f"    {row['id']}  {row['question']}")
            print(f"       {row['note']}")
    else:
        print("  No failures.")

    # Called out separately: an answer that should have been a refusal is the
    # failure that reaches a customer as a confident invention.
    wrong_answers = [
        r for r in failures if r["expect"] == "refuse"
    ]
    if wrong_answers:
        print(
            f"\n  {len(wrong_answers)} question(s) outside the documents were answered"
            " anyway. Those are inventions, not gaps."
        )


def cmd_retrieval(args: argparse.Namespace) -> None:
    """Offline: did retrieval find the right passage, and nothing for the rest?"""
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.retriever import Retriever

    retriever = Retriever(get_knowledge_base())
    rows: List[dict] = []

    for case in load_cases():
        hits = retriever.policy_passages(case["question"], top_k=args.top_k)
        found = [h.policy.doc_id for h in hits]

        if case["expect"] == "answer":
            wanted = set(case["expect_docs"])
            ok = bool(wanted & set(found))
            note = f"expected one of {sorted(wanted)}, retrieved {found or 'nothing'}"
        else:
            # Refusal is judged on grounding, not on the model: retrieving
            # nothing is what makes the pipeline decline.
            ok = not found
            note = f"retrieved {found}, expected nothing"

        rows.append({**case, "pass": ok, "note": note, "found": found})

    _report(rows, f"Retrieval only, top_k={args.top_k}")

    if args.verbose:
        print("\n  Every case:")
        for row in rows:
            mark = "ok  " if row["pass"] else "FAIL"
            print(f"    {mark} {row['id']}  {row['found']}")


def cmd_end_to_end(args: argparse.Namespace) -> None:
    """Against the running service, so it measures what a customer receives."""
    import httpx

    rows: List[dict] = []
    for case in load_cases():
        try:
            response = httpx.post(
                f"{args.url.rstrip('/')}/api/v1/chat/ask",
                json={"question": case["question"]},
                timeout=args.timeout,
            )
            body = response.json()
        except httpx.HTTPError as exc:
            rows.append(
                {**case, "pass": False, "note": f"request failed: {type(exc).__name__}"}
            )
            continue

        status = body.get("status")
        answered = status == "ok" and bool(body.get("answerVi"))
        cited = [c["docId"] for c in body.get("citations", [])]

        if case["expect"] == "answer":
            ok = answered and bool(set(case["expect_docs"]) & set(cited))
            note = f"status={status}, cited {cited or 'nothing'}"
        else:
            ok = not answered
            note = f"status={status}, answered={answered}, cited {cited}"

        rows.append({**case, "pass": ok, "note": note})

    _report(rows, f"End to end against {args.url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    retrieval = sub.add_parser("retrieval", help="offline, no model required")
    retrieval.add_argument("--top-k", type=int, default=3)
    retrieval.add_argument("--verbose", action="store_true")

    e2e = sub.add_parser("end-to-end", help="against the running service")
    e2e.add_argument("--url", default="http://127.0.0.1:8000")
    e2e.add_argument("--timeout", type=float, default=30.0)

    args = parser.parse_args()
    {"retrieval": cmd_retrieval, "end-to-end": cmd_end_to_end}[args.command](args)


if __name__ == "__main__":
    main()
