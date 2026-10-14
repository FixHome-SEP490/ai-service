# app/services/pipeline/dialogue_state.py
"""What the customer has established, turn by turn, beyond the words they used.

The service used to remember a conversation as one string: everything the
customer said, joined. That is enough for symptoms that pile up — "không mát",
then "còn kêu to nữa" — and it is exactly wrong for everything else a person
does in a conversation. They rule things out. They report what they already
tried. They say what is *not* happening. They push back on an answer.

Joined into a bag of words, all of that reads as more evidence for the thing
being denied. "Mới vệ sinh tuần trước rồi, lưới lọc sạch" contains "vệ sinh"
and "lưới lọc", which are the dirty-filter fault's own words, so the retriever
ranked the dirty filter *higher* after the customer had excluded it (0.721
against 0.554 before they said anything). The assistant then repeated the
advice the customer had just told it was wrong, which is the single fastest
way to show someone you were not listening.

This module reads each customer turn into facts:

    exclusions      faults the customer has ruled out, and how: an action
                    already done ("đã vệ sinh rồi"), a cause denied ("không
                    phải do bẩn"), evidence that contradicts it ("lưới lọc
                    sạch"), or a flat "không phải đâu" to the last answer

    penalties       faults whose symptom the customer said is absent ("không
                    có chảy nước"). Lowered, not removed: absence of one
                    symptom makes a fault less likely, not impossible

    retrieval text  only the clauses that describe what *is* happening, so
                    the scorer never again counts a denial as a match

It also normalises how Vietnamese is actually typed before any of that: no
diacritics, teencode ("ko", "dc", "j"), regional words ("hông", "răng", "hư",
"bể"), Telex residue ("khoong", "mats") and stretched letters ("khônggg").

Every word is carried in two forms, folded and accented. When the customer typed
the accents they are used: folding makes "chảy" (leaking) and "cháy" (burning)
the same word, and "không có chảy nước" must not read as "không phải do cháy".
When they typed without accents, the folded form is all there is and it is used.

Everything here is lexical and deterministic, on purpose. It runs in CI with
no model, its decisions can be read in a trace, and the lexicon behind it is a
JSON file the team curates (`app/data/dialogue_knowledge.json`), so a phrasing
it misses is fixed by adding a line, not by retraining anything. The language
model still reads the whole conversation; this layer makes sure the facts it is
handed — the shortlist and the ranking — already reflect what was said.

Safety faults are never excluded by the customer's word. "Không có mùi gas" can
lower a gas leak in the ranking, but the warning about it is not something a
sentence can switch off.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "dialogue_knowledge.json"

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_BOUNDARY_RE = re.compile(r"[.,;!?\n\r…:()\[\]{}|/\\~=+*#\"“”]+|\s-\s|\s–\s")
_REPEAT_RE = re.compile(r"(.)\1{2,}")

NEGATED_PENALTY = 0.45
"""Multiplier for a fault whose own symptom the customer said is absent.

Strong enough to move it below a fault that matches what *is* happening, not so
strong that a fault with nothing else going for it disappears."""

SUSPECTED_BOOST = 1.3
"""Multiplier for a fault the customer names as their own suspicion.

"Không biết có phải hết gas không" is the strongest single clue in a long
message: the customer has looked at the machine and has a theory. The scorer
counts words, and in a message of forty words "gas" is one of them; this makes
it count for what it is."""

PERSIST_BOOST = 2.0
"""Multiplier for what a technician checks next when the customer's fix did not work.

"Thay thanh đốt rồi vẫn không nóng": the element is out, and the thermostat is
the next thing anyone who repairs water heaters would look at. Retrieval has no
way to know that - after the exclusion it only sees "không nóng", which fits the
thermostat and a blocked inlet alike. The order comes from `if_persists` in the
lexicon, curated per fault."""

CONFIRMED_BOOST = 1.5
"""Multiplier for the fault the last answer led with, when the customer says
"đúng rồi". It was the leader already; this keeps it there against whatever
the next message's words happen to match."""

DANGER_BOOST = 2.5
"""Multiplier for the appliance's safety faults once the customer has described
danger: smoke, a burning smell, sparks, a shock, gas. Ranking decides which
warning is pinned, and a fault that is fourth on the words "khói ra từ máy lạnh"
is a warning nobody gets."""

SAFETY_PENALTY = 0.6
"""Multiplier for a safety fault the customer ruled out in words.

Gentler than the others and never an exclusion: the cost of being wrong about a
gas leak is not symmetric with the cost of an extra line of warning."""

_FILLERS_AFTER_NEGATOR = frozenset(
    {"co", "phai", "bi", "do", "tai", "vi", "he", "the", "nao", "la", "con", "may", "gi",
     "thay", "duoc", "qua", "lam", "hoan", "toan", "bao", "gio", "nhe", "a", "dau", "dang",
     "tai", "it", "nhieu", "chut", "ti", "xiu", "chi"}
)
"""Words allowed between a negator and what it negates.

"Không phải do bẩn", "không hề bẩn", "không có bị chảy nước". Anything else
breaks the link: in "không mát do bẩn" the negation is about cooling, and the
dirt is being blamed, not denied."""

_ACTION_ONLY_NEGATORS = frozenset({"chua", "khoi", "chua he"})

_PARTICLES = frozenset(
    {"ma", "a", "nha", "nhe", "day", "do", "roi", "ha", "he", "ne", "luon", "thi", "het",
     "ca", "em", "anh", "chi", "minh", "toi", "nhung", "con", "van", "deu", "that", "tham"}
)
"""Words that do not change what a short clause says: "không sao mà", "ổn hết rồi"."""

_AMBIGUOUS_BARE = frozenset(
    {"do", "den", "tu", "o", "cua", "voi", "u", "ga", "bi", "de", "an", "ma", "la", "co",
     "thi", "the", "ro", "ri", "ne", "mo", "to", "bo", "ban", "nong", "on", "bom", "loi",
     "nut", "hu", "ho", "chay", "be", "mat", "ve", "tat", "rung", "sau", "keo", "khoa",
     "khoi", "no", "chap"}
)
"""One-word cues that, typed without accents, are several different words:
"do" is "do", "đó", "đỏ" and "dơ"; "chay" is "chạy", "cháy" and "chảy". A
one-word cue acts on such a token only when the customer typed the accent."""

_PREVERBAL = frozenset({"da", "moi", "vua"})

_LEADING_FILLERS = frozenset({"a", "u", "o", "thi", "ma", "nhung", "thoi", "ah", "uh", "e", "em", "anh", "chi", "da"})

_META_FILLERS = frozenset(
    """vay the gio nay do kia oi nhe nhi nha ne ha he a ah u um ok thi la
    co khong ko k di nua luon voi cho hoi xin tu de minh toi tui ban ad shop
    sua may nao nhieu khoang tam lam qua bay ma roi ca ui""".split()
)
"""Words that may sit around a meta phrase without making it about the
appliance: "vậy giờ sửa sao nhỉ", "cho mình hỏi luôn bao nhiêu tiền"."""

_MAX_TYPO_LENGTH = 12
"""Longest word the typo corrector will try. The longest Vietnamese syllable is
seven letters; the cost of a candidate set grows with the square of the length,
and a two-thousand-letter "word" would otherwise be a way to stall the service."""
"""Done markers that only count in front of the action: "đã thay", "mới thay",
"vừa thay". After it, "mới" is an adjective - "thay ổ mới" is a new socket."""

_OLD_TONE = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
}
"""Old-style tone placement to new. "hoà" and "hòa" are the same word."""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def fold(text: str) -> str:
    """Lowercase and strip diacritics. "Điều hòa" -> "dieu hoa"."""
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d")


def _accented(text: str) -> str:
    """Lowercase NFC with tone marks in the modern position."""
    word = unicodedata.normalize("NFC", text.lower())
    for old, new in _OLD_TONE.items():
        if old in word:
            word = word.replace(old, new)
    return word


def _has_accent(word: str) -> bool:
    return fold(word) != word


@dataclass(frozen=True)
class Tok:
    f: str
    """Folded form, always present."""
    a: Optional[str]
    """Accented form when the customer typed accents, None otherwise."""


def _same(token: Tok, folded: str, accented: str) -> bool:
    if token.a is not None and _has_accent(accented):
        return token.a == accented
    return token.f == folded


@dataclass(frozen=True)
class Phrase:
    folded: Tuple[str, ...]
    accented: Tuple[str, ...]
    original: str

    def at(self, tokens: Sequence[Tok], start: int) -> bool:
        n = len(self.folded)
        if start < 0 or start + n > len(tokens):
            return False
        return all(
            _same(tokens[start + i], self.folded[i], self.accented[i]) for i in range(n)
        )

    def find(self, tokens: Sequence[Tok], start: int = 0) -> int:
        starts = _starts(tokens).get(self.folded[0], ())
        for i in starts:
            if i >= start and self.at(tokens, i):
                return i
        return -1

    def span(
        self, tokens: Sequence[Tok], gaps: frozenset = frozenset(), max_gaps: int = 2
    ) -> Optional[Tuple[int, int]]:
        found = self._span(tokens, gaps, max_gaps)
        if (
            found is not None
            and len(self.folded) == 1
            and self.folded[0] in _AMBIGUOUS_BARE
            and tokens[found[0]].a is None
            and _has_accent(self.accented[0])
        ):
            return None
        return found

    def _span(
        self, tokens: Sequence[Tok], gaps: frozenset, max_gaps: int
    ) -> Optional[Tuple[int, int]]:
        """Where the phrase is, allowing up to `max_gaps` filler words inside it.

        "Thông cái lỗ thoát nước" is "thông lỗ thoát nước" with a classifier in
        the middle, and nobody types the curated phrase exactly.
        """
        n = len(self.folded)
        for i in _starts(tokens).get(self.folded[0], ()):
            if not _same(tokens[i], self.folded[0], self.accented[0]):
                continue
            j, k, used = 1, i + 1, 0
            while j < n and k < len(tokens):
                if _same(tokens[k], self.folded[j], self.accented[j]):
                    j += 1
                elif tokens[k].f in gaps and used < max_gaps:
                    used += 1
                else:
                    break
                k += 1
            if j == n:
                return i, k
        return None

    def __len__(self) -> int:
        return len(self.folded)


_STARTS_CACHE: Dict[int, Tuple[Sequence[Tok], Dict[str, List[int]]]] = {}


def _starts(tokens: Sequence[Tok]) -> Dict[str, List[int]]:
    """Where each folded word occurs in a clause, so a phrase is only tried
    where its first word is. A clause is read against two thousand phrases
    when the appliance is not known yet; trying each at every position made a
    long message take seconds."""
    key = id(tokens)
    cached = _STARTS_CACHE.get(key)
    if cached is not None and cached[0] is tokens:
        return cached[1]
    index: Dict[str, List[int]] = {}
    for i, token in enumerate(tokens):
        index.setdefault(token.f, []).append(i)
    if len(_STARTS_CACHE) > 64:
        _STARTS_CACHE.clear()
    _STARTS_CACHE[key] = (tokens, index)
    return index


def _phrase(text: str) -> Optional[Phrase]:
    words = _WORD_RE.findall(_accented(text))
    if not words:
        return None
    return Phrase(
        folded=tuple(fold(w) for w in words), accented=tuple(words), original=text
    )


def _phrases(texts: Iterable[str]) -> Tuple[Phrase, ...]:
    out = [p for p in (_phrase(t) for t in texts or []) if p]
    # Longest first, so "vệ sinh lưới lọc" is reported rather than "vệ sinh".
    return tuple(sorted(out, key=len, reverse=True))


def _folded_text(tokens: Sequence[Tok]) -> str:
    return " ".join(t.f for t in tokens)


def _contains(haystack: str, needle: str) -> bool:
    return bool(needle) and f" {needle} " in f" {haystack} "


def _edit1(word: str) -> Set[str]:
    letters = "abcdefghijklmnopqrstuvwxyz"
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = {a + b[1:] for a, b in splits if b}
    swaps = {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
    replaces = {a + c + b[1:] for a, b in splits if b for c in letters}
    inserts = {a + c + b for a, b in splits for c in letters}
    return deletes | swaps | replaces | inserts


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FaultCues:
    done: Tuple[Phrase, ...]
    cause: Tuple[Phrase, ...]
    absent: Tuple[Phrase, ...]
    never_exclude: bool = False
    tried: Tuple[Phrase, ...] = ()
    """Tried, and it rules out a sub-cause only: "chia đều đồ" for a machine
    that will not spin, which may still be a belt."""


class DialogueLexicon:
    """The curated lexicon, plus a vocabulary drawn from the knowledge base."""

    def __init__(
        self, data: dict, vocabulary: Iterable[str], symptom_phrases: Iterable[str] = ()
    ) -> None:
        norm = data.get("normalize", {})
        self.with_diacritics: Dict[str, str] = {
            _accented(k): _accented(v) for k, v in norm.get("with_diacritics", {}).items()
        }
        self.folded: Dict[str, str] = {
            fold(k): fold(v) for k, v in norm.get("folded", {}).items()
        }
        self.phrases: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = sorted(
            (
                (tuple(fold(k).split()), tuple(fold(v).split()))
                for k, v in norm.get("phrases", {}).items()
                if fold(k) != fold(v)
            ),
            key=lambda kv: len(kv[0]),
            reverse=True,
        )
        self.negators: Tuple[str, ...] = tuple(fold(n) for n in data.get("negators", []))
        self.done_markers: Tuple[str, ...] = tuple(fold(m) for m in data.get("done_markers", []))
        self.intent_markers: Tuple[str, ...] = tuple(
            fold(m) for m in data.get("intent_markers", [])
        )
        self.denial_patterns: Tuple[str, ...] = tuple(
            sorted((fold(p) for p in data.get("denial_patterns", [])), key=len, reverse=True)
        )
        self.previous_denials: Tuple[str, ...] = tuple(
            sorted((fold(p) for p in data.get("previous_denials", [])), key=len, reverse=True)
        )
        self.confirmations: Tuple[str, ...] = tuple(fold(c) for c in data.get("confirmations", []))
        self.post_denials: Tuple[str, ...] = tuple(
            sorted((fold(p) for p in data.get("post_denials", [])), key=len, reverse=True)
        )
        self.meta_phrases: Tuple[Tuple[str, ...], ...] = tuple(
            sorted(
                (tuple(fold(m).split()) for m in data.get("meta_phrases", [])),
                key=len,
                reverse=True,
            )
        )
        self.off_topic_terms: Tuple[str, ...] = tuple(fold(t) for t in data.get("off_topic_terms", []))
        self.danger_cues: Tuple[Phrase, ...] = _phrases(data.get("danger_cues", []))
        self.danger_exceptions: Tuple[Phrase, ...] = _phrases(data.get("danger_exceptions", []))
        self.suspicion_markers: Tuple[str, ...] = tuple(
            fold(m) for m in data.get("suspicion_markers", [])
        )
        self.hedges: Tuple[Tuple[str, ...], ...] = tuple(
            sorted(
                # The words of a stated theory go too: "có phải hết gas" is a
                # question about gas, and "phải" on its own is the remote's
                # "phải đứng sát mới bấm được".
                (
                    tuple(fold(h).split())
                    for h in list(data.get("hedges", [])) + list(data.get("suspicion_markers", []))
                ),
                key=len,
                reverse=True,
            )
        )
        self.connectors: frozenset = frozenset(fold(c) for c in data.get("clause_connectors", []))
        self.ack: Dict[str, str] = dict(data.get("ack", {}))
        self.gap_words: frozenset = frozenset(fold(w) for w in data.get("gap_words", []))
        self.generic_tried: Tuple[Phrase, ...] = _phrases(data.get("generic_tried", []))
        self.if_persists: Dict[str, Tuple[str, ...]] = {
            code: tuple(nxt) for code, nxt in data.get("if_persists", {}).items()
        }
        self.cues: Dict[str, FaultCues] = {
            code: FaultCues(
                done=_phrases(entry.get("done", [])),
                cause=_phrases(entry.get("cause", [])),
                absent=_phrases(entry.get("absent", [])),
                never_exclude=bool(entry.get("never_exclude", False)),
                tried=_phrases(entry.get("tried", [])),
            )
            for code, entry in data.get("faults", {}).items()
        }
        vocab = {fold(w) for w in vocabulary if w}
        for value in self.folded.values():
            vocab.update(value.split())
        for _, target in self.phrases:
            vocab.update(target)
        for cue in self.cues.values():
            for group in (cue.done, cue.cause, cue.absent):
                for phrase in group:
                    vocab.update(phrase.folded)
        vocab.update(w for n in self.negators for w in n.split())
        self.vocabulary: frozenset = frozenset(w for w in vocab if w)

        # Word pairs a connector must not be cut out of: "còn" joins clauses in
        # "không mát, còn kêu to", and is the whole point of "kính còn nguyên".
        keep: Set[Tuple[str, str]] = set()
        texts = list(data.get("keep_together", [])) + list(symptom_phrases)
        for entry in data.get("faults", {}).values():
            for group in ("done", "cause", "absent"):
                texts += entry.get(group, [])
        for text in texts:
            words = [fold(w) for w in _WORD_RE.findall(_accented(text))]
            for a, b in zip(words, words[1:]):
                if a in self.connectors or b in self.connectors:
                    keep.add((a, b))
        self.keep_together: frozenset = frozenset(keep)

        # Two-word terms of the trade with a dialect word inside, curated in
        # `terms`: "mô" is "đâu" in Huế, and "mô tơ" is a motor everywhere;
        # "tê tay" is a shock, not "kia tay". Inside one, nothing is remapped.
        terms: Set[Tuple[str, str]] = set()
        for text in data.get("terms", []):
            words = _WORD_RE.findall(_accented(text))
            terms.update(zip(words, words[1:]))
        self.terms: frozenset = frozenset(terms)

    # -- normalisation ------------------------------------------------------

    def _canonical(self, raw: str) -> List[Tok]:
        """One typed word to its canonical tokens (usually one, sometimes none)."""
        accented = _accented(raw)
        if accented in self.with_diacritics:
            mapped = self.with_diacritics[accented]
            return [Tok(fold(w), w) for w in mapped.split()]
        accented = _REPEAT_RE.sub(r"\1", accented)
        folded = fold(accented)
        if not folded:
            return []
        if folded in self.folded and not _has_accent(accented):
            # Typed without accents and a known shorthand: "rui" is "rồi" far
            # more often than it is half of "rủi ro".
            target = self.folded[folded]
            return [Tok(w, None) for w in target.split()]
        if folded in self.vocabulary:
            return [Tok(folded, accented if _has_accent(accented) else None)]
        if folded in self.folded:
            target = self.folded[folded]
            return [Tok(w, None) for w in target.split()]
        fixed = self._telex(folded)
        if fixed:
            return [Tok(fixed, None)]
        if 4 <= len(folded) <= _MAX_TYPO_LENGTH and folded.isalpha():
            fixed = self._typo(folded)
            if fixed:
                return [Tok(fixed, None)]
        return [Tok(folded, accented if _has_accent(accented) else None)]

    def _typo(self, word: str) -> Optional[str]:
        """One slip of the finger, if exactly one word in the vocabulary explains it.

        Tried in the order slips happen: two letters swapped ("khôgn"), one
        dropped ("ngun"), one doubled or stray ("nưcớc"), one wrong. The first
        kind that explains the word unambiguously wins; a tie at that level
        means the word is left as it was, because guessing between "tay" and
        "thay" is how a hand becomes a replacement.
        """
        letters = "abcdefghijklmnopqrstuvwxyz"
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        tiers = [
            {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1},
            {a + c + b for a, b in splits for c in letters},
            {a + b[1:] for a, b in splits if b},
            {a + c + b[1:] for a, b in splits if b for c in letters},
        ]
        for tier in tiers:
            found = {c for c in tier if c != word and c in self.vocabulary and len(c) >= 3}
            if len(found) == 1:
                return found.pop()
            if found:
                return None
        return None

    def _telex(self, word: str) -> Optional[str]:
        """Residue of a Telex keyboard that did not convert: "khoong", "mats"."""
        attempts = []
        if len(word) > 2 and word[-1] in "sfrxj":
            attempts.append(word[:-1])
        collapsed = re.sub(r"(aa|ee|oo|dd)", lambda m: m.group(0)[0], word)
        collapsed = collapsed.replace("ow", "o").replace("uw", "u").replace("aw", "a")
        attempts.append(collapsed)
        if len(collapsed) > 2 and collapsed[-1] in "sfrxj":
            attempts.append(collapsed[:-1])
        for attempt in attempts:
            if attempt != word and attempt in self.vocabulary:
                return attempt
        return None

    def _apply_phrases(self, tokens: List[Tok]) -> List[Tok]:
        if not self.phrases:
            return tokens
        out: List[Tok] = []
        i = 0
        while i < len(tokens):
            for source, target in self.phrases:
                n = len(source)
                if tuple(t.f for t in tokens[i : i + n]) == source:
                    out.extend(Tok(w, None) for w in target)
                    i += n
                    break
            else:
                out.append(tokens[i])
                i += 1
        return out

    def clauses(self, text: str) -> List[List[Tok]]:
        """Normalised clauses of one message."""
        out: List[List[Tok]] = []
        for segment in _BOUNDARY_RE.split(text or ""):
            tokens: List[Tok] = []
            raws = _WORD_RE.findall(segment)
            for i, raw in enumerate(raws):
                here = _accented(raw)
                nxt = _accented(raws[i + 1]) if i + 1 < len(raws) else ""
                prev = _accented(raws[i - 1]) if i > 0 else ""
                if (here, nxt) in self.terms or (prev, here) in self.terms:
                    tokens.append(Tok(fold(here), here if _has_accent(here) else None))
                    continue
                tokens.extend(self._canonical(raw))
            tokens = self._apply_phrases([t for t in tokens if t.f])
            current: List[Tok] = []
            for index, token in enumerate(tokens):
                if token.f in self.connectors and current:
                    after = tokens[index + 1].f if index + 1 < len(tokens) else ""
                    if (current[-1].f, token.f) not in self.keep_together and (
                        token.f,
                        after,
                    ) not in self.keep_together:
                        out.append(current)
                        current = []
                        continue
                current.append(token)
            if current:
                out.append(current)
        return out

    def normalize(self, text: str) -> str:
        return " ".join(_folded_text(c) for c in self.clauses(text))


@lru_cache(maxsize=1)
def _raw_data() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


_LEXICON: Optional[DialogueLexicon] = None


def get_lexicon(kb=None) -> DialogueLexicon:
    """Built once. The vocabulary comes from the knowledge base and corpus."""
    global _LEXICON
    if _LEXICON is None:
        if kb is None:
            from app.services.pipeline.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
        words: List[str] = []
        symptoms: List[str] = []
        for device in kb.device_types:
            for fault in kb.faults_for_device(device):
                symptoms += list(fault.symptoms_vi)
                symptoms.append(fault.name_vi)
                symptoms += list(fault.suggested_actions_vi)
                words += _WORD_RE.findall(fold(" ".join(fault.symptoms_vi)))
                words += _WORD_RE.findall(fold(fault.name_vi))
                words += _WORD_RE.findall(fold(" ".join(fault.suggested_actions_vi)))
            for alias in kb.aliases_vi(device):
                words += _WORD_RE.findall(fold(alias))
            name = kb.device_name_vi(device)
            if name:
                words += _WORD_RE.findall(fold(name))
        try:
            from app.services.pipeline.corpus import get_corpus

            counts: Dict[str, int] = {}
            for chunk in get_corpus():
                for word in _WORD_RE.findall(fold(chunk.text)):
                    counts[word] = counts.get(word, 0) + 1
            words += [w for w, n in counts.items() if n >= 3]
        except Exception:  # pragma: no cover - the corpus is optional here
            pass
        _LEXICON = DialogueLexicon(_raw_data(), words, symptoms)
    return _LEXICON


# ---------------------------------------------------------------------------
# Reading one turn
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Exclusion:
    fault_code: str
    kind: str
    """"done", "cause", "absent" or "previous"."""
    phrase_vi: str
    """The curated phrase that matched, in Vietnamese, for the acknowledgement."""


@dataclass
class TurnReading:
    retrieval_text: str
    """The clauses that describe what is happening, for the retriever."""
    exclusions: List[Exclusion] = field(default_factory=list)
    reinstated: List[str] = field(default_factory=list)
    """Faults an earlier turn excluded and this one brings back ("chưa vệ sinh")."""
    penalties: Dict[str, float] = field(default_factory=dict)
    boosts: Dict[str, float] = field(default_factory=dict)
    """Faults the customer named as a suspicion without denying them."""
    persist: Dict[str, float] = field(default_factory=dict)
    """What a technician checks next, after a fix the customer reports did not work."""
    denied_previous: bool = False
    confirmed_previous: bool = False
    danger: bool = False
    """The customer described danger in this turn, and did not negate it."""
    meta_only: bool = False
    """Every clause was about the conversation, none about the appliance."""


_SYMPTOM_CACHE: Dict[str, Tuple[Phrase, ...]] = {}


def _symptom_phrases(fault) -> Tuple[Phrase, ...]:
    cached = _SYMPTOM_CACHE.get(fault.fault_code)
    if cached is None:
        cached = _phrases(fault.symptoms_vi)
        _SYMPTOM_CACHE[fault.fault_code] = cached
    return cached


class _ClauseReader:
    def __init__(self, lexicon: DialogueLexicon, faults: Sequence, previous: Sequence[str]):
        self.lex = lexicon
        self.faults = list(faults)
        self.codes = {f.fault_code for f in self.faults}
        self.previous = [c for c in previous if c in self.codes]
        self.named: List[Tuple[str, str]] = []
        """Causes the last clause named without denying, for "..., không sao"."""

    def _negated_at(self, folded: List[str], position: int) -> bool:
        """A negator governs `position` if only filler words stand between.

        "Chưa" and "khỏi" are left out here: they qualify actions, not symptoms.
        "Chưa thay lõi lọc" is a filter that is overdue - evidence for the fault
        whose symptom list says "lâu chưa thay lõi", not against it.
        """
        i = position - 1
        while i >= 0 and folded[i] in _FILLERS_AFTER_NEGATOR:
            i -= 1
        if i < 0:
            return False
        negators = [n for n in self.lex.negators if n not in _ACTION_ONLY_NEGATORS]
        if folded[i] in negators:
            return True
        return i >= 1 and f"{folded[i - 1]} {folded[i]}" in negators

    def _done(self, folded: List[str], start: int, length: int) -> Optional[bool]:
        """True if the action at start is reported done, False if not yet, None if unclear."""
        before = folded[:start]
        after = folded[start + length :]
        near = before[-4:] + after[:5]
        joined = " ".join(near)
        if "chua" in near:
            return False
        front = " ".join(before[-4:])
        if any(_contains(" ".join(before[-3:] + after[:3]), m) for m in self.lex.intent_markers):
            # "có nên vệ sinh không", "định vệ sinh", "vệ sinh giá bao nhiêu".
            if not (
                any(_contains(joined, m) for m in ("roi", "xong"))
                or any(_contains(front, m) for m in _PREVERBAL)
            ):
                return None
        for marker in self.lex.done_markers:
            if marker == "van":
                if "van" in after[:3]:
                    return True
                continue
            if marker in _PREVERBAL:
                if _contains(front, marker):
                    return True
                continue
            if _contains(joined, marker):
                return True
        return None

    def _denied_after(self, after: List[str]) -> bool:
        """A denial right after the cause: "lưới lọc thì không phải", "tụ ổn mà".

        Not when it is itself negated: "không bình thường" is the opposite.
        """
        for pattern in self.lex.post_denials:
            words = pattern.split()
            for i in range(len(after) - len(words) + 1):
                if after[i : i + len(words)] != words:
                    continue
                if words[0] not in self.lex.negators and i > 0 and after[i - 1] in self.lex.negators:
                    continue
                return True
        return False

    def is_bare_denial(self, folded: List[str]) -> bool:
        """A clause that is only "không sao", "vẫn ổn", "bình thường mà"."""
        core = [w for w in folded if w not in _PARTICLES]
        return bool(core) and " ".join(core) in self.lex.post_denials and core[0] not in ("ok",)

    def _is_own_symptom(self, fault, tokens: List[Tok], start: int, end: int) -> bool:
        """The matched action is part of one of this fault's own symptoms.

        "Mới thay pin tháng trước mà đã hết" is in the knowledge base as a
        symptom of a lock battery problem; it reports a fix, and is evidence
        for the fault rather than against it.

        Not when the symptom is itself a fix that failed - "thay bóng rồi vẫn
        không sáng", listed under the dead bulb because the corpus file for it
        is where the next branch is discussed. Its own text says the bulb branch
        is ruled out from that sentence on, and it is.
        """
        for phrase in _symptom_phrases(fault):
            if len(phrase) <= end - start:
                continue
            found = phrase.span(tokens, self.lex.gap_words)
            if found is not None and found[0] <= start and found[1] >= end:
                if "van" in [t.f for t in tokens[end : found[1]]]:
                    continue
                return True
        return False

    def read(self, tokens: List[Tok]):
        folded = [t.f for t in tokens]
        exclusions: List[Exclusion] = []
        reinstated: List[str] = []
        penalties: Dict[str, float] = {}
        boosts: Dict[str, float] = {}
        persist: Dict[str, float] = {}
        self.named: List[Tuple[str, str]] = []
        factual = False
        persisting = -1
        """End of the last fix the customer reported, for "... rồi mà vẫn chảy"."""

        for fault in self.faults:
            cues = self.lex.cues.get(fault.fault_code)
            if cues is None:
                continue
            for phrase in cues.done:
                found = phrase.span(tokens, self.lex.gap_words)
                if found is None:
                    continue
                position, end = found
                if self._is_own_symptom(fault, tokens, position, end):
                    break
                state = self._done(folded, position, end - position)
                if state is True:
                    exclusions.append(Exclusion(fault.fault_code, "done", phrase.original))
                    factual = True
                    persisting = max(persisting, end)
                    # In the order a technician checks: the first next step
                    # counts most.
                    nexts = [c for c in self.lex.if_persists.get(fault.fault_code, ()) if c in self.codes]
                    for rank, code in enumerate(nexts):
                        factor = max(1.2, PERSIST_BOOST - 0.3 * rank)
                        persist[code] = max(factor, persist.get(code, 1.0))
                    break
                if state is False:
                    # Not done yet is evidence *for* the fault: keep the clause
                    # in retrieval, and undo any earlier exclusion.
                    reinstated.append(fault.fault_code)
                    break
            for phrase in cues.absent:
                found = phrase.span(tokens, self.lex.gap_words)
                if found is not None and self._done(folded, found[0], found[1] - found[0]) is None and any(
                    _contains(" ".join(folded[max(0, found[0] - 3) : found[0]]), m)
                    for m in self.lex.intent_markers
                ):
                    # "định chỉ cắm một cái": a plan, not something observed.
                    continue
                if found is not None:
                    exclusions.append(Exclusion(fault.fault_code, "absent", phrase.original))
                    factual = True
                    break
            for phrase in cues.cause:
                found = phrase.span(tokens, self.lex.gap_words)
                if found is None:
                    continue
                position = found[0]
                # Only an explicit denial: "không phải do bẩn", "không thể nào
                # do gas". A bare "không" in front of a cause word is usually
                # the symptom itself - "quạt không tuốc năng" is a fan whose
                # oscillation has stopped, not a fan whose oscillation is cleared.
                before = " ".join(folded[:position])
                if any(_contains(before, pattern) for pattern in self.lex.denial_patterns) or self._denied_after(
                    folded[found[1] : found[1] + 9]
                ):
                    exclusions.append(Exclusion(fault.fault_code, "cause", phrase.original))
                    factual = True
                elif any(_contains(before, m) for m in self.lex.suspicion_markers):
                    # Only a theory the customer states as one: "có phải hết
                    # gas không", "chắc là do tụ". A cause word on its own is
                    # usually the situation itself - "mất thẻ từ" is a lost
                    # card, not a suspected card reader.
                    boosts[fault.fault_code] = SUSPECTED_BOOST
                else:
                    self.named.append((fault.fault_code, phrase.original))
                break

        # Something tried that settles nothing on its own: "khởi động lại",
        # "chia đều đồ". It is not a symptom, so it is not searched for.
        tried_spans: List[Tuple[int, int]] = []
        pools = [self.lex.generic_tried] + [
            self.lex.cues[f.fault_code].tried for f in self.faults if f.fault_code in self.lex.cues
        ]
        for pool in pools:
            for phrase in pool:
                found = phrase.span(tokens, self.lex.gap_words)
                if found is not None and self._done(folded, found[0], found[1] - found[0]) is not False:
                    tried_spans.append(found)

        # A symptom said to be absent: "không có chảy nước", "có kêu đâu".
        for fault in self.faults:
            for phrase in _symptom_phrases(fault):
                if phrase.folded[0] in self.lex.negators:
                    continue
                position = phrase.find(tokens)
                if position < 0:
                    continue
                if len(phrase) < 2 and not (position > 0 and folded[position - 1] == "co"):
                    continue
                negated = self._negated_at(folded, position)
                end = position + len(phrase)
                if not negated and position > 0 and folded[position - 1] == "co":
                    negated = "dau" in folded[end : end + 3]
                if negated:
                    penalties[fault.fault_code] = NEGATED_PENALTY
                    factual = True
                    break

        # "Có X đâu" said of anything is a denial, whether or not X is a listed
        # symptom; keeping it in retrieval counts X as present.
        if not factual and len(folded) <= 8 and folded and folded[-1] == "dau" and "co" in folded:
            factual = True

        # "Thông lỗ thoát nước rồi mà vẫn chảy": the fix is not evidence, but
        # what is still happening after it is the best evidence there is.
        if factual and persisting >= 0 and not penalties:
            tail = folded[persisting:]
            if "van" in tail:
                rest = tail[tail.index("van") + 1 :]
                if rest:
                    return exclusions, reinstated, penalties, (boosts, persist), False, self._without_hedges(rest)

        if tried_spans and not factual:
            drop = {i for start, end in tried_spans for i in range(start, end)}
            rest = [w for i, w in enumerate(folded) if i not in drop]
            if "van" in rest:
                rest = rest[rest.index("van") + 1 :]
            return exclusions, reinstated, penalties, (boosts, persist), False, self._without_hedges(rest)

        return exclusions, reinstated, penalties, (boosts, persist), factual, self._without_hedges(folded)

    def describes_danger(self, tokens: List[Tok]) -> bool:
        folded = [t.f for t in tokens]
        harmless = [
            found
            for phrase in self.lex.danger_exceptions
            for found in [phrase.span(tokens)]
            if found is not None
        ]
        for phrase in self.lex.danger_cues:
            found = phrase.span(tokens)
            if found is None:
                continue
            if any(start <= found[0] < end for start, end in harmless):
                continue
            before = " ".join(folded[: found[0]])
            if self._negated_at(folded, found[0]) or any(
                _contains(before, p) for p in self.lex.denial_patterns
            ):
                # "Không có mùi khét": the shorter "khét" inside it is negated
                # with it, not a fresh mention.
                harmless.append(found)
                continue
            return True
        return False

    def is_meta(self, folded: List[str]) -> bool:
        """The clause says nothing about the appliance: "cảm ơn em", "đúng rồi",
        "có nguy hiểm không", "vậy giờ sửa sao"."""
        rest: List[str] = []
        i = 0
        while i < len(folded):
            for phrase in self.lex.meta_phrases:
                if tuple(folded[i : i + len(phrase)]) == phrase:
                    i += len(phrase)
                    break
            else:
                rest.append(folded[i])
                i += 1
        if len(rest) == len(folded):
            return False
        return all(w in _PARTICLES or w in _META_FILLERS for w in rest)

    def _without_hedges(self, folded: List[str]) -> str:
        """The clause without "không biết" and the like, for retrieval."""
        out: List[str] = []
        i = 0
        while i < len(folded):
            for hedge in self.lex.hedges:
                if tuple(folded[i : i + len(hedge)]) == hedge:
                    i += len(hedge)
                    break
            else:
                out.append(folded[i])
                i += 1
        return " ".join(out)

    def denies_previous(self, text: str) -> bool:
        if not self.previous:
            return False
        # "À, hông phải dzậy", "ờ sai rồi": a filler in front is still a no.
        words = text.split()
        while words and words[0] in _LEADING_FILLERS:
            words = words[1:]
        text = " ".join(words)
        return any(text == p or text.startswith(p + " ") for p in self.lex.previous_denials)

    def confirms_previous(self, text: str) -> bool:
        return any(_contains(text, c) for c in self.lex.confirmations)


def read_turn(
    text: str,
    faults: Sequence,
    previous_codes: Sequence[str] = (),
    lexicon: Optional[DialogueLexicon] = None,
) -> TurnReading:
    """Read one customer message against the faults of the appliance in question.

    `faults` is the pool for the known appliance, or every fault when it is not
    known yet. `previous_codes` is what the last answer named, so "không phải
    đâu" has something to deny.
    """
    lex = lexicon or get_lexicon()
    reader = _ClauseReader(lex, faults, previous_codes)
    kept: List[str] = []
    reading = TurnReading(retrieval_text="")
    seen: Set[str] = set()
    named: List[Tuple[str, str]] = []
    metas = clauses = 0
    for tokens in lex.clauses(text):
        if not tokens:
            continue
        if named and reader.is_bare_denial([t.f for t in tokens]):
            # "Lưới lọc thì em kiểm tra rồi, không sao": the denial is its own
            # clause, about the cause the clause before it named.
            for code, phrase in named:
                if code not in seen:
                    seen.add(code)
                    reading.exclusions.append(Exclusion(code, "cause", phrase))
                    reading.boosts.pop(code, None)
            named = []
            continue
        exclusions, reinstated, penalties, (boosts, persist), factual, folded_text = reader.read(tokens)
        named = list(reader.named)
        if reader.describes_danger(tokens):
            reading.danger = True
        for code, factor in persist.items():
            reading.persist[code] = max(factor, reading.persist.get(code, 1.0))
        for code, factor in boosts.items():
            if code not in {e.fault_code for e in exclusions} | seen:
                reading.boosts[code] = max(factor, reading.boosts.get(code, 1.0))
        for exclusion in exclusions:
            if exclusion.fault_code not in seen:
                seen.add(exclusion.fault_code)
                reading.exclusions.append(exclusion)
        reading.reinstated += [c for c in reinstated if c not in reading.reinstated]
        for code, factor in penalties.items():
            reading.penalties[code] = min(factor, reading.penalties.get(code, 1.0))
        denied = not exclusions and reader.denies_previous(folded_text)
        if denied:
            reading.denied_previous = True
            code = reader.previous[0]
            if code not in seen:
                seen.add(code)
                reading.exclusions.append(Exclusion(code, "previous", ""))
        if reader.confirms_previous(folded_text):
            reading.confirmed_previous = True
        meta = not (factual or denied) and reader.is_meta(folded_text.split())
        if meta:
            metas += 1
        if not (factual or denied or meta):
            kept.append(folded_text)
        clauses += 1
    reading.retrieval_text = " ".join(kept)
    reading.meta_only = clauses > 0 and metas == clauses
    # "Đúng rồi" to the last answer keeps its leader leading.
    if reading.confirmed_previous and reader.previous and not reading.exclusions:
        code = reader.previous[0]
        reading.boosts[code] = max(CONFIRMED_BOOST, reading.boosts.get(code, 1.0))
    return reading


# ---------------------------------------------------------------------------
# State across turns
# ---------------------------------------------------------------------------


@dataclass
class DialogueState:
    excluded: Dict[str, Exclusion] = field(default_factory=dict)
    penalties: Dict[str, float] = field(default_factory=dict)
    boosts: Dict[str, float] = field(default_factory=dict)
    persist: Dict[str, float] = field(default_factory=dict)
    danger: bool = False
    """Sticky: once danger is described it stays described for the session."""
    last_new: List[Exclusion] = field(default_factory=list)
    """Exclusions this turn added, for the acknowledgement."""

    def apply(self, reading: TurnReading, never_exclude: Set[str]) -> None:
        self.last_new = []
        for code in reading.reinstated:
            self.excluded.pop(code, None)
        for exclusion in reading.exclusions:
            code = exclusion.fault_code
            if code in never_exclude:
                self.penalties[code] = min(SAFETY_PENALTY, self.penalties.get(code, 1.0))
                continue
            if code not in self.excluded:
                self.excluded[code] = exclusion
                self.last_new.append(exclusion)
        for code, factor in reading.penalties.items():
            self.penalties[code] = min(factor, self.penalties.get(code, 1.0))
        for code, factor in reading.boosts.items():
            self.boosts[code] = max(factor, self.boosts.get(code, 1.0))
        for code, factor in reading.persist.items():
            self.persist[code] = max(factor, self.persist.get(code, 1.0))
        if reading.danger:
            self.danger = True

    def excluded_codes(self) -> Set[str]:
        return set(self.excluded)

    def factors(self) -> Dict[str, float]:
        """Score multipliers for the retriever: suspicions up, absences down."""
        out: Dict[str, float] = {}
        # Separate reasons multiply: the customer suspects gas *and* has already
        # cleaned the filter, and each is evidence on its own.
        danger = never_excluded_codes() if self.danger else set()
        for code in set(self.penalties) | set(self.boosts) | set(self.persist) | danger:
            out[code] = (
                self.penalties.get(code, 1.0)
                * self.boosts.get(code, 1.0)
                * self.persist.get(code, 1.0)
                * (DANGER_BOOST if code in danger else 1.0)
            )
        return out


def is_off_topic(text: str, lexicon: Optional[DialogueLexicon] = None) -> bool:
    """Whether the message is about a subject FixHome has nothing to say on."""
    lex = lexicon or get_lexicon()
    folded = " ".join(t.f for clause in lex.clauses(text) for t in clause)
    return any(_contains(folded, term) for term in lex.off_topic_terms)


def never_excluded_codes() -> Set[str]:
    lex = get_lexicon()
    return {code for code, cue in lex.cues.items() if cue.never_exclude}


def acknowledgement_vi(
    exclusions: Sequence[Exclusion], name_of, next_name: Optional[str] = None
) -> Optional[str]:
    """The sentence that tells the customer they were heard.

    Wording comes from `dialogue_knowledge.json`; only the fault name and the
    matched phrase are filled in, both of which are curated strings.
    """
    lex = get_lexicon()
    lines: List[str] = []
    for exclusion in exclusions[:2]:
        template = lex.ack.get(exclusion.kind)
        name = name_of(exclusion.fault_code)
        if not template or not name:
            continue
        lines.append(template.format(phrase=exclusion.phrase_vi, fault=name.lower()))
    if not lines:
        return None
    if next_name and lex.ack.get("next"):
        lines.append(lex.ack["next"].format(fault=next_name.lower()))
    return " ".join(lines)
