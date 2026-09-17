"""Build the bulk of the case suite out of the corpus itself.

The hand-written cases in chat_cases.py encode judgement: which messages are
too vague to answer, which are out of scope, which must warn before anything
else. There is no way to generate those and no reason to.

What can be generated is volume, and volume is what a suite of a hundred and
forty-three lacks. Every fault file quotes the sentences that fault arrives
as — the blunt version, the one with no tone marks, the one describing a
consequence, the one where the customer has already guessed wrong — and each
quote comes with the fault it was written under. That is a labelled example,
written per fault by someone thinking about the trade rather than about
scoring, and there are over a thousand of them.

    python tools/build_cases.py --count 260 > tools/chat_cases_generated.py

Regenerate after editing the corpus. The output is committed, so a run of the
suite does not depend on this script and a reviewer can read what is being
tested.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import device_hint  # noqa: E402
from app.services.pipeline.corpus import get_corpus  # noqa: E402
from app.services.pipeline.knowledge_base import get_knowledge_base  # noqa: E402
from tools.sync_symptoms import PHRASING_HEADINGS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIN_WORDS = 3
"""Below this the message settles nothing and the service is right to ask.

"Hư rồi" is a real thing customers type and it is in the hand-written suite as
an `ask` case. Generating it as a `diagnose` case would test the opposite of
what the service should do.
"""


def harvest() -> List[Tuple[str, str, str]]:
    """Every quoted customer sentence, with the fault and device it belongs to."""
    kb = get_knowledge_base()
    device_of = {
        fault.fault_code: fault.device_type
        for device in kb.device_types
        for fault in kb.faults_for_device(device)
    }
    seen: Dict[str, Tuple[str, str, str]] = {}
    for chunk in get_corpus():
        if chunk.doc_type != "fault" or not chunk.fault_code:
            continue
        if not chunk.heading_vi.startswith(PHRASING_HEADINGS):
            continue
        device = device_of.get(chunk.fault_code)
        if not device:
            continue
        for quote in re.findall(r'"([^"]+)"', chunk.text):
            text = " ".join(quote.split())
            if len(text.split()) < MIN_WORDS or len(text) > 70:
                continue
            # One sentence, one case. The same phrasing appears under more than
            # one fault, and a case that expects both is weaker than one that
            # expects either, so the first wins and duplicates are dropped.
            seen.setdefault(text.casefold(), (text, chunk.fault_code, device))

    # A message that names no appliance is one the service is right to answer
    # with a question, so a generated case that expects a diagnosis has to name
    # one. Half of these quotes do — "quạt trần kêu lộc cộc" — and half are the
    # fragment a customer types when the appliance is already on screen.
    named = []
    for text, fault, device in seen.values():
        if not device_hint.devices_named_in(text, kb):
            label = kb.device_name_vi(device)
            if not label:
                continue
            text = f"{label.lower()} {text}"
        named.append((text, fault, device))
    return named


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=260)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    found = harvest()
    random.Random(args.seed).shuffle(found)
    chosen = found[: args.count]

    print('"""Cases generated from the corpus by tools/build_cases.py.')
    print()
    print("Do not edit by hand: regenerate after changing the corpus. Each entry")
    print("is a sentence a fault file says that fault arrives as, so the label is")
    print("the fault the sentence was written under.")
    print('"""')
    print()
    print("from __future__ import annotations")
    print()
    print("from typing import List")
    print()
    print("from chat_cases import Case")
    print()
    print(f"# {len(chosen)} cases, harvested from {len(found)} quoted sentences.")
    print("GENERATED: List[Case] = [")
    for text, fault, device in chosen:
        safe = text.replace('"', "'")
        print(f'    Case("{safe}", "diagnose", "{device}", ["{fault}"]),')
    print("]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
