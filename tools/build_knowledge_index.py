"""Write app/data/knowledge_index.json: the passages the chat answers questions from.

    python tools/build_knowledge_index.py           # rewrite the file
    python tools/build_knowledge_index.py --check   # exit 1 if the file is stale

Diagnosis reads the fault cards (tools/build_fault_cards.py). Everything else
a customer asks - what FixHome is, who the assistant is, how booking, payment
and warranty work, where FixHome serves, how often to clean an air
conditioner, whether a fridge is worth repairing, how long a repair takes -
is answered from these passages.

How the documents are split, and why there. Every document under
app/data/knowledge is written so that each "##" section reads on its own (its
README requires it), so a section is the unit: one topic, one voice, small
enough to quote. Sections written for the assistant rather than about the
subject (sample dialogues, sources, sentences never to say, what awaits a
technician's confirmation, how customers misspell things) are left out, so a
passage can always be quoted to a customer.

Each passage has a scope, and a question only sees the scopes its conversation
is in: `platform` always; `device:<type>` for the appliance being discussed;
`fault:<code>` for the fault just concluded. Two kinds are generated from the
catalogue rather than written: what FixHome takes on (`catalog:services`) and
each appliance's services with prices (`catalog:<type>`), so a price or a
service list is never a sentence somebody typed and forgot to update.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "app" / "data" / "knowledge"
DATA = ROOT / "app" / "data"
OUT = DATA / "knowledge_index.json"

TEXT_MAX = 1200

# Platform documents. thiet-bi-de-nhin-nham.md is dialogue rules, not knowledge.
PLATFORM_DOCS = (
    "tong-quan-fixhome", "vai-tro-cua-ai", "quy-trinh-dat-lich", "gia-va-cach-tinh-tien", "bao-hanh", "khu-vuc-phuc-vu",
    "cau-hoi-thuong-gap",
)
# From the persona documents only the one that says who the assistant is.
PERSONA_SECTIONS = ("em la ai",)

SKIP = (
    "nen tri thuc", "cho can", "kich ban", "nhung cau khong", "cho em khong buoc qua",
    "khach goi ten", "khach go khong dau", "pham vi tai lieu", "vi sao tai lieu nay",
    "khach hoi the nao", "tra loi the nao cho dung",
    # Written for the vision model the chat no longer is; the detector reads photographs now.
    "doc anh", "anh khach gui", "khach chi gui anh",
)
# Fault sections a customer asks about after the diagnosis.
FAULT_SECTIONS = (
    "noi ngan gon", "chuyen gi dang xay ra", "de lau thi hong gi", "khach tu kiem tra", "viec khach khong nen tu lam",
    "viec khach tu lam duoc", "tho toi thi lam gi", "cai gi lam chi phi thay doi", "khach hay hoi them",
    "giu cho benh khong tai", "phong cho lan sau", "sua hay thay", "khi nao ca nay thanh gap", "nguyen nhan",
)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _clean(text: str) -> str:
    text = re.sub(r"\*\*|`|^#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<!\n)\n(?!\n|- )", " ", text)  # rejoin wrapped lines, keep paragraphs and lists
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _clip(text: str) -> str:
    if len(text) <= TEXT_MAX:
        return text
    cut = text[:TEXT_MAX]
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return cut[: end + 1] if end > TEXT_MAX // 2 else cut.rsplit(" ", 1)[0] + "…"


def _sections(path: Path):
    body = re.sub(r"^---.*?---\s*", "", path.read_text(encoding="utf-8"), flags=re.S)
    title = next((m.group(1).strip() for m in re.finditer(r"^# +(.+)$", body, flags=re.M)), path.stem)
    parts = re.split(r"^## +(.+)$", body, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        yield title, parts[i].strip(), parts[i + 1].strip()


def _passage(pid: str, scope: str, doc: str, section: str, text: str) -> Dict[str, str]:
    return {"id": pid, "scope": scope, "doc_vi": doc, "section_vi": section, "text_vi": _clip(_clean(text))}


def _catalog() -> List[Dict[str, str]]:
    services = [s for s in json.loads((DATA / "service_catalog.json").read_text(encoding="utf-8"))["services"] if s.get("active")]
    names = {d["device_type"]: d["name_vi"] for d in json.loads((DATA / "device_catalog.json").read_text(encoding="utf-8"))["devices"]}
    by_category: Dict[str, List[str]] = defaultdict(list)
    by_device: Dict[str, List[str]] = defaultdict(list)
    for s in services:
        by_category[s["category_vi"]].append(s["name_vi"])
        price = s.get("price_min_vnd")
        top = s.get("price_max_vnd")
        money = (f"{price:,}đ" + (f" đến {top:,}đ" if top and top != price else "")).replace(",", ".") if price else "báo giá sau khi kiểm tra"
        kind = "giá tham khảo, thợ báo giá chính xác sau khi kiểm tra" if s.get("pricing") == "inspection" else "giá cố định theo loại máy"
        for device in s.get("device_types") or []:
            by_device[device].append(f"- {s['name_vi']}: {money} ({kind})")
    out = [
        _passage(
            "catalog:services", "platform", "Danh mục dịch vụ FixHome", "FixHome đang nhận những dịch vụ gì",
            "FixHome đang nhận các dịch vụ sau, theo nhóm:\n" + "\n".join(f"- {c}: {', '.join(v)}" for c, v in by_category.items())
            + "\nFixHome không nhận sửa laptop, máy tính, điện thoại, máy in, xe máy, ô tô.",
        )
    ]
    for device, lines in by_device.items():
        out.append(_passage(
            f"catalog:{device}", f"device:{device}", "Bảng giá dịch vụ", f"Giá dịch vụ {names.get(device, device).lower()}",
            f"Dịch vụ {names.get(device, device).lower()} trên FixHome, giá là tiền công, chưa gồm linh kiện:\n" + "\n".join(lines),
        ))
    return out


def build() -> Dict[str, object]:
    passages: List[Dict[str, str]] = []
    for stem in PLATFORM_DOCS:
        for n, (doc, section, text) in enumerate(_sections(KNOWLEDGE / "system" / f"{stem}.md")):
            if not fold(section).startswith(SKIP):
                passages.append(_passage(f"system:{stem}:{n}", "platform", doc, section, text))
    for path in sorted((KNOWLEDGE / "persona").glob("*.md"), key=lambda p: p.name):
        for n, (doc, section, text) in enumerate(_sections(path)):
            if fold(section).startswith(PERSONA_SECTIONS):
                passages.append(_passage(f"persona:{path.stem}:{n}", "platform", doc, section, text))
    for path in sorted((KNOWLEDGE / "devices").glob("*.md"), key=lambda p: p.name):
        for n, (doc, section, text) in enumerate(_sections(path)):
            if not fold(section).startswith(SKIP):
                passages.append(_passage(f"device:{path.stem}:{n}", f"device:{path.stem}", doc, section, text))
    for path in sorted((KNOWLEDGE / "faults").glob("*.md"), key=lambda p: p.name):
        for n, (doc, section, text) in enumerate(_sections(path)):
            if fold(section).startswith(FAULT_SECTIONS):
                passages.append(_passage(f"fault:{path.stem}:{n}", f"fault:{path.stem}", doc, section, text))
    passages += _catalog()
    return {"_comment_vi": "Sinh bởi tools/build_knowledge_index.py. Không sửa tay.", "passages": passages}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("knowledge_index.json is stale: run python tools/build_knowledge_index.py")
            sys.exit(1)
        return
    OUT.write_text(text, encoding="utf-8")
    scopes: Dict[str, int] = defaultdict(int)
    for x in data["passages"]:
        scopes[x["scope"].split(":")[0]] += 1
    print(f"{len(data['passages'])} passages: {dict(scopes)}")


if __name__ == "__main__":
    main()
