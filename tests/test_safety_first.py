"""The warn-before-diagnosing branches, checked mechanically.

Some faults in this corpus have a first sentence that is not negotiable: close
the gas cylinder valve, shut the main stopcock, unplug it and do not switch it
back on. Those cannot be left to whether the wording happened to rank well.

Two things are asserted here. Every fault the team marked HIGH resolves to a
section that gets pinned — if someone adds a dangerous fault and forgets the
`safety_heading`, this fails rather than shipping quietly. And the pinned text
reaches the top of the prompt, above the appliance and the conversation,
because a small model attends to what it reads first.

The instruction texts themselves are checked by substring on the few cases
where getting it wrong is irreversible: a gas leak, a burst pipe, a burning
smell from something wired into the wall.
"""

from __future__ import annotations

import pytest

from app.services.pipeline import context as ctxmod
from app.services.pipeline.conversation import Conversation
from app.services.pipeline.corpus import get_corpus
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.qwen_client import build_context_prompt
from app.services.pipeline.retriever import Retriever


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


@pytest.fixture(scope="module")
def retriever(kb):
    return Retriever(kb)


def _high_urgency_codes(kb):
    return sorted(
        fault.fault_code
        for device in kb.device_types
        for fault in kb.faults_for_device(device)
        if fault.urgency.upper() == "HIGH"
    )


def _prompt_for(kb, retriever, message: str, device_type: str) -> str:
    chat = Conversation(session_id="safety")
    chat.add("customer", message)
    candidates = retriever.candidate_faults(message, device_type, top_k=3)
    ctx = ctxmod.build(
        kb,
        retriever,
        chat,
        message,
        device_type,
        "description",
        candidates,
        has_image=False,
    )
    return build_context_prompt(ctx)


# -- every dangerous fault has something to pin ----------------------------


def test_every_high_urgency_fault_declares_a_safety_section(kb):
    """Declared in frontmatter, not inferred from the heading.

    Matching headings by pattern reached 13 of 25: the corpus words the
    instruction differently per cluster — "Bốn việc phải nói ngay", "Câu trả
    lời đầu tiên, trước mọi câu hỏi", "Ca khẩn nhất của cụm điện" — and the
    twelve it missed included a burst pipe and a gas regulator.
    """
    declared = {
        chunk.fault_code: chunk.safety_heading
        for chunk in get_corpus()
        if chunk.doc_type == "fault" and chunk.safety_heading
    }
    missing = [code for code in _high_urgency_codes(kb) if code not in declared]
    assert not missing, f"bệnh HIGH chưa khai báo safety_heading: {missing}"


def test_declared_safety_headings_point_at_a_real_section():
    """A typo in the frontmatter would silently disable the pin."""
    by_file: dict[str, set] = {}
    declared: dict[str, str] = {}
    for chunk in get_corpus():
        by_file.setdefault(chunk.source_file, set()).add(chunk.heading_vi)
        if chunk.safety_heading:
            declared[chunk.source_file] = chunk.safety_heading
    broken = [
        f"{path} -> {heading!r}"
        for path, heading in declared.items()
        if heading not in by_file[path]
    ]
    assert not broken, f"safety_heading không khớp mục nào: {broken}"


def test_every_high_urgency_fault_actually_pins(kb, retriever):
    """End to end, one code at a time, rather than only checking the data."""
    unpinned = [
        code for code in _high_urgency_codes(kb) if not retriever.safety_passages([code])
    ]
    assert not unpinned, f"không ghim được mục an toàn: {unpinned}"


def test_low_urgency_faults_pin_nothing(kb, retriever):
    """Pinning is for danger. A dripping tap must not arrive under a heading
    telling the model to warn before anything else."""
    assert retriever.safety_passages(["FAUCET_DRIP"]) == []
    assert retriever.safety_passages(["LIGHT_BULB_DEAD"]) == []


def test_only_one_instruction_is_pinned(retriever):
    """A gas smell shortlists both the leak and the regulator. Two blocks each
    headed "say this first" is an instruction that cannot be followed twice."""
    pinned = retriever.safety_passages(["STOVE_GAS_LEAK", "STOVE_REGULATOR"])
    assert len(pinned) == 1
    assert pinned[0].chunk.fault_code == "STOVE_GAS_LEAK"


# -- and it reaches the model, first ---------------------------------------


def test_the_warning_comes_before_the_appliance_in_the_prompt(kb, retriever):
    prompt = _prompt_for(kb, retriever, "bep gas nha em co mui gas", "gas_stove")
    assert "PHẢI NÓI NGAY" in prompt
    assert prompt.index("PHẢI NÓI NGAY") < prompt.index("THIẾT BỊ")


@pytest.mark.parametrize(
    "message,device_type,must_contain",
    [
        # Gas: the counter-intuitive one. The reflex on smelling gas is to open
        # a window by flicking on the fan.
        ("bep gas nha em co mui gas", "gas_stove", "không bật hay tắt bất kỳ công tắc điện nào"),
        ("bep gas nha em co mui gas", "gas_stove", "khoá van bình gas"),
        # Water: damage grows by the minute, so the first message is one action.
        ("vo ong nuoc phun khap nha", "water_pipe", "Khoá van tổng"),
        # Mains-wired appliances: the switch is not enough.
        ("quat tran co mui khet", "ceiling_fan", "aptomat"),
        ("den nha tam bi vao nuoc", "light_bulb", "aptomat"),
        # Microwave: never open the case, and the reason travels with it.
        ("lo vi song toe lua trong ruot", "microwave_oven", "đừng mở cửa"),
    ],
)
def test_the_instruction_itself_survives_into_the_prompt(
    kb, retriever, message, device_type, must_contain
):
    prompt = _prompt_for(kb, retriever, message, device_type)
    assert must_contain.lower() in prompt.lower(), message


def test_a_harmless_fault_gets_no_warning_banner(kb, retriever):
    prompt = _prompt_for(kb, retriever, "voi nuoc bi nho giot", "faucet")
    assert "PHẢI NÓI NGAY" not in prompt
