# app/services/pipeline/retriever.py
"""Retrieval over the knowledge base.

Two jobs. For diagnosis it narrows the candidate faults handed to the VLM, so
the model chooses from a short grounded list instead of inventing one. For the
advisory chatbot it retrieves policy passages that answers must cite.

The default implementation is lexical and dependency-free so CI stays fast and
deterministic. Swapping in sentence embeddings means implementing the same two
methods; nothing else in the pipeline changes.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.config import settings
from app.services.pipeline.corpus import Chunk, get_corpus
from app.services.pipeline.knowledge_base import Fault, KnowledgeBase, Policy

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Vietnamese function words, written without diacritics because tokens are
# stripped before matching. Without this, "hư rồi" scores half a point against
# "kêu to rồi tắt" purely on the filler word, and a customer writing "máy lạnh
# hư rồi không biết sao" gets a confident diagnosis built on nothing.
_STOPWORDS = frozenset(
    """
    la co khong chua da dang se bi duoc va thi ma nhung nen roi
    tai cho khi luc nay kia ay nao gi sao vay the nhu
    toi minh em anh chi ban nha a oi um vang da
    mot hai ba cac nhung moi tung deu ca het rat qua lam hoi
    ra vao len xuong di ve lai nua con chi moi vua
    xin nho giup hoi sua kiem tra xem nao
    """.split()
)
"""Seven fillers are deliberately absent, and they are absent for one reason.

Diacritics are stripped before matching, so a filler and a piece of the trade's
core vocabulary can collapse onto the same token. Every one of these was on the
list once and each was deleting a word the customer had just typed:

    do   "do" but also "đỏ", the colour of a gas flame that is burning wrong
    den  "đến" but also "đèn", which is the whole subject of a lighting fault
    tu   "từ" but also "tụ", the capacitor, and "tủ", the refrigerator
    o    "ở" but also "ổ", the socket and the bearing
    cua  "của" but also "cửa", the door of an oven, a fridge, a machine
    voi  "với" but also "vòi", the tap
    u    "ừ" but also "ù", the hum of a motor that is trying to start

The cost of keeping them is a little precision on sentences that use them as
filler, and rarity weighting absorbs most of that: a word that really is filler
appears across most of the symptom lists and is scored near zero anyway. The
cost of listing them was a customer writing "bóng đèn" and being understood to
have said nothing at all."""


def _content_tokens(tokens: List[str]) -> List[str]:
    """Drop filler words, but never return an empty list.

    A query made entirely of stopwords still has to score something rather than
    crash or match everything; returning the original tokens leaves the caller
    to decide, and zero-overlap filtering handles it downstream.
    """
    kept = [t for t in tokens if t not in _STOPWORDS]
    return kept or tokens


def _normalize(text: str) -> List[str]:
    """Lowercase, strip Vietnamese diacritics, tokenize.

    Diacritics are dropped so that a customer typing without tone marks still
    matches the curated symptom phrasing.
    """
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    stripped = stripped.replace("\u0111", "d")
    return _TOKEN_RE.findall(stripped)


@dataclass(frozen=True)
class ScoredFault:
    fault: Fault
    score: float


@dataclass(frozen=True)
class ScoredPolicy:
    policy: Policy
    score: float


@dataclass(frozen=True)
class ScoredChunk:
    """A written passage and how well it covers the question."""

    chunk: Chunk
    score: float


# ---------------------------------------------------------------------------
# Written corpus: index and scoring
# ---------------------------------------------------------------------------

_BM25_K1 = 1.5
_BM25_B = 0.75
"""Standard BM25 constants. k1 caps how much repetition can help; b is how
hard length is penalised."""

_HEADING_REPEATS = 3
"""A word in the heading is counted as occurring this many extra times.

Headings are the one curated summary in the corpus — "Câu phải nói ngay", "Vì
sao lửa đỏ", "Phép thử màu: cách phát hiện rò im lặng". Expressed as repetition
rather than a multiplier so it flows through BM25's own saturation instead of
sitting outside it."""

_FAULT_MATCH_WEIGHT = 1.35
"""Boost for a passage belonging to a fault the shortlist already ranked.

The shortlist is computed from curated symptom phrasing and is the strongest
signal in the pipeline. Without it, a question whose words appear across many
files retrieves prose about the wrong fault of the right appliance — readable,
grounded, and about something else."""

_PHRASING_PENALTY = 0.45
"""Applied to the sections that list how customers word things.

Every fault file has "Khách nói thế nào" and "Khách gõ không dấu, gõ tắt":
short, dense lists of the exact phrases a customer types, with no advice in
them. They are retrieval bait. They match any real message better than the
section that explains what to do, because they were written from the same
vocabulary — and then they hand the model a list of synonyms instead of an
answer. Demoted rather than dropped, because when they do surface they are
decent evidence that the file is the right one."""

_META_HEADINGS = frozenset(
    {
        "nen tri thuc cua tai lieu nay",
    }
)
"""Sections that exist for the team, not the customer.

The sourcing note records which standard or training module a file was written
from and what still needs checking. It is how the corpus stays honest, and it
would be bizarre in front of someone whose fridge is broken."""


def _heading_key(heading: str) -> str:
    return " ".join(_normalize(heading))


class _CorpusIndex:
    """Tokenised corpus with BM25 statistics.

    Built once per process. Plain overlap — what policy retrieval uses — does
    not work here, and the first attempt proved it: a policy passage is two or
    three sentences, so sharing half its words means something, but a corpus
    section is 726 characters of prose and contains most of the common
    vocabulary of the language. Every question scored 1.00 against every
    section of the right appliance and the ordering fell back to alphabetical.

    BM25 fixes both halves of that. Inverse document frequency makes "cảm ứng
    nhiệt" count for more than "máy", and the length term stops a long section
    from winning merely by containing everything. It stays lexical,
    deterministic and dependency-free, so CI is unchanged and the embedding
    decision can still be made later on measured evidence.
    """

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self.chunks: Tuple[Chunk, ...] = tuple(chunks)
        self._freq: List[Dict[str, int]] = []
        self._length: List[int] = []
        document_freq: Dict[str, int] = {}

        for chunk in self.chunks:
            tokens = _content_tokens(_normalize(chunk.text))
            tokens += _content_tokens(_normalize(chunk.heading_vi)) * _HEADING_REPEATS
            counts: Dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            self._freq.append(counts)
            self._length.append(len(tokens))
            for token in counts:
                document_freq[token] = document_freq.get(token, 0) + 1

        total = max(len(self.chunks), 1)
        self._avg_length = (sum(self._length) / total) or 1.0
        self._idf: Dict[str, float] = {
            token: math.log(1.0 + (total - freq + 0.5) / (freq + 0.5))
            for token, freq in document_freq.items()
        }
        self._unseen_idf = math.log(1.0 + (total + 0.5) / 0.5)
        """A word the corpus never uses. It cannot be matched, and it should
        pull the score down: the corpus genuinely does not cover it."""

    def idf(self, token: str) -> float:
        return self._idf.get(token, self._unseen_idf)

    def score(self, index: int, query_tokens: Sequence[str]) -> float:
        """BM25, divided by the question's own weight.

        Dividing makes the number comparable between a three-word question and
        a ten-word one, so a single floor can be set for both. It lands roughly
        in 0 to 2.5 rather than 0 to 1: a section of average length containing
        every query word once scores about 1.0, and repetition or brevity takes
        it higher.
        """
        if not query_tokens:
            return 0.0
        counts = self._freq[index]
        norm = _BM25_K1 * (
            1.0 - _BM25_B + _BM25_B * self._length[index] / self._avg_length
        )
        total = 0.0
        matched = 0.0
        for token in query_tokens:
            weight = self.idf(token)
            total += weight
            freq = counts.get(token, 0)
            if freq:
                matched += weight * (freq * (_BM25_K1 + 1.0)) / (freq + norm)
        if total <= 0.0:
            return 0.0
        return matched / total

    def is_retrievable(self, chunk: Chunk) -> bool:
        return _heading_key(chunk.heading_vi) not in _META_HEADINGS

    def presentation_weight(self, chunk: Chunk) -> float:
        key = _heading_key(chunk.heading_vi)
        if key.startswith("khach noi the nao") or key.startswith("khach go khong dau"):
            return _PHRASING_PENALTY
        return 1.0


@lru_cache(maxsize=1)
def _corpus_index() -> _CorpusIndex:
    return _CorpusIndex(get_corpus())


def _overlap_score(query_tokens: List[str], target: str) -> float:
    target_tokens = set(_content_tokens(_normalize(target)))
    query_tokens = _content_tokens(query_tokens)
    if not target_tokens or not query_tokens:
        return 0.0
    hits = sum(1 for t in set(query_tokens) if t in target_tokens)
    return hits / len(set(query_tokens))


_PRICE_NOISE = {
    "gia", "tien", "bao", "nhieu", "tinh", "het", "cost", "ban", "minh", "sao",
    "the", "nao", "khoang", "chi", "phi", "ben",
}
"""Words in every price question, which match nothing and dilute everything.

"dây điện thay bên mình tính giá sao" is eight tokens of which two say what is
being asked about. Dividing by all eight put the right row under any usable
threshold."""


def _price_score(
    query_tokens: List[str], row_name: str, alias_tokens: Sequence[str] = ()
) -> float:
    """Balance how much of the row the question covers against how much of the
    question the row explains.

    Each direction alone picks a different wrong answer. Dividing by the
    question, as policy retrieval does, buries every short row under a long
    sentence. Dividing by the row rewards the shortest rows: expanded with the
    device's aliases, "thay ổ cắm hết bao nhiêu tiền" covered every word of
    "Công tắc cửa" and scored it a perfect match.
    """
    target = set(_content_tokens(_normalize(row_name)))
    query = {t for t in _content_tokens(query_tokens) if t not in _PRICE_NOISE}
    if not target or not query:
        return 0.0

    # Aliases widen what counts as a hit without widening the question. They
    # are the team's words for a device, not the customer's, so charging the
    # question for their length punishes it for a synonym it never used:
    # "thay block máy lạnh" fell below the floor once six air-conditioner
    # aliases had been added to its denominator.
    alias = {t for t in _content_tokens(list(alias_tokens))} - query

    # The customer's own words count double. Six aliases of "máy lạnh" made
    # every air-conditioner part match as strongly as the cleaning service the
    # question actually named, and "công tắc ổ cắm" — a legitimate alias of a
    # socket — put a door switch above the socket row.
    hits = sum(1 for t in target if t in query) + 0.5 * sum(
        1 for t in target if t in alias
    )
    if not hits:
        return 0.0

    # Recall, deliberately. Tuning this into a precise ranker meant chasing one
    # wrong answer after another: dividing by the question buried short rows,
    # dividing by the row crowned the shortest ones, and balancing the two put
    # "Công tắc cửa" at the top for a question about a socket. Lexical overlap
    # on two-word names cannot tell a near miss from a match.
    #
    # So it gathers candidates rather than choosing one, and Qwen chooses among
    # them — the same division of labour as the fault shortlist, where it
    # works. Nothing outside these rows can reach the customer either way.
    return hits / len(target)


class _SymptomIndex:
    """How rare each word is across one appliance's own symptom lists.

    Plain overlap counted every matched word the same, so "nuoc" — a word in
    nearly every plumbing symptom list, which therefore separates nothing —
    weighed as much as "be", which appears in one list and settles the answer.
    The first fix for that deleted appliance-naming words outright, and it took
    "nuoc" with it: "ong nuoc bi be" arrived as two words, matched no fault at
    all, and a burst pipe reached the customer as silence.

    Rarity handles both cases with no list to maintain. A word used by every
    fault of the appliance carries almost nothing; the appliance's own name is
    exactly such a word, because the symptom lists keep repeating it.
    """

    def __init__(self, faults: Sequence[Fault]) -> None:
        self._df: Dict[str, int] = {}
        for fault in faults:
            seen = set(_normalize(" ".join(fault.symptoms_vi)))
            for token in seen:
                self._df[token] = self._df.get(token, 0) + 1
        self._total = max(len(faults), 1)

    def weight(self, token: str) -> float:
        """Zero for a word no symptom list uses.

        A word outside the vocabulary is not evidence about anything, so it is
        not charged to the denominator either. Charging it punished politeness:
        "am sieu toc nha em bi ro nuoc o day a" would have scored below the
        blunt "ro nuoc" purely for the filler.
        """
        df = self._df.get(token, 0)
        if not df:
            return 0.0
        return math.log(1 + self._total / df)

    def score(self, query_tokens: Iterable[str], fault: Fault) -> float:
        """Share of the query's discriminating weight that this fault matches.

        Filler words are dropped from both sides or from neither. _content_tokens
        returns its input untouched when everything in it is filler, so filtering
        each side independently made an all-filler message unmatchable against
        anything: "khong di duoc" kept its three words while every symptom list
        lost them. That message is how a blocked toilet usually arrives, and a
        blocked toilet is one of the faults that has to warn before it answers.
        """
        tokens = list(query_tokens)
        symptoms = _normalize(" ".join(fault.symptoms_vi))
        if all(token in _STOPWORDS for token in tokens):
            # Rarity can judge filler words on its own. A word common enough to
            # be filler is common enough across the symptom lists to weigh
            # almost nothing, so the rare one in the message decides.
            query, target = tokens, set(symptoms)
        else:
            query, target = _content_tokens(tokens), set(_content_tokens(symptoms))
        weights = {t: self.weight(t) for t in set(query)}
        total = sum(weights.values())
        if total <= 0.0:
            return 0.0
        return sum(w for t, w in weights.items() if t in target) / total


def _device_alias_tokens(question: str, kb: KnowledgeBase) -> List[str]:
    """Add what the team calls a device to what the customer calls it.

    The labour table says "điều hòa" and customers say "máy lạnh", so "vệ sinh
    máy lạnh giá bao nhiêu" matched the water heater row and not one of the
    three air-conditioner cleaning rows sitting right there.
    """
    from app.services.pipeline import device_hint

    extra: List[str] = []
    for hint in device_hint.devices_named_in(question, kb):
        for alias in kb.aliases_vi(hint.device_type):
            extra.extend(_normalize(alias))
        name = kb.device_name_vi(hint.device_type)
        if name:
            extra.extend(_normalize(name))
    return extra


class Retriever:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb
        self._symptom_indexes: Dict[Optional[str], _SymptomIndex] = {}

    def _symptom_index(self, device_type: Optional[str]) -> _SymptomIndex:
        """Built once per appliance, on first use.

        Document frequency is only meaningful inside the pool being ranked: the
        word "nuoc" is everywhere among the plumbing faults and nearly absent
        among the electrical ones, so one index over all 108 would rate it the
        same in both.
        """
        if device_type not in self._symptom_indexes:
            pool = (
                self._kb.faults_for_device(device_type)
                if device_type
                else [
                    f
                    for d in self._kb.device_types
                    for f in self._kb.faults_for_device(d)
                ]
            )
            self._symptom_indexes[device_type] = _SymptomIndex(pool)
        return self._symptom_indexes[device_type]

    def candidate_faults(
        self,
        description: str,
        device_type: Optional[str],
        top_k: int = 5,
    ) -> List[ScoredFault]:
        """Rank faults by symptom overlap, restricted to the detected device.

        Restricting by device is what makes the detector worth its cost: it cuts
        the candidate space before the VLM ever sees it.
        """
        pool = (
            self._kb.faults_for_device(device_type)
            if device_type
            else [f for d in self._kb.device_types for f in self._kb.faults_for_device(d)]
        )
        tokens = _normalize(description)
        # Weighted by how rare each word is among this appliance's own symptom
        # lists. Once the appliance is settled its own name is noise — and worse
        # than noise, because the symptom lists mention it too. "Tai sao lua bep
        # gas lai co mau do" is four content words of which two name the stove,
        # and both matched the gas-leak symptoms, which say "bep gas" in several
        # entries; the fault about a red flame came fourth behind a leak. Rarity
        # settles that with no list of words to delete, which an earlier fix had
        # needed and which had quietly deleted "nuoc" from plumbing messages.
        index = self._symptom_index(device_type)
        scored = [ScoredFault(fault=f, score=index.score(tokens, f)) for f in pool]
        scored.sort(key=lambda s: s.score, reverse=True)
        # Drop zero-overlap faults. Handing the VLM every fault of a device
        # whenever the description says nothing useful invites a confident
        # guess; an empty shortlist correctly ends in a clarification instead.
        return [s for s in scored[:top_k] if s.score > 0.0]

    def content_words(self, text: str) -> int:
        """How many words carry meaning, once function words are dropped.

        A high retrieval score means nothing on its own: the score divides by
        the query's own length, so "hư rồi" matches some symptom perfectly and
        scores 1.00. Counting what the customer actually described separates a
        precise sentence from a shrug.
        """
        return len(_content_tokens(_normalize(text)))

    def price_passages(
        self, question: str, top_k: int = 10, device_type: Optional[str] = None
    ) -> List[ScoredPolicy]:
        """Lines from the labour and parts tables that match what was asked.

        Returned as passages so they travel the same path as policy text: the
        model may restate them and nothing else, which keeps a figure on screen
        traceable to a row somebody in the team owns.

        A lower floor than policy text on purpose. A price row is one short
        line — "Thay ổ cắm điện, tiền công" — so a question shares far less of
        it than of a paragraph, and the policy threshold hid every one of them.
        """
        tokens = _normalize(question)
        if not tokens:
            return []

        # Narrow to the device first, exactly as the fault shortlist does.
        # Ranking all 809 rows at once was the mistake: their names share so
        # much vocabulary that "vệ sinh máy lạnh giá bao nhiêu" ranked a relay,
        # a fridge hinge and refrigeration oil above the air-conditioner
        # cleaning service it had named outright. Within one device the
        # remaining rows are few and the overlap means something again.
        from app.services.pipeline import device_hint

        named = device_hint.devices_named_in(question, self._kb)
        wanted = {hint.device_type for hint in named}
        if not wanted and device_type:
            # The question rarely names the appliance again. "Thay bộ đánh lửa
            # bao nhiêu" arrives in a thread already about a gas stove and was
            # answered citing a refrigerator display board, because each
            # question was searched as though it were the first.
            wanted = {device_type}
        rows = self._kb.price_rows
        if wanted:
            narrowed = [r for r in rows if wanted & set(r.device_types)]
            if narrowed:
                rows = narrowed

        aliases = _device_alias_tokens(question, self._kb)
        scored = [
            ScoredPolicy(
                policy=Policy(
                    doc_id=row.code, title_vi=row.name_vi, content_vi=row.as_text_vi()
                ),
                score=_price_score(tokens, row.name_vi, aliases),
            )
            for row in rows
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= settings.PRICE_MIN_SCORE]

    def safety_passages(
        self, fault_codes: Iterable[str], limit: int = 1
    ) -> List[ScoredChunk]:
        """The instruction to give before diagnosing, for dangerous faults.

        Pinned, not ranked, and that is the whole point. Measured on the gas
        leak — the most dangerous entry in the corpus — a customer writing "bếp
        gas nhà em có mùi gas" retrieved three sections of good prose about gas
        leaks and not the one listing the four things to do. It scored below
        them because it is written as instructions rather than explanation, so
        it repeats the customer's own words least.

        Ranking cannot fix that. A section that has to come first cannot be
        asked to compete on wording, so two pieces of curated data decide
        instead: the fault table's own `urgency`, and a `safety_heading` named
        in the file's frontmatter. Both are written by the team, neither is
        inferred, and `tests/test_safety_first.py` fails if a HIGH fault has no
        section to pin.

        One by default, because there is only one thing to say first. A gas
        smell shortlists both the leak and the regulator, and pinning both
        produced two blocks each headed "say this before anything else" — an
        instruction the model cannot follow twice. The top-ranked fault wins.
        """
        urgent = [
            code
            for code in fault_codes
            if (fault := self._kb.fault(code)) is not None
            and fault.urgency.upper() == "HIGH"
        ]
        if not urgent:
            return []

        found: Dict[str, Chunk] = {
            chunk.fault_code: chunk
            for chunk in _corpus_index().chunks
            if chunk.is_safety and chunk.fault_code in urgent
        }
        ordered = [found[code] for code in urgent if code in found]
        return [ScoredChunk(chunk=chunk, score=1.0) for chunk in ordered[:limit]]

    def corpus_passages(
        self,
        question: str,
        device_type: Optional[str] = None,
        fault_codes: Iterable[str] = (),
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        exclude: Iterable[str] = (),
    ) -> List[ScoredChunk]:
        """Written prose about this appliance that covers the question.

        Two filters run before anything is scored, and they matter more than the
        scoring does.

        The device filter is the same idea that makes the fault shortlist work.
        2,380 fault sections share a great deal of vocabulary — every cluster
        discusses noise, smell, heat and what the customer should check first —
        so ranking all of them against one sentence puts a washing-machine
        bearing beside an air-conditioner fan. Within one appliance the
        remaining sections are few and the overlap means something again.

        The fault filter is a boost rather than a cut: the shortlist is already
        the best evidence the pipeline has about which fault this is, so its
        sections start ahead, but a section from another fault of the same
        appliance can still win when the question is clearly about it.

        Sections with no `device_type` — the business layer — are left out here
        and retrieved by `business_passages`, so a question about a fault cannot
        spend its budget on the booking flow.
        """
        limit = settings.CORPUS_TOP_K if top_k is None else top_k
        threshold = settings.CORPUS_MIN_SCORE if min_score is None else min_score
        tokens = _content_tokens(_normalize(question))
        if not tokens:
            return []

        # A shortlist is required, not merely helpful, and this is the guard
        # that keeps an off-topic message from retrieving confident prose.
        #
        # Two measurements put it here. Unnarrowed, "đặt lịch sửa chữa thế nào"
        # returned three passages about self-diagnosis, a washing machine that
        # will not spin, and water heater servicing — none about booking.
        # Narrowed only by device, "thời tiết hôm nay thế nào" against a known
        # air conditioner still scored 1.19 on "Bối cảnh thời gian", because
        # "hôm" is genuinely rare in a technical corpus and matches "hôm qua
        # còn mát hôm nay không".
        #
        # No lexical floor separates those two cases: real answers measured
        # 1.0 to 2.6 and that false positive sat inside the range. What does
        # separate them is that an off-topic message shares no wording with any
        # curated symptom, so the shortlist comes back empty — the same test
        # the pipeline already uses to decide between answering and asking.
        fault_codes = list(fault_codes)
        if not fault_codes:
            return []

        index = _corpus_index()
        wanted = set(fault_codes)
        seen = set(exclude)
        scored: List[ScoredChunk] = []
        for position, chunk in enumerate(index.chunks):
            if chunk.doc_type not in ("fault", "device"):
                continue
            if device_type and chunk.device_type != device_type:
                continue
            if not index.is_retrievable(chunk):
                continue
            if f"{chunk.source_file}::{chunk.heading_vi}" in seen:
                continue
            score = index.score(position, tokens) * index.presentation_weight(chunk)
            if chunk.fault_code and chunk.fault_code in wanted:
                score *= _FAULT_MATCH_WEIGHT
            scored.append(ScoredChunk(chunk=chunk, score=score))

        scored.sort(key=lambda s: (-s.score, s.chunk.source_file, s.chunk.heading_vi))
        return [s for s in scored[:limit] if s.score >= threshold]

    def business_passages(
        self,
        question: str,
        top_k: int = 1,
        min_score: Optional[float] = None,
    ) -> List[ScoredChunk]:
        """Passages from the business layer: booking, pricing model, warranty.

        Kept apart from the appliance prose and given its own small budget. A
        customer asking what a repair costs needs the rule about how the figure
        is put together, and that rule lives in one of five system files rather
        than in any fault. Ranked together, a fault's 2,380 sections would drown
        it every time.
        """
        threshold = settings.CORPUS_MIN_SCORE if min_score is None else min_score
        tokens = _content_tokens(_normalize(question))
        if not tokens:
            return []

        index = _corpus_index()
        scored = [
            ScoredChunk(chunk=chunk, score=index.score(position, tokens))
            for position, chunk in enumerate(index.chunks)
            if chunk.doc_type == "system" and index.is_retrievable(chunk)
        ]
        scored.sort(key=lambda s: (-s.score, s.chunk.source_file, s.chunk.heading_vi))
        return [s for s in scored[:top_k] if s.score >= threshold]

    def policy_passages(
        self, question: str, top_k: int = 3, min_score: Optional[float] = None
    ) -> List[ScoredPolicy]:
        """Passages that actually cover the question, or nothing.

        The floor is the whole point. Lexical overlap scores every question
        against every passage, so a question about the weather still retrieves
        the air-conditioner maintenance policy on the word it shares. Returning
        that leaves the model as the only thing preventing an invented answer.
        """
        threshold = settings.POLICY_MIN_SCORE if min_score is None else min_score
        tokens = _normalize(question)
        scored = [
            ScoredPolicy(
                policy=p,
                score=_overlap_score(tokens, f"{p.title_vi} {p.content_vi}"),
            )
            for p in self._kb.policies
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= threshold]
