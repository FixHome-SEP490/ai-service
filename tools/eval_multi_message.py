"""Several appliances in one message: is each one found, and each one diagnosed?

    python tools/eval_multi_message.py                    # about 6,000 messages
    python tools/eval_multi_message.py --cases 20000 --split test --out multi.json

PO 25/10/2026: a customer tells about two or three appliances at once and the
assistant answers every one in the same reply. That works only if the message
is cut into the right pieces and each piece goes to the right appliance. This
builds such messages from `understanding_bank.json` (descriptions written the
way people talk, never the knowledge base's own symptom wording), two or three
different appliances per message, joined the many ways people join them
("còn", "với lại", "ngoài ra", "à quên", a full stop, nothing at all), then
said in a region's words and typed every way `dialogue_corpus.styled` knows.

Held out the same way as eval_understanding.py: a message is `test` when its
first description is, and the connectors and openers of `test` messages are
never used in `dev` ones. Fixes may look at `dev` failures only.

Counted per message:
    found      every appliance of the message is in the reply's devices[]
    lead       the first appliance mentioned leads the reply
    extra      the reply names an appliance the message did not
and per appliance:
    hit        its fault is among the faults its own diagnosis names
    wrong      its diagnosis names faults and its fault is not one of them
    asked      its diagnosis asks a question instead of naming a fault
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from eval_understanding import BANK, _SELF, _tidy, dialect, split_of  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONNECTORS = {
    "dev": [", ", ". ", ", còn ", ", với lại ", " ngoài ra ", ", thêm cái ", " và ", "; ", ", cả ", ". Còn ", " rồi ", ", "],
    "test": [" xong ", ", à quên, ", ". Thêm nữa ", " kèm theo ", ", mà ", " - "],
}
OPENERS = {
    "dev": ["", "", "", "nhà em có mấy việc: ", "chào em, nhờ xem giúp mấy cái: ", "cho hỏi chút, "],
    "test": ["", "", "Dạ anh chị ơi, nhà có vài thứ hư: ", "nhờ FixHome xử lý giúp: "],
}
STYLES = [
    "chuẩn", "chuẩn", "không dấu", "teencode", "telex sót", "viết hoa", "kéo dài",
    "emoji", "không dấu câu", "lỗi gõ", "giọng nói", "trộn tiếng anh",
]


@dataclass
class Message:
    devices: List[str]
    faults: List[str]
    split: str
    region: str
    style: str
    text: str
    pieces: List[str] = field(default_factory=list)


def build(bank: dict, count: int, seed: int, styled, device_names) -> List[Message]:
    rng = random.Random(seed)
    devices = [d for d, info in bank["devices"].items() if info.get("faults")]
    out: List[Message] = []
    tries = 0
    while len(out) < count and tries < count * 5:
        tries += 1
        chosen = rng.sample(devices, 3 if rng.random() < 0.4 else 2)
        region = rng.choice(["bac", "trung", "nam"])
        pieces, faults, split = [], [], None
        for i, device in enumerate(chosen):
            info = bank["devices"][device]
            code = rng.choice(sorted(info["faults"]))
            phrases = info["faults"][code].get("clear") or []
            if not phrases:
                break
            if split is None:
                pool = phrases
            else:
                pool = [p for p in phrases if split_of(p) == split] or phrases
            phrase = rng.choice(pool)
            split = split or split_of(phrase)
            if rng.random() < 0.75:
                name = rng.choice(device_names.get(device, {}).get(region) or [device])
            else:
                same = [n for n in info["names"] if split_of(n) == split] or info["names"]
                name = rng.choice(same)
            me = rng.choice(_SELF[region]) if i == 0 and rng.random() < 0.5 else ""
            pieces.append(_tidy(f"{name} {me} {phrase}"))
            faults.append(code)
        if len(pieces) != len(chosen):
            continue
        joins = CONNECTORS[split]
        text = rng.choice(OPENERS[split]) + pieces[0]
        for piece in pieces[1:]:
            text += rng.choice(joins) + piece
        style = rng.choice(STYLES)
        text = styled(dialect(_tidy(text), region, rng), style, rng)
        if text.strip(" ,.!?"):
            out.append(Message(chosen, faults, split, region, style, text[:2000], pieces))
    return out


class _NoDetector:
    async def detect(self, image):
        return []


async def run(messages: List[Message]) -> List[dict]:
    from app.schemas.diagnosis import DiagnosisRequest
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm

    kb = get_knowledge_base()
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    rows = []
    for message in messages:
        started = time.perf_counter()
        try:
            reply = await pipeline.diagnose(DiagnosisRequest(description=message.text))
        except Exception as exc:  # a crash is a result
            rows.append({**asdict(message), "error": repr(exc)[:200]})
            continue
        ms = round(1000 * (time.perf_counter() - started), 1)
        entries = {d.device_type: [f.fault_code for f in d.suspected_faults] for d in reply.devices}
        order = [d.device_type for d in reply.devices]
        if not entries:
            held = pipeline._conversations.peek(reply.session_id)
            device = (reply.device.device_type if reply.device else None) or (held.device_type if held else None)
            if device:
                entries = {device: [f.fault_code for f in reply.suspected_faults]}
                order = [device]
        rows.append({**asdict(message), "got": order, "faults_got": entries, "ms": ms})
        if len(pipeline._conversations._sessions) > 600:
            pipeline._conversations._sessions.clear()
    return rows


def score(rows: List[dict]) -> dict:
    t = Counter()
    for row in rows:
        if "error" in row:
            t["error"] += 1
            continue
        t["messages"] += 1
        got = row["got"]
        t["found"] += set(row["devices"]) <= set(got)
        t["lead"] += bool(got) and got[0] == row["devices"][0]
        t["extra"] += bool(set(got) - set(row["devices"]))
        for device, fault in zip(row["devices"], row["faults"]):
            t["appliances"] += 1
            named = row["faults_got"].get(device)
            if named is None:
                t["missing"] += 1
            elif fault in named:
                t["hit"] += 1
            elif named:
                t["wrong"] += 1
            else:
                t["asked"] += 1
    return dict(t)


def report(rows: List[dict], show: int) -> dict:
    out = {}
    for split in ("dev", "test", "all"):
        part = [r for r in rows if split == "all" or r["split"] == split]
        if not part:
            continue
        t = score(part)
        out[split] = t
        m, a = t.get("messages", 0) or 1, t.get("appliances", 0) or 1
        print(f"--- {split}: {t.get('messages', 0)} tin, {t.get('appliances', 0)} thiết bị, lỗi chương trình {t.get('error', 0)}")
        print(f"  đủ mọi thiết bị trong tin      {t.get('found', 0):6d}/{m}  {100 * t.get('found', 0) / m:5.1f}%")
        print(f"  thiết bị nói đầu đứng đầu      {t.get('lead', 0):6d}/{m}  {100 * t.get('lead', 0) / m:5.1f}%")
        print(f"  thêm thiết bị không có trong tin {t.get('extra', 0):4d}/{m}  {100 * t.get('extra', 0) / m:5.1f}%")
        print(f"  mỗi thiết bị: đúng lỗi         {t.get('hit', 0):6d}/{a}  {100 * t.get('hit', 0) / a:5.1f}%")
        print(f"  mỗi thiết bị: hỏi lại          {t.get('asked', 0):6d}/{a}  {100 * t.get('asked', 0) / a:5.1f}%")
        print(f"  mỗi thiết bị: sai chắc nịch    {t.get('wrong', 0):6d}/{a}  {100 * t.get('wrong', 0) / a:5.1f}%")
        print(f"  mỗi thiết bị: bị bỏ sót        {t.get('missing', 0):6d}/{a}  {100 * t.get('missing', 0) / a:5.1f}%")
    by_style = Counter()
    by_style_ok = Counter()
    for r in rows:
        if "error" in r:
            continue
        by_style[r["style"]] += 1
        by_style_ok[r["style"]] += set(r["devices"]) <= set(r["got"])
    print("  theo kiểu gõ (đủ thiết bị): " + ", ".join(
        f"{s} {100 * by_style_ok[s] / by_style[s]:.0f}%" for s in sorted(by_style)))
    misses = [r for r in rows if "error" not in r and not set(r["devices"]) <= set(r["got"]) and r["split"] == "dev"]
    for r in misses[:show]:
        print(f"  [SÓT] {r['devices']} -> {r['got']} | {r['text'][:160]}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--show", type=int, default=25)
    parser.add_argument("--out", default="")
    parser.add_argument("--app-root", default=str(TOOLS.parent))
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.app_root).resolve()))
    from dialogue_corpus import DEVICE_NAMES, styled

    bank = json.loads(Path(BANK).read_text(encoding="utf-8"))
    messages = build(bank, args.cases, args.seed, styled, DEVICE_NAMES)
    if args.split != "all":
        messages = [m for m in messages if m.split == args.split]
    started = time.time()
    rows = asyncio.run(run(messages))
    ms = sorted(r["ms"] for r in rows if "ms" in r)
    print(f"chạy {len(rows)} tin trong {time.time() - started:.0f}s; trung vị {ms[len(ms) // 2]:.0f} ms, p95 {ms[int(len(ms) * 0.95)]:.0f} ms")
    totals = report(rows, args.show)
    if args.out:
        Path(args.out).write_text(json.dumps({"totals": totals, "rows": rows}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
