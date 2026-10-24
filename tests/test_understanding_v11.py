"""Understanding the same fault however it is said (understanding_bank.json)."""

import asyncio
import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import retriever as retriever_module
from app.services.pipeline.device_hint import devices_named_in
from app.services.pipeline.dialogue_state import get_lexicon, read_turn
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

ROOT = Path(__file__).resolve().parents[1]
KB = get_knowledge_base()
LEX = get_lexicon(KB)


def _split_of(phrase):
    import hashlib

    return "test" if hashlib.sha1(phrase.strip().lower().encode("utf-8")).digest()[0] % 10 < 3 else "dev"


# --- the held-out bank and the phrasebook ---------------------------------------


def test_the_bank_covers_every_fault_with_both_halves():
    bank = json.loads((ROOT / "tools" / "understanding_bank.json").read_text(encoding="utf-8"))
    codes = {f.fault_code for d in KB.device_types for f in KB.faults_for_device(d)}
    banked = {code for info in bank["devices"].values() for code in info["faults"]}
    assert banked == codes
    phrases = [
        p
        for info in bank["devices"].values()
        for f in info["faults"].values()
        for p in f["clear"] + f["indirect"]
    ]
    share = sum(_split_of(p) == "test" for p in phrases) / len(phrases)
    assert 0.2 < share < 0.4


def test_no_held_out_phrase_is_learned():
    """The phrasebook may only grow from the dev half; a test phrase in it would
    make every reported understanding number a memory test."""
    bank = json.loads((ROOT / "tools" / "understanding_bank.json").read_text(encoding="utf-8"))
    held_out = {
        " ".join(p.lower().split())
        for info in bank["devices"].values()
        for f in info["faults"].values()
        for p in f["clear"] + f["indirect"]
        if _split_of(p) == "test"
    }
    learned = json.loads((ROOT / "app" / "data" / "learned_phrasings.json").read_text(encoding="utf-8"))
    codes = {f.fault_code for d in KB.device_types for f in KB.faults_for_device(d)}
    for code, phrases in learned["faults"].items():
        assert code in codes
        for phrase in phrases:
            assert " ".join(phrase.lower().split()) not in held_out


def _top(retriever, text, device):
    return [c.fault.fault_code for c in retriever.candidate_faults(LEX.normalize(text), device, 3)]


def test_written_sections_and_learned_phrasings_find_what_the_symptom_lists_miss(monkeypatch):
    text = "tháng nào cũng phải lấy que tăm thông cái rãnh phía sau"
    bare = Retriever(KB, phrasebook={})
    monkeypatch.setattr(settings, "RETRIEVAL_WRITTEN_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "RETRIEVAL_LEARNED_WEIGHT", 0.0)
    assert "FRIDGE_DRAIN_BLOCKED" not in _top(bare, text, "refrigerator")
    monkeypatch.setattr(settings, "RETRIEVAL_WRITTEN_WEIGHT", 2.0)
    assert "FRIDGE_DRAIN_BLOCKED" in _top(bare, text, "refrigerator")
    monkeypatch.setattr(settings, "RETRIEVAL_LEARNED_WEIGHT", 2.0)
    assert _top(Retriever(KB), text, "refrigerator")[0] == "FRIDGE_DRAIN_BLOCKED"


def test_evidence_only_faults_are_never_decisive():
    candidates = Retriever(KB).candidate_faults(
        LEX.normalize("dưới bếp ai xả nước rửa rau là trên này lạnh toát"), "water_heater", 5
    )
    by_code = {c.fault.fault_code: c.score for c in candidates}
    assert "WH_INSTANT_NO_HOT" in by_code
    assert by_code["WH_INSTANT_NO_HOT"] <= settings.RETRIEVAL_EVIDENCE_ONLY_CAP < settings.RETRIEVAL_DECISIVE_SCORE


def test_a_curated_match_keeps_its_score():
    """The new evidence orders the list; thresholds still read the symptom list."""
    on = Retriever(KB).candidate_faults("ổ cắm không lên", "power_outlet", 3)
    assert on[0].fault.fault_code == "OUTLET_NO_POWER"
    assert on[0].score <= 1.0
    assert on[0].score - on[1].score >= 0.3


# --- naming the appliance ------------------------------------------------------


@pytest.mark.parametrize(
    "text,device",
    [
        ("tủ Toshiba nhà em không lạnh", "refrigerator"),
        ("con Daikin nhà em chảy nước", "air_conditioner"),
        ("bếp Rinnai lửa đỏ", "gas_stove"),
        ("ấm Xiaomi đun mãi không sôi", "kettle"),
        ("bình Picenza không nóng", "water_heater"),
        ("con Electrolux cửa trước kêu to", "washing_machine"),
        ("máy giặc nhà em không vắt", "washing_machine"),
        ("đìu hòa không mát", "air_conditioner"),
        ("bàn cầu nhà em xả yếu", "toilet"),
        ("lò viba không nóng", "microwave_oven"),
        ("ổ nối dài bị cháy đen", "power_outlet"),
    ],
)
def test_brands_slips_and_common_names_settle_the_appliance(text, device):
    assert {h.device_type for h in devices_named_in(text, KB)} == {device}


@pytest.mark.parametrize(
    "text",
    [
        "cái Panasonic nhà em hỏng",  # Panasonic makes ten of them: ask
        "đèn báo nháy đỏ",  # an indicator light on any appliance
        "quạt gắn trên trần ạ",  # one letter from "quạt bàn", meaning a ceiling
    ],
)
def test_a_brand_or_a_slip_alone_does_not_guess(text):
    named = {h.device_type for h in devices_named_in(text, KB)}
    assert "electric_fan" not in named or "quat ban" not in text
    assert len(named) <= 1
    if text.startswith(("cái Panasonic", "đèn báo")):
        assert not named


# --- what the search reads -----------------------------------------------------


def test_framing_is_kept_out_of_the_search_but_small_talk_still_counts():
    reading = read_turn("máy lạnh không mát nhờ xem giúp, mẹ em bảo", KB.faults_for_device("air_conditioner"))
    assert "xem giup" not in reading.retrieval_text
    assert "khong mat" in reading.retrieval_text
    small_talk = read_turn("có nguy hiểm không", KB.faults_for_device("air_conditioner"))
    assert small_talk.retrieval_text == ""
    assert small_talk.meta_only


class _NoDetector:
    async def detect(self, image):
        return []


@pytest.mark.parametrize(
    "text,device",
    [
        ("lò vi sóng nhà em dạo này hơi lạ", "microwave_oven"),
        ("dùng thấy không ổn lắm", "induction_hob"),
        ("có vấn đề gì đó mà em không tả được", "gas_stove"),
    ],
)
def test_a_vague_message_is_met_with_a_question(text, device):
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)

    async def run():
        chat = pipeline._conversations.get_or_create(None)
        chat.remember_device(device, 0.9, "image")
        return await pipeline.diagnose(DiagnosisRequest(description=text, sessionId=chat.session_id))

    reply = asyncio.run(run())
    assert reply.status.value == "needs_clarification"


# --- speed ---------------------------------------------------------------------


def test_the_normalisation_cache_hands_out_fresh_lists():
    first = retriever_module._normalize("máy lạnh không mát")
    first.append("hong")
    assert retriever_module._normalize("máy lạnh không mát") == ["may", "lanh", "khong", "mat"]
