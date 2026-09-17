"""Score retrieval against the case suite, without a model or a server.

Everything the model can possibly say is decided before the model runs: which
faults were shortlisted, which written passages were pulled, whether a warning
was pinned. Measuring that separately is what makes it possible to change the
retriever at a laptop, in a second, instead of renting a GPU to find out.

    python tools/eval_retrieval.py
    python tools/eval_retrieval.py --show-passages
    python tools/eval_retrieval.py --only pin

Three numbers, and they are not equally important.

    shortlist   did the right fault reach the candidate list
    corpus      did prose from the right file come back
    pin         was the warning pinned, on the cases where missing it is
                irreversible

A missed explanation is a gap. A missed warning is a defect. They are reported
apart so that an average can never hide the second behind the first.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import context as ctxmod  # noqa: E402
from app.services.pipeline.conversation import Conversation  # noqa: E402
from app.services.pipeline.knowledge_base import get_knowledge_base  # noqa: E402
from app.services.pipeline.retriever import Retriever  # noqa: E402
from tools.chat_cases import CASES, Case  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class Result:
    case: Case
    shortlist: List[str]
    passages: List[str]
    business: List[str]
    pinned: Optional[str]

    @property
    def shortlist_ok(self) -> Optional[bool]:
        if not self.case.faults_any:
            return None
        return any(code in self.shortlist for code in self.case.faults_any)

    @property
    def corpus_ok(self) -> Optional[bool]:
        if not self.case.corpus_any:
            return None
        return any(f in self.passages for f in self.case.corpus_any)

    @property
    def business_ok(self) -> Optional[bool]:
        if not self.case.business_any:
            return None
        return any(f in self.business for f in self.case.business_any)

    @property
    def pin_ok(self) -> Optional[bool]:
        if not self.case.pin:
            return None
        return self.pinned == self.case.pin

    @property
    def silence_ok(self) -> Optional[bool]:
        """For out-of-scope messages: nothing at all may come back.

        Retrieving confident prose for "hôm nay ăn gì ngon" is worse than
        retrieving nothing, because everything downstream treats a passage as
        something the answer may be built from.
        """
        if self.case.expect != "refuse" or self.case.device:
            return None
        return not (self.passages or self.pinned)


def run_case(kb, retriever: Retriever, case: Case) -> Result:
    chat = Conversation(session_id="eval")
    chat.add("customer", case.text)
    candidates = (
        retriever.candidate_faults(case.text, case.device, top_k=3)
        if case.device
        else []
    )
    ctx = ctxmod.build(
        kb,
        retriever,
        chat,
        case.text,
        case.device,
        "description",
        candidates,
        has_image=False,
    )
    return Result(
        case=case,
        shortlist=[c.fault.fault_code for c in candidates],
        passages=[h.chunk.source_file for h in ctx.passages],
        business=[h.chunk.source_file for h in ctx.business],
        pinned=ctx.safety[0].chunk.fault_code if ctx.safety else None,
    )


def _rate(values: List[Optional[bool]]) -> str:
    scored = [v for v in values if v is not None]
    if not scored:
        return "     —"
    hits = sum(1 for v in scored if v)
    return f"{hits:>3}/{len(scored):<3} {hits / len(scored):>5.0%}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-passages", action="store_true")
    parser.add_argument(
        "--only",
        choices=["shortlist", "corpus", "business", "pin", "silence"],
        help="only report failures of this kind",
    )
    args = parser.parse_args()

    kb = get_knowledge_base()
    retriever = Retriever(kb)
    results = [run_case(kb, retriever, case) for case in CASES]

    print(f"{len(results)} ca\n")
    print(f"{'shortlist':<12}{_rate([r.shortlist_ok for r in results])}")
    print(f"{'corpus':<12}{_rate([r.corpus_ok for r in results])}")
    print(f"{'business':<12}{_rate([r.business_ok for r in results])}")
    print(f"{'pin':<12}{_rate([r.pin_ok for r in results])}   <- bỏ sót là lỗi, không phải thiếu")
    print(f"{'im lặng':<12}{_rate([r.silence_ok for r in results])}")

    checks = {
        "shortlist": lambda r: r.shortlist_ok,
        "corpus": lambda r: r.corpus_ok,
        "business": lambda r: r.business_ok,
        "pin": lambda r: r.pin_ok,
        "silence": lambda r: r.silence_ok,
    }
    wanted = [args.only] if args.only else list(checks)

    for kind in wanted:
        failures = [r for r in results if checks[kind](r) is False]
        if not failures:
            continue
        print(f"\nHỎNG — {kind} ({len(failures)})")
        for r in failures:
            print(f"  {r.case.text!r}")
            if kind == "shortlist":
                print(f"      mong: {r.case.faults_any}")
                print(f"      được: {r.shortlist or '(rỗng)'}")
            elif kind == "corpus":
                print(f"      mong: {r.case.corpus_any}")
                print(f"      được: {r.passages or '(rỗng)'}")
            elif kind == "business":
                print(f"      mong: {r.case.business_any}")
                print(f"      được: {r.business or '(rỗng)'}")
            elif kind == "pin":
                print(f"      mong ghim: {r.case.pin}")
                print(f"      ghim được: {r.pinned or '(không ghim gì)'}")
            elif kind == "silence":
                print(f"      lấy nhầm: {r.passages}")

    if args.show_passages:
        print("\nCHI TIẾT")
        for r in results:
            if not (r.passages or r.business or r.pinned):
                continue
            print(f"\n  {r.case.text!r}")
            if r.pinned:
                print(f"      GHIM {r.pinned}")
            for path in r.passages:
                print(f"      {path}")
            for path in r.business:
                print(f"      BIZ {path}")


if __name__ == "__main__":
    main()
