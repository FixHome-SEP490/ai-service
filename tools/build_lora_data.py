"""Training data for the fault-choosing LoRA adapter, captured from the pipeline itself.

    python tools/build_lora_data.py --out datasets/lora/fault-v1
    python tools/build_lora_data.py --out datasets/lora/fault-v1 --single 12000 --dialogues 4000

PO 27/10/2026: train Qwen so it understands descriptions it has never seen and
the whole conversation, not only the last message. On the held-out half of the
understanding bank the served model put the right fault first about 31% of the
time, because the fault was chosen by the word scorer and the model only
reordered what came after it.

Every example is a real prompt: the pipeline runs on the customer's words with
VLM_FAULT_MODEL set, exactly as it will in service, and a capturing model
records the system and user messages `QwenClient.assess_context` would send
(`_assess_system`, `build_context_prompt`) together with the candidates it was
offered. The answer is the JSON the client already parses, with the labelled
fault, or no fault when the words settle nothing (the pipeline then asks).

Held out the way the evaluations are (`eval_understanding.split_of`):

    train, val   only `dev` phrases of tools/understanding_bank.json, dev personas
                 and dev connectors; val is a fixed 3% slice of them, for
                 choosing the checkpoint
    test         only `test` phrases and test personas; never trained on, used
                 once to decide whether the adapter goes into service

Conversations (`kind`):
    single       one message, the way eval_understanding builds them
    vague        a message that names the appliance and nothing else: no fault
    vague_then   "máy lạnh bị sao á" first, the description next
    pushback     a description, then "sai rồi, ..." with another fault's words
    more         an indirect description, then the clear one of the same fault
    feedback     real customers' words a person reviewed (tools/feedback_cases.json,
                 written by tools/feedback_review.py apply), train only

tools/dialogue_corpus.py conversations are not used: they label only what must
not be answered (must_not), not the fault that is right.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PUSHBACK = {
    "dev": ["sai rồi, ", "không phải đâu em, ", "em đoán chưa đúng rồi, ", "không phải bệnh đó, ", "nhầm rồi em, "],
    "test": ["chẩn đoán sai rồi, ", "ủa em ơi sai rồi. ", "không đúng đâu, ", "nói sai rồi em ơi, "],
}
MORE = {
    "dev": ["à mà ", "thêm nữa là ", "nói rõ hơn là ", "à quên, "],
    "test": ["à còn ", "em kể thêm: ", "cụ thể là "],
}
ASK_JSON = {"fault_codes": [], "condition_codes": [], "confidence": 0.2, "reason": ""}


def answer_json(code: Optional[str]) -> str:
    if not code:
        return json.dumps(ASK_JSON, ensure_ascii=False)
    return json.dumps({"fault_codes": [code], "condition_codes": [], "confidence": 0.9, "reason": ""}, ensure_ascii=False)


@dataclass
class Talk:
    kind: str
    split: str
    device: str
    turns: List[str]
    gold: Optional[str]
    must_not: List[str] = field(default_factory=list)


def _bank():
    return json.loads((TOOLS / "understanding_bank.json").read_text(encoding="utf-8"))


def build_talks(single: int, dialogues: int, seed: int) -> List[Talk]:
    from dialogue_corpus import DEVICE_NAMES, styled
    from eval_understanding import build_cases, split_of

    rng = random.Random(seed)
    bank = _bank()
    talks: List[Talk] = []

    # One message: the evaluation's own builder, photo cases left out (the
    # adapter learns text; a photograph goes to the base model).
    cases = [c for c in build_cases(bank, 20, seed, styled, DEVICE_NAMES) if c.kind in ("clear", "indirect", "vague") and c.mode != "photo"]
    rng.shuffle(cases)
    # Vague messages are few in the bank; they get their own quota so the
    # adapter learns when the words settle nothing and the pipeline should ask.
    per_split = {}
    caps = {("dev", False): single, ("test", False): max(1, single // 6),
            ("dev", True): max(1, single // 15), ("test", True): max(1, single // 90)}
    for case in cases:
        key = (case.split, case.kind == "vague")
        if per_split.get(key, 0) >= caps[key]:
            continue
        per_split[key] = per_split.get(key, 0) + 1
        talks.append(Talk("vague" if case.kind == "vague" else "single", case.split, case.device, [case.text], case.fault))

    # Several turns from the bank, each split from its own phrases only.
    styles = ["chuẩn", "chuẩn", "không dấu", "teencode", "lỗi gõ", "giọng nói", "không dấu câu"]
    for split, count in (("dev", dialogues), ("test", max(1, dialogues // 6))):
        made = 0
        attempts = 0
        devices = sorted(bank["devices"])
        while made < count and attempts < count * 20:
            attempts += 1
            device = rng.choice(devices)
            info = bank["devices"][device]
            names = [n for n in info["names"] if split_of(n) == split] or info["names"]
            phrases = {
                code: {k: [p for p in v.get(k, []) if split_of(p) == split] for k in ("clear", "indirect")}
                for code, v in info["faults"].items()
            }
            usable = [c for c, v in phrases.items() if v["clear"] or v["indirect"]]
            if len(usable) < 2:
                continue
            style = rng.choice(styles)
            name = rng.choice(names)
            kind = rng.choice(["vague_then", "pushback", "more", "pushback"])
            gold = rng.choice(usable)
            said = rng.choice(phrases[gold]["clear"] or phrases[gold]["indirect"])
            if kind == "vague_then":
                vague = [p for p in info.get("vague", []) if split_of(p) == split] or [f"{name} bị sao á"]
                first = f"{name} {rng.choice(vague)}"
                turns = [first, said]
            elif kind == "pushback":
                other = rng.choice([c for c in usable if c != gold])
                wrong = rng.choice(phrases[other]["clear"] or phrases[other]["indirect"])
                turns = [f"{name} {wrong}", rng.choice(PUSHBACK[split]) + said]
            else:
                if not (phrases[gold]["clear"] and phrases[gold]["indirect"]):
                    continue
                turns = [f"{name} {rng.choice(phrases[gold]['indirect'])}", rng.choice(MORE[split]) + rng.choice(phrases[gold]["clear"])]
            turns = [styled(t, style, rng) for t in turns]
            if not all(t.strip(" ,.!?") for t in turns):
                continue
            talks.append(Talk(kind, split, device, turns, gold))
            made += 1

    # What real customers said, once a person settled the fault
    # (tools/feedback_review.py apply): trained on every time, a few copies so
    # a handful of real sentences is not lost among the generated ones.
    cases = json.loads((TOOLS / "feedback_cases.json").read_text(encoding="utf-8")).get("cases", [])
    for case in cases:
        for _ in range(3):
            talks.append(Talk("feedback", "dev", case["device"], [case["text"]], case["fault"]))
    return talks


class _NoDetector:
    async def detect(self, image):
        return []


async def capture(talks: List[Talk]) -> List[dict]:
    from app.core.config import settings
    from app.schemas.diagnosis import DiagnosisRequest
    from app.services.pipeline import qwen_client
    from app.services.pipeline import service_catalog as sc
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm, VlmVerdict

    settings.VLM_FAULT_MODEL = "fixhome-fault"  # the pipeline offers what the adapter will be offered

    class Capture(StubVlm):
        def __init__(self):
            self.gold: Optional[str] = None
            self.last: Optional[dict] = None

        async def assess_context(self, crop, context, candidate_condition_codes):
            offered = [c.fault.fault_code for c in context.candidates]
            self.last = {
                "system": qwen_client._assess_system(False),
                "user": qwen_client.build_context_prompt(context),
                "offered": offered,
                "device_known": context.device_type is not None,
            }
            # Earlier turns answer the way the service would without the
            # adapter (retrieval's leader), so the history reads like a real one.
            pick = self.gold if self.gold in offered else (offered[0] if offered else None)
            return VlmVerdict(fault_codes=[pick] if pick else [], confidence=0.9 if pick else 0.2)

    kb = get_knowledge_base()
    sc.install(sc.LiveCatalog())
    vlm = Capture()
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=vlm, retriever=Retriever(kb), kb=kb)
    rows = []
    for i, talk in enumerate(talks):
        session = None
        last = None
        for turn_no, text in enumerate(talk.turns):
            final = turn_no == len(talk.turns) - 1
            vlm.gold = None if not final else talk.gold
            vlm.last = None
            try:
                reply = await pipeline.diagnose(DiagnosisRequest(description=text[:2000], session_id=session))
            except Exception:
                last = None
                break
            session = reply.session_id
            last = vlm.last if final else last
        if not last or not last["device_known"]:
            continue  # the pipeline asked which appliance before the model was consulted
        gold = talk.gold if talk.gold in last["offered"] else None
        if talk.gold and gold is None:
            continue  # the customer's own denial took it off the list: no clean label
        rows.append({
            "messages": [
                {"role": "system", "content": last["system"]},
                {"role": "user", "content": last["user"]},
                {"role": "assistant", "content": answer_json(gold)},
            ],
            "gold": gold,
            "offered": last["offered"],
            "kind": talk.kind,
            "split": talk.split,
            "device": talk.device,
            "turns": talk.turns,
        })
        if len(pipeline._conversations._sessions) > 500:
            pipeline._conversations._sessions.clear()
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{len(talks)}", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--single", type=int, default=12000, help="one-message examples from dev phrases")
    parser.add_argument("--dialogues", type=int, default=4000, help="multi-turn examples from dev phrases")
    parser.add_argument("--seed", type=int, default=20261027)
    args = parser.parse_args()

    logging.disable(logging.WARNING)
    talks = build_talks(args.single, args.dialogues, args.seed)
    print(f"{len(talks)} cuộc trò chuyện, đang chụp prompt")
    rows = asyncio.run(capture(talks))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    buckets = {"train": [], "val": [], "test": []}
    for row in rows:
        if row["split"] == "test":
            buckets["test"].append(row)
            continue
        key = hashlib.sha1(json.dumps(row["turns"], ensure_ascii=False).encode("utf-8")).digest()[0]
        buckets["val" if key % 100 < 3 else "train"].append(row)
    manifest = {"seed": args.seed, "counts": {}, "by_kind": {}, "chars": {}}
    for name, items in buckets.items():
        path = out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        manifest["counts"][name] = len(items)
        kinds = {}
        for item in items:
            kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
        manifest["by_kind"][name] = kinds
        lengths = sorted(len(item["messages"][0]["content"]) + len(item["messages"][1]["content"]) for item in items) or [0]
        manifest["chars"][name] = {"median": lengths[len(lengths) // 2], "p95": lengths[int(len(lengths) * 0.95)]}
        manifest[f"sha1_{name}"] = hashlib.sha1(path.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
