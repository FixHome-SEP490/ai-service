"""Error codes the appliance shows, read from the manufacturer's own table.

"Máy lạnh Daikin báo U0" has one right answer, and it is the manufacturer's,
not ours: app/data/error_codes.json holds only codes copied from a brand's
official document, with the link. A code that is not in the table is not
guessed at, whatever it looks like; the customer is told so and the
technician reads it on the spot. Codes also differ between models, so every
answer says that too.

Only for a brand and an appliance we hold a table for, and only when the
message says the machine is showing something ("báo", "lỗi", "mã", ...): a
bare "UE" in a sentence is not read as a code.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DATA = Path(__file__).resolve().parents[2] / "data" / "error_codes.json"

_CUES = ("bao", "loi", "ma", "hien", "nhay", "error", "code", "chop", "nhap nhay")
# Shapes a code takes on a display: U4, 4C, 4C2, E1, dE1, 9E1, IE, tcL.
_TOKEN = re.compile(r"(?<![0-9A-Za-zÀ-ỹ])([0-9]?[A-Za-z]{1,3}[0-9]{0,2}|[0-9][A-Za-z][0-9]?)(?![0-9A-Za-zÀ-ỹ])")


def _codes_said(text: str) -> List[str]:
    """Tokens that read as a code: typed with a capital ("U4", "dE"), or right
    after "báo" / "lỗi" / "mã" ("báo lỗi ue"). Lower-case words elsewhere are
    words: unaccented "de" is "để", "5p" is five minutes."""
    found = []
    for match in _TOKEN.finditer(text):
        token = match.group(1)
        before = _fold(text[: match.start()]).split()
        if token != token.lower() or (before and before[-1] in _CUES):
            found.append(token)
    return found


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


@dataclass(frozen=True)
class CodeEntry:
    code: str
    meaning_en: str
    meaning_vi: str
    action_vi: str
    faults: tuple


@dataclass(frozen=True)
class BrandTable:
    brand: str
    brand_vi: str
    aliases: tuple
    device_type: str
    source_title: str
    source_url: str
    codes: Dict[str, CodeEntry]

    def find(self, token: str) -> Optional[CodeEntry]:
        return self.codes.get(token.upper())


@dataclass(frozen=True)
class CodeReading:
    """What one message said about an error code."""

    table: Optional[BrandTable]
    token: str
    entry: Optional[CodeEntry]
    """None when the brand is known but the code is not in its table."""


class ErrorCodeBook:
    def __init__(self, tables: List[BrandTable]) -> None:
        self.tables = tables

    def brand_in(self, text: str) -> Optional[str]:
        folded = f" {_fold(text)} "
        for table in self.tables:
            if any(f" {_fold(alias)} " in folded for alias in table.aliases):
                return table.brand
        return None

    def table_for(self, brand: Optional[str], device_type: Optional[str]) -> Optional[BrandTable]:
        return next(
            (t for t in self.tables if t.brand == brand and t.device_type == device_type), None
        )

    def devices(self) -> set:
        return {t.device_type for t in self.tables}

    def read(
        self, text: str, brand: Optional[str], device_type: Optional[str], following_up: bool = False
    ) -> Optional[CodeReading]:
        """The code the message reports, if it reports one.

        With a table for the brand and appliance: the entry, or entry None for
        a code not in it. Without a known brand: a reading with no table, but
        only for a token that some table for this appliance knows, so the
        assistant can ask which brand it is.
        """
        folded = f" {_fold(text)} "
        # "còn U0 thì sao" after a code was explained needs no "báo".
        if not following_up and not any(f" {cue} " in folded for cue in _CUES):
            return None
        tokens = _codes_said(text or "")
        table = self.table_for(brand, device_type)
        if table is not None:
            for token in tokens:
                entry = table.find(token)
                if entry:
                    return CodeReading(table, token.upper(), entry)
            # Something code-shaped that the table does not hold: say so, never guess.
            for token in tokens:
                if re.search(r"[0-9]", token) and re.search(r"[A-Za-z]", token) and len(token) <= 4:
                    return CodeReading(table, token.upper(), None)
            return None
        if brand is None and device_type in self.devices():
            for token in tokens:
                if any(t.find(token) for t in self.tables if t.device_type == device_type):
                    return CodeReading(None, token.upper(), None)
        return None


def _load(raw: dict) -> List[BrandTable]:
    tables = []
    for t in raw["tables"]:
        codes: Dict[str, CodeEntry] = {}
        for code, e in t["codes"].items():
            entry = CodeEntry(
                code=code.upper(),
                meaning_en=e["meaning_en"],
                meaning_vi=e["meaning_vi"],
                action_vi=e.get("action_vi", ""),
                faults=tuple(e.get("faults", [])),
            )
            for name in [code, *e.get("same_as", [])]:
                codes[name.upper()] = entry
        tables.append(
            BrandTable(
                brand=t["brand"],
                brand_vi=t["brand_vi"],
                aliases=tuple(t["aliases"]),
                device_type=t["device_type"],
                source_title=t["source"]["title"],
                source_url=t["source"]["url"],
                codes=codes,
            )
        )
    return tables


@lru_cache(maxsize=1)
def get_error_code_book() -> ErrorCodeBook:
    return ErrorCodeBook(_load(json.loads(DATA.read_text(encoding="utf-8"))))


def reply_vi(reading: CodeReading, urgent: bool) -> str:
    """The sentence the customer reads. Templated; nothing here comes from the model."""
    if reading.table is None:
        return f"Anh/chị cho em biết máy hãng gì để em tra đúng mã {reading.token} theo tài liệu của hãng nhé."
    brand = reading.table.brand_vi
    if reading.entry is None:
        return (
            f"Mã {reading.token} em chưa thấy trong bảng mã lỗi của {brand} mà em đang có, "
            "nên em không đoán ý nghĩa để tránh sai ạ; thợ sẽ đọc mã trực tiếp trên máy."
        )
    line = f"Theo bảng mã lỗi của {brand}, mã {reading.token} là {reading.entry.meaning_vi}."
    if reading.entry.action_vi and not urgent:
        line += f" Hãng hướng dẫn: {reading.entry.action_vi}."
    return line + " Mã lỗi có thể khác tùy dòng máy, thợ sẽ kiểm tra lại tận nơi ạ."


def note_vi(reading: CodeReading) -> Optional[str]:
    """The line for the technician, with what the code means per the brand."""
    if reading.table is None:
        return f"Máy báo mã {reading.token} (chưa rõ hãng)."
    if reading.entry is None:
        return f"Máy {reading.table.brand_vi} báo mã {reading.token} (không có trong bảng mã của hãng)."
    return f"Máy {reading.table.brand_vi} báo mã {reading.token}: {reading.entry.meaning_vi} (theo tài liệu hãng)."


CODE_BOOST = 1.8
"""How far a code from the brand's table moves the faults it names up the list.
Strong, because the machine measured it; not final, because codes differ
between models and a sensor can be the thing that failed."""
