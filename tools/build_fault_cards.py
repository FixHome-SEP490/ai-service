"""Write app/data/fault_cards.json: one card per fault, the unit the chat model reasons over.

    python tools/build_fault_cards.py           # rewrite the file
    python tools/build_fault_cards.py --check   # exit 1 if the file is stale

How the knowledge is split, and why. The documents run to a thousand lines
each and used to be chunked by heading into 3,319 passages, retrieved by
shared words. A question about a smell could pull a paragraph on refrigerant
pressure from a neighbouring fault, and the model answered from whatever came
first. Diagnosis is not a search problem here: an appliance has at most twelve
faults, so the model is shown all of them. What it lacks is the expertise that
separates them, and that is what a card holds, one fault per card, one voice,
no prices:

    signs        how customers describe it (symptoms_vi)
    rule_out     when it must NOT be concluded ("Khi nào KHÔNG ...")
    ask          the most decisive question ("Cây hỏi", "Câu hỏi tách nhánh")
    versus       for each look-alike fault, how to tell the two apart
                 ("Lẫn với bệnh nào", "Phân biệt với ...")
    summary      what it is, in plain words, for a follow-up "vì sao"

Sentences are cut from the documents, never written here, so a technician's
correction to a document reaches the model the next time this runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
FAULT_DIR = ROOT / "app" / "data" / "knowledge" / "faults"
KB = ROOT / "app" / "data" / "fault_knowledge_base.json"
OUT = ROOT / "app" / "data" / "fault_cards.json"

SENTENCE_MAX = 170
SUMMARY_MAX = 320
RULES_MAX = 4
VERSUS_MAX = 5


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _frontmatter(text: str) -> Dict[str, object]:
    match = re.match(r"^---\n(.*?)\n---", text, flags=re.S)
    meta: Dict[str, object] = {}
    if not match:
        return meta
    key = None
    for line in match.group(1).splitlines():
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key:
            meta.setdefault(key, []).append(item.group(1).strip())  # type: ignore[union-attr]
            continue
        pair = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if pair:
            key, value = pair.group(1), pair.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            elif value:
                meta[key] = value
    return meta


def _sections(text: str) -> Dict[str, str]:
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    parts = re.split(r"^## +(.+)$", body, flags=re.M)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def _matching(sections: Dict[str, str], *starts: str) -> List[str]:
    return [body for title, body in sections.items() if any(_fold(title).startswith(_fold(s)) for s in starts)]


def _clean(text: str) -> str:
    return " ".join(re.sub(r"\*\*|[`#>]", "", text).split())


def _sentence(text: str, limit: int = SENTENCE_MAX) -> str:
    text = _clean(text)
    first = re.split(r"(?<=[.?!])\s+", text, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0] + "…"


def _paragraphs(text: str) -> List[str]:
    return [p for p in re.split(r"\n\s*\n", text) if p.strip() and not p.lstrip().startswith("|")]


def _summary(sections: Dict[str, str]) -> str:
    body = (_matching(sections, "nói ngắn gọn") or list(sections.values())[:1] or [""])[0]
    text = _clean(" ".join(_paragraphs(body)[:2]))
    if len(text) <= SUMMARY_MAX:
        return text
    cut = text[:SUMMARY_MAX]
    end = cut.rfind(". ")
    return cut[: end + 1] if end > SUMMARY_MAX // 2 else cut.rsplit(" ", 1)[0] + "…"


def _rules(sections: Dict[str, str]) -> List[str]:
    out: List[str] = []
    for body in _matching(sections, "khi nào không"):
        for p in _paragraphs(body):
            s = _sentence(p)
            if s and s not in out:
                out.append(s)
    return out[:RULES_MAX]


def _ask(sections: Dict[str, str]) -> str:
    for body in _matching(sections, "cây hỏi", "câu hỏi tách", "câu hỏi phân"):
        for p in _paragraphs(body):
            s = _sentence(p)
            if s:
                return re.sub(r"^Câu hỏi[^:]*:\s*", "", s)
    return ""


TELLS = ("tach", "khac", "con ", "neu", "trong khi", "nguoc lai", "chi ", "khong ")


def _telling_sentence(body: str) -> str:
    """The sentence that says how to tell the two apart, not the preamble about why it matters."""
    sentences = [x for p in _paragraphs(body) for x in re.split(r"(?<=[.?!])\s+", _clean(p)) if x]
    pick = next((x for x in sentences if any(t in _fold(x) for t in TELLS)), sentences[0] if sentences else "")
    return _sentence(pick)


def _named_code(title_rest: str, codes: List[str], names: Dict[str, str]) -> Optional[str]:
    """The look-alike a "Phân biệt với ..." heading names, by overlap with the faults' names."""
    words = set(title_rest.split())
    scored = [(len(words & set(_fold(names.get(c, "")).split())), c) for c in codes]
    best = max(scored, default=(0, None))
    return best[1] if best[0] >= 1 else None


def _versus(sections: Dict[str, str], codes: List[str], own: str, names: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for body in _matching(sections, "lẫn với bệnh nào"):
        for p in _paragraphs(body):
            m = re.match(r"\s*\*\*([A-Z][A-Z0-9_]+)\.?\*\*\.?\s*(.*)", p, flags=re.S)
            if m and m.group(1) != own:
                out.setdefault(m.group(1), _telling_sentence(m.group(2)))
    for title, body in sections.items():
        fold = _fold(title)
        if not fold.startswith("phan biet voi"):
            continue
        code = _named_code(fold[len("phan biet voi"):], codes, names)
        if code and code not in out and code != own:
            out[code] = _telling_sentence(body)
    return dict(list(out.items())[:VERSUS_MAX])


def card(path: Path, symptoms: List[str], names: Dict[str, str]) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    meta = _frontmatter(text)
    sections = _sections(text)
    confusable = [c for c in meta.get("confusable_with", []) or [] if isinstance(c, str)]
    return {
        "signs_vi": symptoms[:8],
        "rule_out_vi": _rules(sections),
        "ask_vi": _ask(sections),
        "versus_vi": _versus(sections, confusable, path.stem, names),
        "confusable_with": confusable,
        "summary_vi": _summary(sections),
    }


def build() -> Dict[str, object]:
    kb = {f["fault_code"]: f for f in json.loads(KB.read_text(encoding="utf-8"))["faults"]}
    names = {code: f["name_vi"] for code, f in kb.items()}
    cards = {
        path.stem: card(path, list(kb.get(path.stem, {}).get("symptoms_vi") or []), names)
        for path in sorted(FAULT_DIR.glob("*.md"))
        if path.stem in kb
    }
    return {
        "_comment_vi": "Sinh bởi tools/build_fault_cards.py từ app/data/knowledge/faults. Không sửa tay.",
        "cards": cards,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("fault_cards.json is stale: run python tools/build_fault_cards.py")
            sys.exit(1)
        return
    OUT.write_text(text, encoding="utf-8")
    cards = data["cards"]
    print(
        f"{len(cards)} cards; no rule_out {sum(not c['rule_out_vi'] for c in cards.values())}, "
        f"no ask {sum(not c['ask_vi'] for c in cards.values())}, "
        f"no versus {sum(not c['versus_vi'] for c in cards.values())}"
    )


if __name__ == "__main__":
    main()
