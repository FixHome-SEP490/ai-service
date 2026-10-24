"""Does the service understand the same fault whoever says it, however it is typed?

`eval_dialogue.py` tests the conversation around a symptom, but the symptom
phrases it uses are the knowledge base's own, so it cannot tell whether the
service understands a customer who describes the fault in different words.
This does. `understanding_bank.json` holds, for every fault, descriptions
written the way people actually talk ("bật cả tiếng mà phòng vẫn hầm hập")
that deliberately avoid the wording of `symptoms_vi`, plus names for each
appliance that are not in the alias list ("con Daikin", "cái Ariston"). Each
description is then said by a different person:

    who      elderly, young, angry, technical, terse, storyteller, polite,
             worried, asking straight out, asking for a technician, passing
             on what a relative said
    where    Bắc, Trung, Nam words ("hư", "hông", "nỏ", "rứa", "dzậy", "chi")
    how      every typing style `dialogue_corpus.styled` knows: no accents,
             teencode, Telex left on, caps, stretched letters, emoji, no
             punctuation, typos, voice-to-text, English words
    device   named the usual way, named by brand or slang, known from a
             photograph, or not named at all

The bank is split once, by a hash of each description, into `dev` (70%) and
`test` (30%). Fixes may be guided by failures on `dev`. `test` is the number
to report, and none of its wording may be copied into `app/data/`: the moment
it is, it measures memory instead of understanding.

    python tools/eval_understanding.py                  # about 35,000 cases
    python tools/eval_understanding.py --per-phrase 40  # more
    python tools/eval_understanding.py --split test --out result.json
    python tools/eval_understanding.py --app-root ../other-checkout

What is counted, worst first:

    wrong      answered with confidence, and the fault is not even among the
               three the shortlist ranked first. The customer acts on it.
    refused    told it is not a household repair, about a household repair.
    top3       the fault is among the first three of the shortlist the model
               chooses from. This is what retrieval controls.
    top1       the shortlist leads with it.
    device     the appliance the service settled on, where the message names
               one or a photograph did.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

TOOLS = Path(__file__).resolve().parent
BANK = TOOLS / "understanding_bank.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Who is speaking
# ---------------------------------------------------------------------------

PERSONAS: Dict[str, List[str]] = {
    "lớn tuổi": [
        "Cháu ơi, {s} {p} cháu ạ",
        "Chào cháu, {s} dạo này {p}, cháu xem giúp bà với",
        "Cô hỏi chút, {s} {p}",
        "bác nhờ cháu xem hộ, {s} {p}",
    ],
    "trẻ": ["{s} {p}", "ê {s} {p} á", "{s} {p} luôn á", "{s} {p} huhu"],
    "bực bội": [
        "{s} mới mua mà đã {p}, bực mình quá",
        "làm ăn kiểu gì mà {s} {p}",
        "{s} lại {p} nữa rồi, chán thật sự",
    ],
    "kỹ thuật": [
        "Tình trạng: {s} {p}. Đã thử rút điện cắm lại.",
        "{s} {p}, nguồn điện vẫn ổn định",
    ],
    "kiệm lời": ["{s} {p}", "{p}"],
    "kể lể": [
        "hôm qua đang dùng bình thường thì tự nhiên {s} {p}, lo quá không biết làm sao",
        "{s} mua được ba năm rồi, trước giờ không sao, mấy hôm nay thì {p}",
        "chuyện là {s} {p}, con nhỏ nó cứ hỏi hoài",
    ],
    "lịch sự": [
        "Xin chào, {s} đang gặp tình trạng {p}. Mong được tư vấn ạ",
        "Cho mình hỏi, {s} {p}, nhờ kiểm tra giúp",
    ],
    "lo lắng": ["{s} {p}, có nguy hiểm không ạ", "{s} {p}, em sợ quá"],
    "hỏi thẳng": ["{s} {p} là bị gì vậy", "tại sao {s} {p}", "{s} {p} thì sửa sao"],
    "nhờ thợ": ["{s} {p}, cho thợ qua xem giúp với", "{s} {p}, đặt thợ giúp em"],
    "kể hộ": ["mẹ em bảo {s} {p}", "chồng em nói {s} {p}, nhờ xem giúp"],
}

# The same eleven speakers framed in other words, used only for `test` cases.
# Retrieval drops conversational framing ("nhờ xem giúp", "mẹ em bảo"), and a
# test that reused the framings that list was written from would be testing the
# list. These are worded apart from it on purpose.
PERSONAS_TEST: Dict[str, List[str]] = {
    "lớn tuổi": ["Này cháu, {s} {p}, cháu bảo bà phải làm thế nào", "ông nhờ cháu chút, {s} {p}"],
    "trẻ": ["ủa {s} {p} là sao á", "trời ơi {s} {p} nè"],
    "bực bội": ["mua về chưa nổi một tháng mà {s} {p}, quá thất vọng", "{s} {p}, tôi không hiểu nổi"],
    "kỹ thuật": ["Mô tả lỗi: {s} {p}. Điện áp đo được 220V.", "{s} {p}, đã kiểm tra aptomat"],
    "kiệm lời": ["{p} ạ", "{s} {p} nhé"],
    "kể lể": ["sáng nay dậy sớm định dùng thì thấy {s} {p}, cả nhà cuống hết cả lên", "nhà có đám giỗ mà {s} {p}, khổ thân em"],
    "lịch sự": ["Dạ chào anh chị, {s} {p}, phiền anh chị hỗ trợ", "Kính gửi FixHome, {s} {p}"],
    "lo lắng": ["{s} {p}, để vậy có sao không ạ", "{s} {p}, có cháy nổ gì không anh"],
    "hỏi thẳng": ["{s} {p}, lỗi gì đây", "vì sao {s} {p}"],
    "nhờ thợ": ["{s} {p}, sắp xếp người qua sửa giúp mình", "{s} {p}, gửi kỹ thuật qua nhà giúp"],
    "kể hộ": ["bà nội nhắn em là {s} {p}", "hàng xóm nhờ hỏi giúp, {s} {p}"],
}

_SELF = {"bac": ["nhà em", "nhà mình", "nhà tôi"], "trung": ["nhà tui", "nhà em"], "nam": ["nhà tui", "nhà em", "nhà mình"]}
_UNNAMED = ["nó", "cái này", "máy nhà em", ""]

# Word for word, what each region says instead. Applied at word boundaries,
# each occurrence with a fair chance, so one message can mix them as people do.
DIALECT: Dict[str, Dict[str, List[str]]] = {
    "bac": {"hư": ["hỏng"], "vậy": ["thế"], "hông": ["không"]},
    "trung": {
        "không": ["không", "nỏ", "khôn"], "gì": ["chi"], "sao": ["răng"], "vậy": ["rứa"],
        "thế": ["rứa"], "đâu": ["mô"], "này": ["ni"], "kia": ["tê"], "giờ": ["chừ"],
        "hỏng": ["hư"], "nhiều": ["nhiều", "lắm"],
    },
    "nam": {
        "không": ["hông", "hổng", "không"], "hỏng": ["hư"], "vậy": ["dzậy", "zậy", "vậy"],
        "thế": ["vậy"], "lắm": ["quá trời", "lắm"], "gì": ["gì", "dì"], "rồi": ["rồi", "rùi"],
    },
}


def dialect(text: str, region: str, rng: random.Random) -> str:
    table = DIALECT.get(region, {})
    if not table:
        return text

    def swap(match: re.Match) -> str:
        word = match.group(0)
        options = table.get(word.lower())
        if not options or rng.random() > 0.6:
            return word
        return rng.choice(options)

    return re.sub(r"\w+", swap, text)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


@dataclass
class Case:
    fault: Optional[str]  # None for a vague or off-topic message
    device: Optional[str]
    kind: str  # clear | indirect | vague | offtopic
    split: str
    phrase: str
    persona: str
    region: str
    style: str
    mode: str  # named | alias | photo | none
    text: str


def split_of(phrase: str) -> str:
    digest = hashlib.sha1(phrase.strip().lower().encode("utf-8")).digest()
    return "test" if digest[0] % 10 < 3 else "dev"


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"^[,.]\s*", "", text)
    return text


def build_cases(bank: dict, per_phrase: int, seed: int, styled, device_names) -> List[Case]:
    rng = random.Random(seed)
    cases: List[Case] = []
    styles = [
        "chuẩn", "chuẩn", "không dấu", "teencode", "telex sót", "viết hoa", "kéo dài",
        "emoji", "không dấu câu", "lỗi gõ", "giọng nói", "trộn tiếng anh",
    ]
    modes = ["named", "named", "alias", "photo", "none"]

    def one(device, fault, kind, phrase, mode=None):
        persona = rng.choice(list(PERSONAS))
        region = rng.choice(["bac", "trung", "nam"])
        style = rng.choice(styles)
        mode = mode or rng.choice(modes)
        info = bank["devices"][device]
        me = rng.choice(_SELF[region])
        if mode == "named":
            name = rng.choice(device_names.get(device, {}).get(region) or [device])
            subject = f"{name} {me}"
        elif mode == "alias":
            # Names are split the same way as descriptions, so a test case is
            # held out in both what it says and what it calls the appliance.
            same = [n for n in info["names"] if split_of(n) == split_of(phrase)] or info["names"]
            subject = f"{rng.choice(same)} {me}"
        else:
            subject = rng.choice(_UNNAMED)
        template = rng.choice((PERSONAS_TEST if split_of(phrase) == "test" else PERSONAS)[persona])
        text = _tidy(template.replace("{s}", subject).replace("{p}", phrase))
        text = dialect(text, region, rng)
        text = styled(text, style, rng)
        if text.strip(" ,.!?"):  # the API refuses an empty description before the pipeline sees it
            cases.append(Case(fault, device, kind, split_of(phrase), phrase, persona, region, style, mode, text))

    for device, info in bank["devices"].items():
        for code, phrases in info["faults"].items():
            for kind in ("clear", "indirect"):
                for phrase in phrases.get(kind, []):
                    for _ in range(per_phrase):
                        one(device, code, kind, phrase)
        for phrase in info.get("vague", []):
            for _ in range(max(2, per_phrase // 4)):
                one(device, None, "vague", phrase, mode=rng.choice(["named", "photo"]))
    for phrase in bank.get("offtopic", []):
        for _ in range(max(2, per_phrase // 4)):
            style = rng.choice(styles)
            text = styled(dialect(phrase, rng.choice(["bac", "trung", "nam"]), rng), style, rng)
            if not text.strip(" ,.!?"):
                continue
            cases.append(Case(None, None, "offtopic", split_of(phrase), phrase, "-", "-", style, "none", text))
    return cases


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


class _NoDetector:
    async def detect(self, image):
        return []


async def run(cases: List[Case]) -> List[dict]:
    from app.core.config import settings
    from app.schemas.diagnosis import DiagnosisRequest
    from app.services.pipeline.knowledge_base import get_knowledge_base
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm

    kb = get_knowledge_base()
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(kb), kb=kb)
    store = pipeline._conversations
    rows = []
    for case in cases:
        chat = store.get_or_create(None)
        if case.mode == "photo" and case.device:
            chat.remember_device(case.device, 0.9, "image")
        started = time.perf_counter()
        try:
            response = await pipeline.diagnose(
                DiagnosisRequest(description=case.text[:2000], sessionId=chat.session_id)
            )
        except Exception as exc:  # a crash is a result, not a reason to stop
            rows.append({**asdict(case), "error": repr(exc)[:200]})
            continue
        elapsed = time.perf_counter() - started
        held = store.get_or_create(response.session_id or chat.session_id)
        device = held.device_type or (response.device.device_type if response.device else None)
        state = getattr(held, "state", None)
        ranked = pipeline._retriever.candidate_faults(
            held.symptom_text(), device, 5,
            (state.excluded_codes() or None) if state else None,
            state.factors() if state is not None else None,
        ) if device else []
        ranked_codes = [r.fault.fault_code for r in ranked]
        suspected = [f.fault_code for f in response.suspected_faults]
        asked = (response.clarification.questions_vi if response.clarification else None) or []
        message = response.message_vi or ""
        refused = settings.OUT_OF_SCOPE_MESSAGE_VI in [message, *asked]
        status = getattr(response.status, "value", response.status)
        rows.append({
            **asdict(case),
            "got_device": device,
            "status": status,
            "refused": refused,
            "suspected": suspected[:3],
            "ranked": ranked_codes,
            "ms": round(1000 * elapsed, 2),
        })
        if len(store._sessions) > 500:
            store._sessions.clear()
    return rows


async def run_http(cases: List[Case], url: str, concurrency: int) -> List[dict]:
    """The same cases against a running service, the real model included.

    Only what a request can carry: a photograph cannot be faked over HTTP, so
    `photo` cases are left out. The faults counted are the ones the reply
    names, which is what the customer reads."""
    import httpx

    from app.core.config import settings

    url = url.rstrip("/")
    gate = asyncio.Semaphore(concurrency)
    rows: List[dict] = []

    async def one(client, case: Case) -> None:
        async with gate:
            started = time.perf_counter()
            try:
                response = await client.post(
                    f"{url}/api/v1/diagnosis/analyze", json={"description": case.text[:2000]}, timeout=90.0
                )
                body = response.json()
            except Exception as exc:
                rows.append({**asdict(case), "error": repr(exc)[:200]})
                return
            if response.status_code != 200:
                rows.append({**asdict(case), "error": f"HTTP {response.status_code}"})
                return
            device = (body.get("device") or {}).get("deviceType")
            suspected = [f.get("faultCode") for f in body.get("suspectedFaults") or []]
            asked = (body.get("clarification") or {}).get("questionsVi") or []
            message = body.get("messageVi") or ""
            rows.append({
                **asdict(case),
                "got_device": device,
                "status": body.get("status"),
                "refused": settings.OUT_OF_SCOPE_MESSAGE_VI in [message, *asked],
                "suspected": suspected[:3],
                "ranked": suspected[:3],
                "ms": round(1000 * (time.perf_counter() - started), 1),
                # A reply that asks a question carries no device field, so
                # over HTTP an unnamed device means "asked", not "wrong".
                "http": True,
            })

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(client, c) for c in cases if c.mode != "photo"))
    return rows


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score(row: dict) -> Dict[str, Optional[bool]]:
    kind = row["kind"]
    if "error" in row:
        return {"no_crash": False}
    if kind == "offtopic":
        return {"offtopic_refused": row["refused"] or row["status"] == "needs_clarification" and not row["suspected"]}
    if kind == "vague":
        answered_confidently = row["status"] == "ok" and bool(row["suspected"])
        return {"vague_asked": not answered_confidently}
    fault, ranked, suspected = row["fault"], row["ranked"], row["suspected"]
    top1 = bool(ranked) and ranked[0] == fault
    top3 = fault in ranked[:3]
    answered = row["status"] == "ok" and bool(suspected)
    out = {
        "top1": top1,
        "top3": top3,
        "top5": fault in ranked[:5],
        "not_wrong": not (answered and suspected[0] != fault and not top3),
        "not_refused": not row["refused"],
    }
    if row["mode"] in ("named", "alias", "photo") and not row.get("http"):
        out["device"] = row["got_device"] == row["device"]
    else:
        # Nothing named it. Settling on the right appliance is good; asking
        # which appliance is fine; settling on the wrong one is the failure.
        out["device"] = row["got_device"] in (row["device"], None)
    return out


def report(rows: List[dict], show: int) -> dict:
    totals: Dict[str, Counter] = defaultdict(Counter)
    by: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        totals["no_crash"]["n"] += 1
        totals["no_crash"]["ok"] += "error" not in row
        for key, ok in score(row).items():
            if key == "no_crash":
                continue
            if ok is None:
                continue
            totals[key]["n"] += 1
            totals[key]["ok"] += bool(ok)
            if key in ("top3", "device", "not_wrong"):
                for dim in ("split", "kind", "persona", "region", "style", "mode", "device"):
                    if dim == "device" and key == "device":
                        continue
                    by[f"{dim}:{row[dim]}"][key]["n"] += 1
                    by[f"{dim}:{row[dim]}"][key]["ok"] += bool(ok)

    def pct(c: Counter) -> str:
        return f"{c['ok']}/{c['n']} {100 * c['ok'] / c['n']:5.1f}%" if c["n"] else "-"

    labels = {
        "top1": "lỗi đứng đầu danh sách",
        "top3": "lỗi nằm trong 3 đầu",
        "top5": "lỗi nằm trong 5 đầu",
        "not_wrong": "không trả lời sai chắc nịch",
        "not_refused": "không từ chối nhầm",
        "device": "nhận đúng thiết bị",
        "vague_asked": "câu mơ hồ thì hỏi lại",
        "offtopic_refused": "câu lạc đề thì từ chối",
        "no_crash": "không lỗi chương trình",
    }
    print(f"\n{len(rows)} câu\n")
    for key, label in labels.items():
        if totals[key]["n"]:
            print(f"  {label:32} {pct(totals[key])}")
    print("\ntheo nhóm (lỗi trong 3 đầu | thiết bị | không sai chắc nịch):")
    for group in sorted(by):
        cells = by[group]
        print(f"  {group:34} {pct(cells['top3']):>18} {pct(cells['device']):>18} {pct(cells['not_wrong']):>18}")

    misses = [r for r in rows if r["kind"] in ("clear", "indirect") and not score(r).get("top3", True)]
    print(f"\nví dụ lỗi không vào 3 đầu ({len(misses)}):")
    rng = random.Random(1)
    for r in rng.sample(misses, min(show, len(misses))):
        print(f"  [{r['fault']}] ({r['persona']}/{r['region']}/{r['style']}/{r['mode']}) {r['text']}")
        print(f"      thiết bị={r['got_device']} xếp={r['ranked'][:3]} trạng thái={r['status']}")
    return {k: dict(v) for k, v in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default=str(TOOLS.parent))
    parser.add_argument("--bank", default=str(BANK))
    parser.add_argument("--per-phrase", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--device", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--show", type=int, default=30)
    parser.add_argument("--url", default="", help="score a running service over HTTP, real model included")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="keep this many cases, spread evenly")
    parser.add_argument(
        "--fail-under",
        default="",
        help="e.g. top3=0.8,not_wrong=0.9: exit 1 if a share falls below, for the nightly run",
    )
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    sys.path.insert(0, str(TOOLS))
    sys.path.insert(0, str(app_root))
    from dialogue_corpus import DEVICE_NAMES, styled

    bank = json.loads(Path(args.bank).read_text(encoding="utf-8"))
    if args.device:
        bank["devices"] = {k: v for k, v in bank["devices"].items() if k == args.device}
    cases = build_cases(bank, args.per_phrase, args.seed, styled, DEVICE_NAMES)
    if args.split != "all":
        cases = [c for c in cases if c.split == args.split]
    if args.limit and len(cases) > args.limit:
        step = len(cases) / args.limit
        cases = [cases[int(i * step)] for i in range(args.limit)]
    started = time.time()
    rows = asyncio.run(run_http(cases, args.url, args.concurrency) if args.url else run(cases))
    print(f"chạy {len(rows)} câu trong {time.time() - started:.0f}s, mã nguồn: {app_root}")
    ms = sorted(r["ms"] for r in rows if "ms" in r)
    if ms:
        print(f"thời gian xử lý một câu (không tính mô hình): trung vị {ms[len(ms) // 2]:.1f} ms, p95 {ms[int(len(ms) * 0.95)]:.1f} ms")
    totals = report(rows, args.show)
    if args.out:
        Path(args.out).write_text(
            json.dumps({"totals": totals, "rows": rows}, ensure_ascii=False), encoding="utf-8"
        )
    failed = []
    for rule in filter(None, args.fail_under.split(",")):
        key, floor = rule.split("=")
        cell = totals.get(key.strip(), {})
        share = cell.get("ok", 0) / cell["n"] if cell.get("n") else 0.0
        if share < float(floor):
            failed.append(f"{key.strip()} {share:.3f} < {float(floor):.3f}")
    if failed:
        print("DƯỚI NGƯỠNG: " + "; ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
